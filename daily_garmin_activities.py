#!/usr/bin/env python3
"""
Daily Garmin Activities Sync

Fetches ALL cardio activities from Garmin Connect (running, cycling, swimming, etc.)
and saves them to garmin_activities.csv with sport-specific metrics.

Replaces the older daily_garmin_runs.py which only fetched running activities.
"""

import garth
from garminconnect import Garmin
from datetime import date, timedelta
import csv
import os
import sys
import platform
import json
from dotenv import load_dotenv

# 1. Load configuration
load_dotenv()

# 2. Platform-Aware Safety Check
check_mount = os.getenv("CHECK_MOUNT_STATUS", "False").lower() == "true"
drive_path = os.getenv("DRIVE_MOUNT_PATH", "/home/pi/google_drive")
is_windows = platform.system() == "Windows"

if check_mount and not is_windows:
    print(f"Safety Check: Verifying mount at {drive_path}...")
    if not os.path.ismount(drive_path):
        print(f"CRITICAL ERROR: Drive is not mounted at {drive_path}.")
        print("Stopping script to prevent writing to local storage.")
        sys.exit(1)
    else:
        print("Safety Check: PASSED. Drive is mounted.")
elif check_mount and is_windows:
    print("Note: Mount check skipped on Windows (not applicable).")

# --- CONFIGURATION ---
SAVE_PATH = os.getenv("SAVE_PATH")
CSV_FILE = os.path.join(SAVE_PATH, "garmin_activities.csv") if SAVE_PATH else "garmin_activities.csv"
TOKEN_DIR = ".garth"

# Activity type categories for filtering
CARDIO_TYPES = [
    'running', 'cycling', 'swimming', 'walking', 'hiking',
    'trail_running', 'treadmill_running', 'indoor_cycling', 'mountain_biking',
    'gravel_cycling', 'road_biking', 'lap_swimming', 'open_water_swimming',
    'elliptical', 'stair_climbing', 'rowing', 'indoor_rowing',
    'cross_country_skiing', 'skate_skiing', 'backcountry_skiing'
]

# CSV Headers - expanded schema for multi-sport
HEADERS = [
    # Identifiers
    "Date", "Time", "activityName", "sportType",
    # Duration & Distance
    "duration", "elapsedDuration", "movingDuration", "distance",
    # Speed/Pace
    "averageSpeed", "maxSpeed",
    # Heart Rate
    "averageHR", "maxHR",
    "hrTimeInZone_1", "hrTimeInZone_2", "hrTimeInZone_3", "hrTimeInZone_4", "hrTimeInZone_5",
    # Power (Cycling/Running)
    "avgPower", "maxPower", "normPower",
    # Cadence
    "avgCadence", "maxCadence",
    # Elevation (Cycling/Running/Hiking)
    "totalAscent", "totalDescent",
    # Running Specific
    "steps", "avgStrideLength",
    # Swimming Specific
    "avgStrokes", "totalStrokes", "poolLength", "numLaps",
    # Training Metrics
    "calories", "trainingEffectLabel", "activityTrainingLoad",
    "aerobicEffect", "anaerobicEffect",
    # VO2 & Performance
    "vo2Max", "lactateThreshold",
    # Activity ID (for reference)
    "activityId"
]
# ---------------------


def safe_get(data, *keys, default=None):
    """Safely navigate nested dictionaries"""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data if data is not None else default


def get_sport_category(activity_type_key):
    """Categorize activity type into main sport categories"""
    if not activity_type_key:
        return "other"

    atype = activity_type_key.lower()

    if any(x in atype for x in ['run', 'treadmill']):
        return "running"
    elif any(x in atype for x in ['cycl', 'bik']):
        return "cycling"
    elif any(x in atype for x in ['swim', 'lap_swim', 'pool']):
        return "swimming"
    elif any(x in atype for x in ['walk', 'hik']):
        return "walking"
    elif any(x in atype for x in ['row']):
        return "rowing"
    elif any(x in atype for x in ['ski']):
        return "skiing"
    elif any(x in atype for x in ['elliptical', 'stair']):
        return "cardio_machine"
    else:
        return "other"


