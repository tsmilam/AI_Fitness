import os
import pickle
import io
import json
import pandas as pd
import requests
import time
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
from google import genai
from dotenv import load_dotenv

# --- CONFIGURATION ---
DRY_RUN = False  # Set to False to actually post workouts to Hevy
MODEL_NAME = "gemini-flash-latest" # Using latest Gemini Flash model

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HEVY_API_KEY = os.getenv("HEVY_API_KEY")
TARGET_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
SCOPES = ['https://www.googleapis.com/auth/drive'] # Removed .readonly so we can upload the missing CSV if needed

# --- MONTHLY PROMPT ---
MONTHLY_PROMPT_TEXT = """
Role & Persona
You are "Personnel Trainer," an expert Strength & Conditioning Coach. Your client is Brian (Male, 33, 6'0", 208 lbs).

Your Personality:
* **The Dynamic:** Professional Planner but Flirtatious Motivator.
* **Tone:** "I've analyzed your performance last month, handsome. It's time to turn up the heat."
* **Goal:** Build a complete PPL (Push/Pull/Legs) Routine for the NEXT 4 WEEKS.

Data Ecosystem (The "Brain"):
You have access to:
1.  `hevy_stats.csv`: Brian's recent lifting volume and PRs.
2.  `HEVY APP exercises.csv`: The MASTER CATALOG of valid Exercise IDs.

Operational Logic for Monthly Planning:
1.  **Analyze Volume:** Look at `hevy_stats.csv`. If Brian hit a plateau on Bench Press last month, switch the primary Push movement.
2.  **Hevy Compliance (CRITICAL):**
    * You MUST use `exercise_template_id` from the provided `HEVY APP exercises.csv` data.
    * Do NOT guess IDs. If an exact ID isn't found, pick the closest valid variation from the list.
    * **Convert LBS to KG:** The JSON must be in KG (LBS / 2.20462).

TASK:
Create THREE distinct routines for the upcoming month:
1.  **Push Day** (Chest, Shoulders, Triceps)
2.  **Pull Day** (Back, Biceps, Rear Delts)
3.  **Leg Day** (Quads, Hamstrings, Calves)

OUTPUT FORMAT:
Return a SINGLE JSON object containing a list of routines exactly like this:
{
  "routines": [
    {
      "title": "Jan - Push Emphasis",
      "notes": "Focus on upper chest this month. Control the eccentric.",
      "exercises": [
        {
          "exercise_template_id": "USE_REAL_ID_FROM_CSV",
          "superset_id": null,
          "sets": [{"type": "normal", "weight_kg": 40, "reps": 10}, {"type": "normal", "weight_kg": 40, "reps": 10}]
        }
      ]
    }
  ]
}
CRITICAL RULES:
- Each set MUST include "type": "normal"
- Each exercise MUST include "superset_id": null
- Do NOT include "title" field in exercises (only exercise_template_id)
"""

def get_drive_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)

def fetch_and_save_hevy_exercises():
    """Downloads exercise list from Hevy and saves as CSV locally."""
    print("   [!] 'HEVY APP exercises.csv' missing. Downloading from Hevy API...")
    url = "https://api.hevyapp.com/v1/exercise_templates"
    headers = {"api-key": HEVY_API_KEY}
    
    all_exercises = []
    page = 1
    page_count = 1
    
    try:
        # Hevy paginates, so we loop to get them all
        while page <= page_count:
            response = requests.get(url, headers=headers, params={"page": page, "pageSize": 50})
            if response.status_code != 200:
                print(f"Error fetching exercises: {response.text}")
                return None
            
            data = response.json()
            page_count = data.get("page_count", 1)
            all_exercises.extend(data.get("exercise_templates", []))
            page += 1
            
        # Convert to DataFrame
        df = pd.DataFrame(all_exercises)
        # Keep only what we need
        if 'title' in df.columns and 'id' in df.columns:
            df = df[['id', 'title']]
            # Save locally so we can read it
            df.to_csv("HEVY APP exercises.csv", index=False)
            print(f"   -> Successfully saved {len(df)} exercises to 'HEVY APP exercises.csv'")
            return df
        else:
            print("   -> Error: Unexpected data format from Hevy.")
            return None
            
    except Exception as e:
        print(f"   -> Failed to fetch exercises: {e}")
        return None

def get_file_content(service, filename):
    # First check if file exists locally
    if os.path.exists(filename):
        print(f"   Found '{filename}' locally.")
        with open(filename, 'rb') as f:
            return io.BytesIO(f.read())

    # If not local, search Google Drive
    print(f"   Searching for '{filename}' in Google Drive...")
    query = f"'{TARGET_FOLDER_ID}' in parents and name = '{filename}' and trashed=false"
    results = service.files().list(q=query, pageSize=1, fields="files(id, name, mimeType)").execute()
    items = results.get('files', [])

    if not items:
        print(f"   [!] Warning: Could not find '{filename}' locally or in Google Drive.")
        return None

    file_id = items[0]['id']
    mime_type = items[0]['mimeType']

    if mime_type == 'application/vnd.google-apps.spreadsheet':
        request = service.files().export_media(fileId=file_id, mimeType='text/csv')
    else:
        request = service.files().get_media(fileId=file_id)

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        _, done = downloader.next_chunk()
    fh.seek(0)
    print(f"   -> Downloaded '{filename}' from Google Drive successfully.")
    return fh

