# AI Fitness Dashboard

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%20%7C%20Linux%20%7C%20Windows-green)

**Your personal fitness command center. Automate data collection. Visualize progress. Generate AI-powered workout plans.**

This project creates a comprehensive fitness tracking system that automatically aggregates your biometrics (Garmin) and weightlifting data (Hevy), displays them in a real-time dashboard, and uses AI (Google Gemini) to generate personalized workout routines.

---

## Features

### Dashboard
- **Training Analytics** - Volume progression, muscle group distribution, workout history
- **Recovery Metrics** - Sleep scores, HRV, weight trends, resting heart rate
- **Multi-Sport Cardio** - Running, cycling, swimming with sport-specific metrics
- **System Monitoring** - Task status, cron jobs, system vitals
- **Trend Lines** - Smooth rolling averages overlay on charts

### Data Sync
- **Garmin Connect** - Sleep, HRV, weight, body composition, SpO2, respiration, VO2 Max
- **Hevy App** - Workouts, exercises, sets, reps, RPE
- **Multi-Sport Activities** - Running, cycling, swimming, hiking, and more
  - Running: Pace, distance, HR zones, cadence, training effect
  - Cycling: Speed, power (watts), cadence, elevation gain
  - Swimming: Stroke count, laps, pool length

### AI Integration
- **Gemini AI Coach** - Generates personalized 4-week PPL routines
- **Auto-Upload** - Pushes AI-generated routines directly to Hevy app
- **Smart Context** - Uses your training history and recovery data

---

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/johnson4601/AI_Fitness.git
cd AI_Fitness

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Run interactive setup
python3 setup.py
```

The setup wizard will guide you through:
- Installing dependencies
- Configuring Garmin, Hevy, and Gemini integrations
- Setting up scheduled tasks
- Configuring dashboard autostart

### 2. Start Dashboard

```bash
streamlit run dashboard_local_server.py
```

Access at: `http://localhost:8501` (or `http://<pi-ip>:8501` from other devices)

---

## Project Structure

```
AI_Fitness/
├── setup.py                  # Interactive setup wizard (START HERE)
├── dashboard_local_server.py # Streamlit dashboard
├── .env                      # Configuration (created by setup.py)
│
├── Daily Scripts (Cron)
│   ├── daily_garmin_health.py      # Health metrics sync
│   ├── daily_garmin_activities.py  # All cardio activities (run/cycle/swim)
│   └── daily_hevy_workouts.py      # Workout sync
│
├── History Import
│   ├── history_garmin_import.py     # Bulk import Garmin health history
│   ├── history_garmin_activities.py # Bulk import all activities (run/cycle/swim)
│   ├── history_hevy_import.py       # Bulk import Hevy history
│   └── update_yesterday_garmin.py   # Fix incomplete daily data
│
├── AI Coach
│   ├── Gemini_Hevy.py           # AI routine generator
│   └── MONTHLY_PROMPT_TEXT.txt  # AI personality config
│
├── Auth
│   ├── setup_garmin_login.py    # Garmin authentication
│   ├── .garth/                  # Garmin tokens (auto-created)
│   ├── credentials.json         # Google OAuth (you provide)
│   └── token.pickle             # Google tokens (auto-created)
│
└── requirements.txt          # Python dependencies
```

---

## Configuration

### Environment Variables (.env)

The setup wizard creates this automatically. Manual configuration:

```ini
# File Paths
SAVE_PATH=/home/pi/GDrive/Gemini Gems/Personal trainer
DRIVE_MOUNT_PATH=/home/pi/GDrive

# Garmin Connect
GARMIN_EMAIL=your_email@example.com
GARMIN_PASSWORD=your_password

# Hevy App (get from Hevy Settings > API)
HEVY_API_KEY=your_hevy_api_key

# Google Services
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_DRIVE_FOLDER_ID=your_folder_id

# System Settings
CHECK_MOUNT_STATUS=True
```

### Reconfigure Anytime

```bash
python3 setup.py
```

Your existing settings are preserved - just press Enter to keep current values.

---

## Raspberry Pi Setup

### Dashboard as a Service

```bash
# Copy service file
sudo cp ai-fitness-dashboard.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable ai-fitness-dashboard
sudo systemctl start ai-fitness-dashboard

# Check status
sudo systemctl status ai-fitness-dashboard
```