def extract_activity_data(act):
    """Extract all relevant fields from a Garmin activity"""

    start_local = act.get('startTimeLocal', '')
    date_str = start_local[:10] if start_local else ''
    time_str = start_local[11:] if len(start_local) > 11 else ''

    # Basic info
    title = act.get('activityName', 'Activity')
    atype_key = safe_get(act, 'activityType', 'typeKey', default='unknown')
    sport_type = get_sport_category(atype_key)

    # Duration & Distance
    duration = act.get('duration', 0)
    elapsed = act.get('elapsedDuration', 0)
    moving = act.get('movingDuration', 0)
    distance = act.get('distance', 0)  # meters

    # Speed
    avg_speed = act.get('averageSpeed', 0)  # m/s
    max_speed = act.get('maxSpeed', 0)

    # Heart Rate
    avg_hr = act.get('averageHR')
    max_hr = act.get('maxHR')

    # HR Zones (seconds in each zone)
    z1 = act.get('hrTimeInZone_1')
    z2 = act.get('hrTimeInZone_2')
    z3 = act.get('hrTimeInZone_3')
    z4 = act.get('hrTimeInZone_4')
    z5 = act.get('hrTimeInZone_5')

    # Power metrics (cycling/running power)
    avg_power = act.get('avgPower') or act.get('averagePower')
    max_power = act.get('maxPower')
    norm_power = act.get('normPower') or act.get('normalizedPower')

    # Cadence
    avg_cadence = act.get('averageCadence') or act.get('avgCadence')
    max_cadence = act.get('maxCadence')

    # Elevation
    total_ascent = act.get('elevationGain') or act.get('totalAscent')
    total_descent = act.get('elevationLoss') or act.get('totalDescent')

    # Running specific
    steps = act.get('steps')
    avg_stride = act.get('avgStrideLength')

    # Swimming specific
    avg_strokes = act.get('avgStrokes') or act.get('averageStrokes')
    total_strokes = act.get('strokes') or act.get('totalStrokes')
    pool_length = act.get('poolLength')
    num_laps = act.get('numLaps') or act.get('numberOfLaps')

    # Training metrics
    calories = act.get('calories')
    te_label = act.get('trainingEffectLabel')
    training_load = act.get('activityTrainingLoad')
    aerobic_effect = act.get('aerobicTrainingEffect')
    anaerobic_effect = act.get('anaerobicTrainingEffect')

    # Performance metrics
    vo2_max = act.get('vO2MaxValue') or act.get('vo2Max')
    lactate = act.get('lactateThresholdHeartRate')

    # Activity ID for reference
    activity_id = act.get('activityId')

    return [
        date_str, time_str, title, sport_type,
        duration, elapsed, moving, distance,
        avg_speed, max_speed,
        avg_hr, max_hr,
        z1, z2, z3, z4, z5,
        avg_power, max_power, norm_power,
        avg_cadence, max_cadence,
        total_ascent, total_descent,
        steps, avg_stride,
        avg_strokes, total_strokes, pool_length, num_laps,
        calories, te_label, training_load,
        aerobic_effect, anaerobic_effect,
        vo2_max, lactate,
        activity_id
    ]


def main():
    # 1. Load Existing IDs
    existing_ids = set()
    folder_path = os.path.dirname(CSV_FILE)
    if folder_path and not os.path.exists(folder_path):
        os.makedirs(folder_path)

    if os.path.isfile(CSV_FILE):
        try:
            with open(CSV_FILE, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) > 1:
                        existing_ids.add(f"{row[0]}_{row[1]}")  # date_time
        except Exception as e:
            print(f"Warning: Could not read existing file: {e}")

    # 2. Login
    try:
        garth.resume(TOKEN_DIR)
        api = Garmin("dummy", "dummy")
        api.garth = garth.client
    except Exception as e:
        print(f"Login Error: {e}")
        return

    # 3. Check Last 3 Days for ALL activity types
    today = date.today()
    start_check = today - timedelta(days=3)

    print(f"Checking activities from {start_check}...")

    try:
        # Fetch ALL activities (no type filter)
        activities = api.get_activities_by_date(start_check.isoformat(), today.isoformat())

        new_rows = []
        if activities:
            for act in activities:
                start_local = act.get('startTimeLocal', '')
                date_str = start_local[:10]
                time_str = start_local[11:]

                sig = f"{date_str}_{time_str}"
                if sig in existing_ids:
                    continue

                # Extract activity data
                row = extract_activity_data(act)
                new_rows.append(row)

                # Log what we found
                sport = row[3]  # sportType
                print(f"   Found: {row[2]} ({sport}) on {date_str}")

        if new_rows:
            # Read existing rows
            existing_rows = []
            if os.path.isfile(CSV_FILE):
                with open(CSV_FILE, mode='r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader, None)  # Skip header
                    existing_rows = list(reader)

            # Combine and sort by date/time descending (newest first)
            all_rows = existing_rows + new_rows
            all_rows.sort(key=lambda x: (x[0], x[1]) if len(x) > 1 else ('', ''), reverse=True)

            # Rewrite entire file
            with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(HEADERS)
                writer.writerows(all_rows)
            print(f"SUCCESS: Added {len(new_rows)} new activities. [Sorted newest to oldest]")
        else:
            print("No new activities found.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