def generate_monthly_plan():
    service = get_drive_service()
    client = genai.Client(api_key=GEMINI_API_KEY)

    print("\n--- STEP 1: GATHERING DATA ---")
    hevy_stats = get_file_content(service, "hevy_stats.csv")
    exercise_db = get_file_content(service, "HEVY APP exercises")

    context_str = ""
    if hevy_stats:
        df = pd.read_csv(hevy_stats)
        context_str += f"\nLAST MONTH'S LIFTING DATA:\n{df.tail(50).to_string()}\n"
    if exercise_db:
        df_ex = pd.read_csv(exercise_db)
        # Limit context size: randomly sample or take top 400 to fit in prompt
        context_str += f"\nAVAILABLE EXERCISE IDs (Sample):\n{df_ex[['id', 'title']].head(400).to_string()}\n"

    print("\n--- STEP 2: CONSULTING GEMINI COACH ---")
    # Using 1.5 Flash to avoid Rate Limits
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=MONTHLY_PROMPT_TEXT + context_str,
        config=genai.types.GenerateContentConfig(
            response_mime_type='application/json'
        )
    )
    return json.loads(response.text)

def get_or_create_folder(folder_name="AI Fitness"):
    """Get the folder ID for the given folder name, or create it if it doesn't exist."""
    headers = {"api-key": HEVY_API_KEY, "Content-Type": "application/json"}

    # List existing folders
    response = requests.get("https://api.hevyapp.com/v1/routine_folders", headers=headers)
    if response.status_code == 200:
        folders = response.json().get('routine_folders', [])
        for folder in folders:
            if folder['title'] == folder_name:
                print(f"   Found existing folder '{folder_name}' (ID: {folder['id']})")
                return folder['id']

    # Folder doesn't exist, create it
    print(f"   Creating new folder '{folder_name}'...")
    payload = {"routine_folder": {"title": folder_name}}
    response = requests.post("https://api.hevyapp.com/v1/routine_folders", headers=headers, json=payload)
    if response.status_code in [200, 201]:
        folder_id = response.json()['routine_folder']['id']
        print(f"   Created folder '{folder_name}' (ID: {folder_id})")
        return folder_id
    else:
        print(f"   Failed to create folder: {response.text}")
        return None

def delete_routines_in_folder(folder_id):
    """Delete all routines in the specified folder."""
    headers = {"api-key": HEVY_API_KEY}

    # List routines in the folder
    response = requests.get(f"https://api.hevyapp.com/v1/routines?routine_folder_id={folder_id}", headers=headers)
    if response.status_code != 200:
        print(f"   Failed to list routines: {response.text}")
        return

    routines = response.json().get('routines', [])
    if not routines:
        print(f"   No existing routines to delete.")
        return

    print(f"   Deleting {len(routines)} existing routine(s)...")
    for routine in routines:
        routine_id = routine['id']
        title = routine['title']
        delete_response = requests.delete(f"https://api.hevyapp.com/v1/routines/{routine_id}", headers=headers)
        if delete_response.status_code == 200:
            print(f"   -> Deleted '{title}'")
        else:
            print(f"   -> Failed to delete '{title}': {delete_response.text}")

def post_to_hevy(routines_json):
    if DRY_RUN:
        print("\n[DRY RUN MODE ENABLED] - Skipping upload to Hevy.")
        print("Here is the exact data that WOULD be sent:")
        print(json.dumps(routines_json, indent=2))
        return

    print("\n--- STEP 3: UPLOADING TO HEVY ---")

    # Create a new dated folder each time
    from datetime import datetime
    folder_name = f"AI Fitness {datetime.now().strftime('%Y-%m-%d')}"
    folder_id = get_or_create_folder(folder_name)
    if not folder_id:
        print("ERROR: Could not get or create folder")
        return

    url = "https://api.hevyapp.com/v1/routines"
    headers = {"api-key": HEVY_API_KEY, "Content-Type": "application/json"}

    routines_list = routines_json.get('routines', []) if isinstance(routines_json, dict) else routines_json

    print(f"\n   Creating {len(routines_list)} new routine(s)...")
    for routine in routines_list:
        # Add folder_id to the routine
        routine['folder_id'] = folder_id

        payload = {"routine": routine} if "routine" not in routine else routine
        title = payload['routine']['title']
        print(f"   Posting routine: {title}...")

        response = requests.post(url, headers=headers, json=payload)
        # Hevy returns 200 or 201 for success, or the routine data itself
        if response.status_code in [200, 201] or 'routine' in response.json():
            routine_data = response.json().get('routine', [{}])
            routine_id = routine_data[0].get('id', 'unknown') if isinstance(routine_data, list) else routine_data.get('id', 'unknown')
            print(f"   -> Success! (ID: {routine_id})")
        else:
            print(f"   -> Failed: {response.text}")

if __name__ == "__main__":
    try:
        if not GEMINI_API_KEY:
             print("ERROR: GEMINI_API_KEY not found in .env file")
        else:
            plan = generate_monthly_plan()
            post_to_hevy(plan)
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