### Scheduled Tasks (Cron)

```bash
crontab -e
```

Add these lines:
```bash
# --- HOURLY DATA SYNC ---
# Garmin health sync (every hour at :30)
30 * * * * cd /home/pi/Documents/AI_Fitness && /usr/bin/python3 daily_garmin_health.py >> /home/pi/cron_log.txt 2>&1

# Hevy workout sync (every hour at :35)
35 * * * * cd /home/pi/Documents/AI_Fitness && /usr/bin/python3 daily_hevy_workouts.py >> /home/pi/cron_log.txt 2>&1

# Garmin activities sync (every hour at :40) - runs, cycling, swimming, etc.
40 * * * * cd /home/pi/Documents/AI_Fitness && /usr/bin/python3 daily_garmin_activities.py >> /home/pi/cron_log.txt 2>&1

# --- DAILY TASKS ---
# Update yesterday's Garmin data (6:00 AM - captures complete step counts)
0 6 * * * cd /home/pi/Documents/AI_Fitness && /usr/bin/python3 update_yesterday_garmin.py >> /home/pi/cron_log.txt 2>&1

# --- MONTHLY TASKS ---
# AI workout plan generation (1st of month at 1:00 AM)
0 1 1 * * cd /home/pi/Documents/AI_Fitness && ./venv/bin/python Gemini_Hevy.py >> /home/pi/cron_log.txt 2>&1

# --- ON REBOOT (optional - sync data after restart) ---
@reboot sleep 60 && cd /home/pi/Documents/AI_Fitness && /usr/bin/python3 daily_garmin_health.py >> /home/pi/cron_log.txt 2>&1
@reboot sleep 65 && cd /home/pi/Documents/AI_Fitness && /usr/bin/python3 daily_hevy_workouts.py >> /home/pi/cron_log.txt 2>&1
@reboot sleep 70 && cd /home/pi/Documents/AI_Fitness && /usr/bin/python3 daily_garmin_activities.py >> /home/pi/cron_log.txt 2>&1
```

### Google Drive Mount (rclone)

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure
rclone config

# Mount (add to /etc/fstab for boot)
rclone mount gdrive: /home/pi/GDrive --vfs-cache-mode writes &
```

---

## Windows Setup

### 1. Clone & Setup

```powershell
git clone https://github.com/johnson4601/AI_Fitness.git
cd AI_Fitness

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Run interactive setup
python setup.py
```

### 2. Environment Configuration

Update `.env` with Windows-style paths:

```ini
SAVE_PATH=C:\Users\YourName\Google Drive\Fitness Data
CHECK_MOUNT_STATUS=False
```

> **Note:** Set `CHECK_MOUNT_STATUS=False` on Windows - the mount check is Linux-specific.

### 3. Start Dashboard

```powershell
venv\Scripts\activate
streamlit run dashboard_local_server.py
```

Access at: `http://localhost:8501`

### 4. Scheduled Tasks (Windows Task Scheduler)

Open Task Scheduler (`taskschd.msc`) and create tasks for each script:

#### Hourly Data Sync (Garmin Health)

1. **Create Task** → Name: "AI Fitness - Garmin Health"
2. **Trigger** → Daily, repeat every 1 hour
3. **Action** → Start a program:
   - Program: `C:\Users\YourName\AI_Fitness\venv\Scripts\python.exe`
   - Arguments: `daily_garmin_health.py`
   - Start in: `C:\Users\YourName\AI_Fitness`

#### Daily Yesterday Sync (6 AM)

1. **Create Task** → Name: "AI Fitness - Yesterday Garmin"
2. **Trigger** → Daily at 6:00 AM
3. **Action** → Start a program:
   - Program: `C:\Users\YourName\AI_Fitness\venv\Scripts\python.exe`
   - Arguments: `update_yesterday_garmin.py`
   - Start in: `C:\Users\YourName\AI_Fitness`

#### Monthly AI Plan (1st of month)

1. **Create Task** → Name: "AI Fitness - Monthly AI Plan"
2. **Trigger** → Monthly, Day 1, at 1:00 AM
3. **Action** → Start a program:
   - Program: `C:\Users\YourName\AI_Fitness\venv\Scripts\python.exe`
   - Arguments: `Gemini_Hevy.py`
   - Start in: `C:\Users\YourName\AI_Fitness`

