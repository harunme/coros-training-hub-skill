---
name: coros-training-hub
description: "Fetch user's activity data (running, hiking, trail running, etc.) and training schedules from COROS Training Hub, including distance, pace, heart rate, and training load. Triggered when user asks about running data, training records, COROS history, training plans, or schedules."
---

# COROS Training Hub

Fetch and display user's activity data and training schedules from COROS Training Hub.

## Workflow

### Step 1 — Get accessToken

Token must be captured via browser DevTools (COROS password is hashed with bcrypt on the frontend and cannot be replicated in Python).

Capture steps:

1. Open https://trainingcn.coros.com/login and log in
2. Browser F12 -> Application/Cookies, copy value of `CPL-coros-token` (~32 chars)

### Step 2 — Run the script

```bash
python3 scripts/coros.py --token <accessToken> activities [--size N] [--page N]
python3 scripts/coros.py --token <accessToken> schedule --start <YYYYMMDD> --end <YYYYMMDD>
```

### Step 3 — Output

#### Activity Records

| Field        | Description                          |
| ------------ | ------------------------------------ |
| Name         | Activity name (e.g. "6k Easy Run")    |
| Date         | Date (YYYY-MM-DD)                    |
| Type         | Running / Trail Running / Walking     |
| Distance     | Kilometers (2 decimal places)         |
| Duration     | Total time (H:MM:SS or MM:SS)        |
| Pace         | Average pace (min:sec /km)           |
| Avg HR       | bpm (if available)                   |
| Max HR       | bpm (if available)                   |
| Avg Cadence  | spm (if available)                   |
| Steps        | Total steps (if available)           |
| Training Load| Training Load value                  |
| Ascent       | Meters                               |
| Descent      | Meters                               |
| Calories     | Kilocalories                         |
| Device       | Watch model                          |

#### Training Schedule

| Field         | Description                                |
| ------------- | ------------------------------------------ |
| Plan Name     | Overall plan name (e.g. "Sub-3:30 Marathon")|
| Day No.       | Day N of the plan                          |
| Date          | Date (YYYY-MM-DD + weekday)                |
| Status        | Completed / Not Started                    |
| Training Item | Day's training item name                   |
| Training Content| Day's exercises (warmup/main/stretch)     |
| Est. Distance| Planned total distance (m -> km)            |
| Est. Duration| Planned duration (s -> H:MM:SS)             |
| Training Load | Training Load value                        |
| Event Tag     | Event markers (e.g. race day)              |

Weekly summary shows planned distance, duration, training load, ATI/CTI, and completed actual distance and load.

## Field Conversion Rules

- `avgSpeed`: sec/km -> `min:sec/km`
- `distance`: meters -> kilometers
- `totalTime`: seconds -> `H:MM:SS`
- Data ordered newest-first

## API Endpoints

- Activity data: `GET https://teamcnapi.coros.com/activity/query`
  - Header: `accesstoken: <accessToken>` (lowercase, not Authorization)
  - Params: `size`, `pageNumber`
- Training schedule: `GET https://teamcnapi.coros.com/training/schedule/query`
  - Header: `accesstoken: <accessToken>` (lowercase)
  - Params: `startDate` (YYYYMMDD, e.g. 20260420), `endDate` (YYYYMMDD), `supportRestExercise` (pass 1)

## Schedule Parsing Rules

- `happenDay`: planned date (YYYYMMDD integer)
- `executeStatus`: 0=Not Started, 1=Completed
- `exerciseType`: 1=Warm-up, 2=Main, 3=Stretch
- `targetType=5`: distance target (meters), `targetType=2`: time target (seconds)
- `weekStages`: weekly summary with planned distance/duration/load/ATI/CTI and actual completion data
