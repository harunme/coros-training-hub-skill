# COROS Training Hub

Fetch and display user's activity data and training schedules from COROS Training Hub.

## Setup

```bash
pip install requests
```

## Get accessToken

Token must be captured via browser DevTools (COROS password is hashed with bcrypt on the frontend and cannot be replicated in Python).

1. Open https://trainingcn.coros.com/login and log in
2. Browser F12 -> Application/Cookies, copy value of `CPL-coros-token` (~32 chars)

## Usage

### Activity Records

```bash
python3 scripts/coros.py --token <accessToken> activities [--size N] [--page N]
```

- `--size`: number of records per page (default: 20)
- `--page`: page number, 1 = most recent (default: 1)

### Training Schedule

```bash
python3 scripts/coros.py --token <accessToken> schedule --start <YYYYMMDD> --end <YYYYMMDD>
```

- `--start`: required, start date (e.g. 20260420)
- `--end`: required, end date (e.g. 20260510)

## Output

### Activity Records

| Field        | Description                          |
| ------------ | ------------------------------------ |
| Name         | Activity name                        |
| Date         | Date (YYYY-MM-DD)                    |
| Type         | Running / Trail Running / Walking     |
| Distance     | Kilometers (2 decimal places)        |
| Duration     | Total time (H:MM:SS or MM:SS)        |
| Pace         | Average pace (min:sec /km)           |
| Avg HR       | bpm (if available)                   |
| Max HR       | bpm (if available)                   |
| Avg Cadence  | spm (if available)                   |
| Steps        | Total steps (if available)            |
| Training Load| Training Load value                  |
| Ascent       | Meters                               |
| Descent      | Meters                               |
| Calories     | Kilocalories                         |
| Device       | Watch model                          |

### Training Schedule

| Field         | Description                                |
| ------------- | ------------------------------------------ |
| Plan Name     | Overall plan name                          |
| Day No.       | Day N of the plan                          |
| Date          | Date (YYYY-MM-DD + weekday)                |
| Status        | Completed / Not Started                    |
| Training Item | Day's training item name                   |
| Training Content | Warm-up / Main / Stretch               |
| Est. Distance | Planned total distance (km)                |
| Est. Duration | Planned duration                           |
| Training Load | Training Load value                        |
| Event Tag     | Event markers (e.g. race day)              |

Weekly summary shows planned distance, duration, training load, ATI/CTI, and completed actual distance and load.

## Field Conversion

- `avgSpeed`: sec/km -> min:sec/km
- `distance`: meters -> kilometers (2 decimal places)
- `totalTime`: seconds -> H:MM:SS or MM:SS
- Data ordered newest-first