> **Tip:** Under "Conditions", uncheck "Start only if on AC power" for laptops.

### 5. Dashboard Autostart (Optional)

Create a batch file `start_dashboard.bat`:

```batch
@echo off
cd /d C:\Users\YourName\AI_Fitness
call venv\Scripts\activate
streamlit run dashboard_local_server.py
```

Add to Startup:
1. Press `Win + R`, type `shell:startup`
2. Create shortcut to `start_dashboard.bat`

### 6. Google Drive Sync

Windows options for Google Drive:

| Method | Description |
|--------|-------------|
| **Google Drive Desktop** | Native app, auto-syncs to `G:\My Drive` |
| **rclone** | Command-line, same as Linux setup |

If using Google Drive Desktop, update `.env`:
```ini
SAVE_PATH=G:\My Drive\Fitness Data
```

---

## Usage

### Initial Data Import

Before automation, backfill your history:

```bash
python3 history_hevy_import.py           # All past workouts
python3 history_garmin_import.py         # Past health metrics
python3 history_garmin_activities.py     # Past activities (runs, cycling, swimming)
```

### Import Flags

All history import scripts support these options:

```bash
# Import from specific date
python3 history_garmin_import.py 2024-01-01

# Force refresh - overwrite existing data with fresh data from source
python3 history_garmin_import.py --force

# Combine both
python3 history_garmin_import.py 2024-06-01 --force
```

| Flag | Behavior |
|------|----------|
| (none) | Skip existing dates, only add new |
| `--force` | Overwrite all data with fresh data from Garmin/Hevy |
| `--backfill` | Fill empty cells only (Garmin Health only) |

### Fixing Incomplete Step Counts

If your cron runs early in the day, step counts may be incomplete. The `update_yesterday_garmin.py` script fixes this by fetching yesterday's complete data:

```bash
# Manual run
python3 update_yesterday_garmin.py

# Recommended cron (runs at 6 AM to capture full previous day)
0 6 * * * cd /home/pi/Documents/AI_Fitness && /usr/bin/python3 update_yesterday_garmin.py >> /home/pi/cron_log.txt 2>&1
```

### Generate AI Workout Plan

```bash
python3 Gemini_Hevy.py
```

This analyzes your last 6 months of data and creates personalized routines uploaded to Hevy.

### Dashboard Controls

Access from **System & Tools** tab:
- **Run** buttons for manual task execution
- **Force Refresh** checkbox for re-syncing data
- **Restart Dashboard** / **Reboot System**
- **Configuration** panel to view settings
- **Monthly Prompt Editor** to customize AI coach

---

## AI Coach Prompt Examples

The `MONTHLY_PROMPT_TEXT.txt` file controls your AI coach's personality and training style. Here are templates for different user types:

### Powerlifter Focus

```
Role & Persona:
You are "Iron Protocol," an elite Powerlifting Coach specializing in peaking cycles. Your client is [Name] ([Gender], born [DOB], [Height]).
Your Personality: Data-driven, methodical, no-nonsense. You speak in percentages and RPE.

Context:
You are generating a JSON payload to program the user's "Hevy" workout tracker for the next 4 weeks.

Data Access:
1. `hevy_stats.csv`: Historical lift data.
2. `HEVY APP exercises.csv`: Master catalog of Exercise IDs.
3. `memory_log.csv`: Personal Records (PRs) and injuries.

Operational Logic:
1. REVIEW DATA: Analyze recent squat, bench, and deadlift performance.
2. IDENTIFY 1RM: Calculate estimated 1RM from recent sets using Epley formula.
3. PERIODIZATION: Program using percentage-based loading (Week 1: 70%, Week 2: 75%, Week 3: 80%, Week 4: Deload 60%).
4. COMPETITION PREP: Focus on singles and doubles in final week if peaking.
5. ACCESSORY WORK: Include targeted weak-point accessories (pause squats, pin press, deficit deadlifts).

CRITICAL LOAD INSTRUCTION:
- Use RPE-based autoregulation: Prescribe RPE 7-8 for volume, RPE 9 for intensity days.
- Include backoff sets after top singles/doubles.
- Prioritize the Big 3 with 2x weekly frequency minimum.

TASK:
Generate THREE routines:
1. "Squat Day - Volume"
2. "Bench Day - Intensity"
3. "Deadlift Day - Speed Work"
```

### Bodybuilding / Hypertrophy

```
Role & Persona:
You are "Aesthetic Architect," a classic bodybuilding coach focused on symmetry and size. Your client is [Name] ([Gender], born [DOB], [Height]).
Your Personality: Motivational, detail-oriented about mind-muscle connection, passionate about the pump.

Context:
You are generating a JSON payload to program the user's "Hevy" workout tracker for the next 4 weeks.

Data Access:
1. `hevy_stats.csv`: Historical lift data.
2. `HEVY APP exercises.csv`: Master catalog of Exercise IDs.
3. `memory_log.csv`: Personal Records (PRs) and injuries.

Operational Logic:
1. REVIEW DATA: Identify lagging muscle groups from training frequency and volume.
2. VOLUME TARGETS: Program 15-20 sets per muscle group per week.
3. REP RANGES: Compound movements 8-12 reps, isolation 12-20 reps.
4. TEMPO: Include slow eccentrics (3-1-1-0) for hypertrophy stimulus.
5. INTENSITY TECHNIQUES: Add drop sets, rest-pause, or supersets for lagging parts.

CRITICAL LOAD INSTRUCTION:
- Use progressive overload via reps first, then weight.
- Include 1-2 "feeder" sets before working sets.
- Prioritize stretch-position exercises (incline curls, RDLs, cable flyes).

TASK:
Generate a 6-day PPL split:
1. "Push A - Chest Emphasis"
2. "Pull A - Back Width"
3. "Legs A - Quad Focus"
4. "Push B - Shoulder Emphasis"
5. "Pull B - Back Thickness"
6. "Legs B - Hamstring/Glute Focus"
```

### Beginner / General Fitness

```
Role & Persona:
You are "Coach Fundamentals," a patient and encouraging trainer for beginners. Your client is [Name] ([Gender], born [DOB], [Height]).
Your Personality: Supportive, educational, focused on building habits and proper form.

Context:
You are generating a JSON payload to program the user's "Hevy" workout tracker for the next 4 weeks.

Data Access:
1. `hevy_stats.csv`: Historical lift data.
2. `HEVY APP exercises.csv`: Master catalog of Exercise IDs.
3. `memory_log.csv`: Personal Records (PRs) and injuries.

Operational Logic:
1. REVIEW DATA: Check for movement patterns already learned.
2. PROGRESSION: Add weight only when all sets hit target reps with good form.
3. EXERCISE SELECTION: Prioritize machines and guided movements over free weights initially.
4. FREQUENCY: Full body 3x per week for beginners.
5. REST: Ensure 48 hours between sessions for recovery.

CRITICAL LOAD INSTRUCTION:
- Keep RPE at 6-7 (2-3 reps in reserve) to build confidence.
- Use straight sets with consistent weight to master form.
- Include detailed notes explaining proper technique cues.

TASK:
Generate THREE full-body routines:
1. "Full Body A - Push Focus"
2. "Full Body B - Pull Focus"
3. "Full Body C - Leg Focus"
```

### Weight Loss / Recomposition

```
Role & Persona:
You are "Metabolic Coach," specializing in fat loss while preserving muscle. Your client is [Name] ([Gender], born [DOB], [Height]).
Your Personality: Energetic, accountability-focused, data-driven about NEAT and recovery.

Context:
You are generating a JSON payload to program the user's "Hevy" workout tracker for the next 4 weeks.

Data Access:
1. `hevy_stats.csv`: Historical lift data.
2. `HEVY APP exercises.csv`: Master catalog of Exercise IDs.
3. `memory_log.csv`: Personal Records (PRs) and injuries.
4. `garmin_stats.csv`: Steps, sleep, recovery metrics.

Operational Logic:
1. REVIEW DATA: Check daily steps, sleep quality, and caloric expenditure.
2. TRAINING STYLE: Circuit-style with shorter rest (45-60 sec) for metabolic effect.
3. STRENGTH PRESERVATION: Keep 2-3 heavy compound sets per workout.
4. SUPERSETS: Pair opposing muscle groups to maximize calorie burn.
5. CONDITIONING: Include finishers (farmer carries, sled pushes, battle ropes).

CRITICAL LOAD INSTRUCTION:
- Maintain intensity on compounds to preserve muscle during deficit.
- Use higher reps (12-15) on isolation for metabolic stress.
- Include active recovery movements between sets.

TASK:
Generate FOUR routines:
1. "Upper Body Circuit"
2. "Lower Body Circuit"
3. "Full Body Metabolic"
4. "Active Recovery / Mobility"
```

### Endurance Athlete (Hybrid Training)

```
Role & Persona:
You are "Hybrid Performance Coach," balancing strength with endurance performance. Your client is [Name] ([Gender], born [DOB], [Height]).
Your Personality: Scientific, periodization-focused, understands the interference effect.

Context:
You are generating a JSON payload to program the user's "Hevy" workout tracker for the next 4 weeks.

Data Access:
1. `hevy_stats.csv`: Historical lift data.
2. `HEVY APP exercises.csv`: Master catalog of Exercise IDs.
3. `garmin_runs.csv`: Running data (pace, HR zones, distance).
4. `garmin_stats.csv`: Recovery metrics (HRV, sleep, RHR).

Operational Logic:
1. REVIEW DATA: Analyze running volume and recovery status.
2. TIMING: Schedule strength on easy run days or separate by 6+ hours.
3. EXERCISE SELECTION: Focus on single-leg work, hip stability, core anti-rotation.
4. VOLUME: Keep strength sessions to 45 min max to avoid interference.
5. PERIODIZATION: Reduce strength volume during peak running weeks.

CRITICAL LOAD INSTRUCTION:
- Prioritize power and strength over hypertrophy (3-6 rep range).
- Include plyometrics for running economy (box jumps, bounds).
- Focus on posterior chain (glutes, hamstrings) for injury prevention.

TASK:
Generate TWO routines:
1. "Runner Strength A - Power Focus"
2. "Runner Strength B - Stability Focus"
```

---

## Dashboard Screenshots

### Training Tab
- Volume progression with trend lines
- Muscle group distribution (pie + bar charts)
- Cardio section with HR zones and pace trends

### Recovery Tab
- Body weight tracking
- Sleep score & HRV trends
- Daily steps and RHR

### System Tab
- Task status and scheduling
- System vitals (CPU, RAM, temp)
- Configuration management

---

## Troubleshooting

### Garmin Login Fails
```bash
rm -rf .garth
# Wait 15-30 minutes (Garmin rate limiting)
python3 setup_garmin_login.py
```

### Dashboard Won't Start
```bash
# Check logs
sudo journalctl -u ai-fitness-dashboard -f

# Restart service
sudo systemctl restart ai-fitness-dashboard
```

### Missing Data in Charts
- Check `.env` paths are correct
- Verify CSV files exist in `SAVE_PATH`
- Run daily scripts manually to test

### Date Format Errors
The system handles mixed date formats automatically. If issues persist:
```bash
# Check CSV format
head -5 /path/to/garmin_stats.csv
```

---

## API Keys & Accounts

| Service | Where to Get |
|---------|--------------|
| **Hevy API** | Hevy App → Settings → Account → API |
| **Gemini API** | https://aistudio.google.com/apikey |
| **Google Drive** | https://console.cloud.google.com (enable Drive API) |
| **Garmin** | Your existing Garmin Connect account |

---

## Tech Stack

- **Dashboard**: Streamlit + Plotly
- **Data**: Pandas, CSV storage
- **Garmin API**: garminconnect, garth
- **Hevy API**: REST API
- **AI**: Google Gemini (google-genai)
- **Scheduling**: Cron + systemd

---

## Contributing

Contributions welcome! Please check the [issues page](https://github.com/johnson4601/AI_Fitness/issues).

---
## ⚠️ Important Disclaimers

**1. Educational Use Only**
This repository is a proof-of-concept demonstrating how to build a data pipeline using Python, APIs, and LLMs. It is intended for personal educational use.

**2. Unofficial APIs**
This project uses the `garminconnect` Python library, which relies on scraping Garmin's endpoints. 
* **Risk:** This is not an official API. Garmin may block scripts or change their login flow at any time.
* **Safety:** Do not use this for commercial purposes. Use at your own risk.

**3. Health & Safety**
The workouts generated by the AI are based on general logic and your provided metrics. Always listen to your body and consult a medical professional before attempting high-intensity training.

## License

MIT License - see [LICENSE](LICENSE)

---

**Built for the data-driven athlete**
