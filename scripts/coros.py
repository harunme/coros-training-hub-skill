#!/usr/bin/env python3
"""
COROS Training Hub - Fetch activity data and training schedules using accessToken.

Usage:
    python3 coros.py --token <accessToken> activities [--size N] [--page N]
    python3 coros.py --token <accessToken> schedule --start <YYYYMMDD> --end <YYYYMMDD>

Getting accessToken (browser DevTools):
    1. Open https://trainingcn.coros.com/login and log in
    2. Browser F12 -> Application/Cookies, copy value of `CPL-coros-token` (~32 chars)
"""

import argparse
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("requests library required: pip install requests")
    sys.exit(1)

# API configuration
API_ACTIVITY_URL = "https://teamcnapi.coros.com/activity/query"
API_SCHEDULE_URL = "https://teamcnapi.coros.com/training/schedule/query"

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Origin": "https://trainingcn.coros.com",
    "Referer": "https://trainingcn.coros.com/",
}


def format_date(date_int, start_time=None):
    """Convert YYYYMMDD int or Unix timestamp to readable date with weekday."""
    weekday_cn = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    if start_time:
        try:
            dt = datetime.fromtimestamp(int(start_time))
            return f"{dt.year}-{dt.month:02d}-{dt.day:02d} {weekday_cn[dt.weekday()]}"
        except (ValueError, OSError):
            pass

    s = str(date_int)
    try:
        dt = datetime(int(s[:4]), int(s[4:6]), int(s[6:8]))
        return f"{s[:4]}-{s[4:6]}-{s[6:8]} {weekday_cn[dt.weekday()]}"
    except (IndexError, ValueError):
        return str(date_int)


def format_pace(seconds_per_km):
    """Convert sec/km to min:sec/km."""
    if not seconds_per_km or seconds_per_km <= 0:
        return "--:--"
    mins = int(seconds_per_km // 60)
    secs = int(seconds_per_km % 60)
    return f"{mins}:{secs:02d}"


def format_duration(seconds):
    """Convert seconds to H:MM:SS or MM:SS."""
    if seconds is None or seconds < 0:
        return "--:--"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_distance(meters):
    """Convert meters to km with 2 decimal places."""
    if meters is None:
        return "0.00"
    return f"{meters / 1000:.2f}"


def format_distance_raw(meters):
    """Convert meters to km with 1 decimal place."""
    if meters is None:
        return "0"
    return f"{meters / 1000:.1f}"


def sport_type_name(sport_type, mode):
    """Return English sport type name."""
    mapping = {
        (100, 8):  "Running",
        (100, 6):  "Running",
        (100, 15): "Trail Running",
        (100, 31): "Walking",
        (102, 15): "Trail Running",
        (900, 31): "Walking",
    }
    return mapping.get((sport_type, mode), "Running")


def format_activity(a):
    """Format a single activity record into a readable string."""
    sport_type = a.get("sportType", 100)
    mode       = a.get("mode", 0)
    name       = a.get("name", "Unknown")
    date_int   = a.get("date")
    start_time = a.get("startTime")
    distance   = float(a.get("distance") or 0)
    total_time = a.get("totalTime", 0)
    avg_speed  = a.get("avgSpeed", 0)
    avg_hr     = a.get("avgHr", 0)
    max_hr     = a.get("maxHr", 0)
    training_load = a.get("trainingLoad", 0)
    ascent     = a.get("ascent", 0)
    descent    = a.get("descent", 0)
    calorie    = a.get("calorie", 0)
    device     = a.get("device", "")
    step       = a.get("step", 0)
    avg_cadence = a.get("avgCadence", 0)

    lines = []
    lines.append(f"  Name:         {name}")
    lines.append(f"  Date:         {format_date(date_int, start_time)}")
    lines.append(f"  Type:         {sport_type_name(sport_type, mode)}")
    lines.append(f"  Distance:     {format_distance(distance)} km")
    lines.append(f"  Duration:     {format_duration(total_time)}")
    lines.append(f"  Pace:         {format_pace(avg_speed)} /km")
    if avg_hr:
        lines.append(f"  Avg HR:       {avg_hr} bpm")
    if max_hr:
        lines.append(f"  Max HR:       {max_hr} bpm")
    if avg_cadence:
        lines.append(f"  Avg Cadence:  {avg_cadence} spm")
    if step:
        lines.append(f"  Steps:        {step}")
    lines.append(f"  Training Load: {training_load}")
    lines.append(f"  Ascent:       {ascent} m")
    lines.append(f"  Descent:      {descent} m")
    if calorie:
        lines.append(f"  Calories:     {calorie // 1000:,} kcal")
    if device:
        lines.append(f"  Device:       {device}")
    return "\n".join(lines)


def exercise_type_name(exercise_type):
    """Return English exercise type name."""
    mapping = {
        1: "Warm-up",
        2: "Main",
        3: "Stretch",
    }
    return mapping.get(exercise_type, f"Type {exercise_type}")


def format_target(target_type, target_value):
    """Format target value based on targetType unit."""
    if target_type == 2:  # time (seconds)
        return format_duration(target_value)
    if target_type == 5:  # distance (meters)
        return f"{format_distance_raw(target_value)} km"
    if target_type == 1:  # count
        return str(target_value)
    return str(target_value)


def schedule_status(execute_status):
    """Return English status from executeStatus."""
    mapping = {
        0: "Not Started",
        1: "Completed",
    }
    return mapping.get(execute_status, str(execute_status))


def format_exercise_summary(bar_chart):
    """Format exerciseBarChart into a single-line summary."""
    if not bar_chart:
        return "None"
    parts = []
    for ex in bar_chart:
        name = ex.get("name", "?")
        etype = ex.get("exerciseType", 0)
        ttype = ex.get("targetType", 0)
        tval = ex.get("targetValue", 0)
        parts.append(f"{exercise_type_name(etype)} {name}({format_target(ttype, tval)})")
    return " / ".join(parts)


def format_schedule_entity(entity, programs_map):
    """Format a single schedule entity into a readable string."""
    happen_day = entity.get("happenDay", 0)
    day_no = entity.get("dayNo", 0)
    status = schedule_status(entity.get("executeStatus", 0))
    bar_chart = entity.get("exerciseBarChart", [])

    program_id = entity.get("planProgramId", "")
    program = programs_map.get(program_id, {})
    plan_distance = program.get("distance", 0) or entity.get("totalDistance", 0)
    duration = program.get("duration", 0)
    training_load = program.get("trainingLoad", 0)
    program_name = program.get("name", "Unknown")

    lines = []
    lines.append(f"  Date:          {format_date(happen_day)}")
    lines.append(f"  Day No.:       Day {day_no}")
    lines.append(f"  Status:        {status}")
    lines.append(f"  Training Item: {program_name}")
    lines.append(f"  Content:       {format_exercise_summary(bar_chart)}")
    if plan_distance:
        lines.append(f"  Est. Distance: {format_distance_raw(plan_distance)} km")
    if duration:
        lines.append(f"  Est. Duration: {format_duration(duration)}")
    if training_load:
        lines.append(f"  Training Load: {training_load}")
    return "\n".join(lines)


def format_week_stage(stage):
    """Format a weekStages entry into a readable string."""
    first_day = stage.get("firstDayInWeek", 0)
    train_sum = stage.get("trainSum", {})

    plan_distance = train_sum.get("planDistance", "0")
    plan_duration = train_sum.get("planDuration", 0)
    plan_load = train_sum.get("planTrainingLoad", 0)
    actual_distance = train_sum.get("actualDistance", "0")
    actual_load = train_sum.get("actualTrainingLoad", 0)
    plan_ati = train_sum.get("planAti", 0)
    plan_cti = train_sum.get("planCti", 0)

    if isinstance(plan_distance, str):
        plan_dist_val = float(plan_distance.replace(",", "").replace('"', ""))
    else:
        plan_dist_val = float(plan_distance)

    lines = []
    lines.append(f"  Week Start:    {format_date(first_day)}")
    lines.append(f"  Plan Distance: {format_distance_raw(plan_dist_val)} km")
    lines.append(f"  Plan Duration: {format_duration(plan_duration)}")
    lines.append(f"  Plan Load:     {plan_load}  |  ATI {plan_ati} / CTI {plan_cti}")
    if actual_load > 0:
        lines.append(f"  Actual Dist:   {format_distance_raw(float(str(actual_distance).replace(',','').replace('"','')))} km")
        lines.append(f"  Actual Load:   {actual_load}")
    return "\n".join(lines)


def fetch_activities(token, size=20, page=1):
    """Fetch activity data list."""
    headers = {
        **BASE_HEADERS,
        "accesstoken": token,
    }
    params = {
        "size": size,
        "pageNumber": page,
    }
    resp = requests.get(API_ACTIVITY_URL, params=params, headers=headers)
    resp.raise_for_status()
    return resp.json()


def fetch_schedule(token, start_date, end_date):
    """Fetch training schedule."""
    headers = {
        **BASE_HEADERS,
        "accesstoken": token,
    }
    params = {
        "startDate": start_date,
        "endDate": end_date,
        "supportRestExercise": 1,
    }
    resp = requests.get(API_SCHEDULE_URL, params=params, headers=headers)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(
        description="COROS Training Hub - Fetch COROS activity data and training schedules"
    )
    parser.add_argument(
        "--token",
        required=True,
        help="COROS accessToken (from browser DevTools Application/Cookies, CPL-coros-token)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="subcommands")

    # Activity data query
    act_parser = subparsers.add_parser("activities", help="Query activity records")
    act_parser.add_argument("--size", type=int, default=20, help="Records per page (default: 20)")
    act_parser.add_argument("--page", type=int, default=1, help="Page number, 1 = most recent (default: 1)")

    # Training schedule query
    sch_parser = subparsers.add_parser("schedule", help="Query training schedule")
    sch_parser.add_argument("--start", required=True, help="Start date (required, YYYYMMDD, e.g. 20260420)")
    sch_parser.add_argument("--end", required=True, help="End date (required, YYYYMMDD, e.g. 20260510)")

    args = parser.parse_args()

    if args.command == "activities":
        _cmd_activities(args)
    elif args.command == "schedule":
        _cmd_schedule(args)


def _cmd_activities(args):
    """Handle activity data query."""
    print(f"Fetching {args.size} activities (page {args.page})...", file=sys.stderr)
    try:
        result = fetch_activities(args.token, size=args.size, page=args.page)
    except Exception as e:
        print(f"Failed to fetch data: {e}", file=sys.stderr)
        sys.exit(1)

    result_code = result.get("result", "")
    if result_code != "0000":
        print(f"API error: {result.get('message', result)}", file=sys.stderr)
        sys.exit(1)

    data        = result.get("data", {})
    total_count = data.get("count", 0)
    data_list   = data.get("dataList", [])

    if not data_list:
        print("No activity records found.")
        return

    total_pages  = data.get("totalPage", 1)
    current_page = data.get("pageNumber", 1)

    print(
        f"\n{total_count} activity records, page {current_page}/{total_pages}\n",
        file=sys.stderr,
    )

    for i, activity in enumerate(data_list, 1):
        print(f"--- Record {i} ---")
        print(format_activity(activity))
        print()


def _cmd_schedule(args):
    """Handle training schedule query."""
    print(f"Querying training schedule {args.start} ~ {args.end}...", file=sys.stderr)
    try:
        result = fetch_schedule(args.token, args.start, args.end)
    except Exception as e:
        print(f"Failed to fetch schedule: {e}", file=sys.stderr)
        sys.exit(1)

    result_code = result.get("result", "")
    if result_code != "0000":
        print(f"API error: {result.get('message', result)}", file=sys.stderr)
        sys.exit(1)

    data = result.get("data", {})
    if not data:
        print("No training schedule found in this period.")
        return

    plan_name = data.get("name", "Unknown Plan")
    sub_plans = data.get("subPlans", [])
    sub_plan_name = sub_plans[0].get("name", "") if sub_plans else ""
    start_day = data.get("startDay", 0)
    end_day = data.get("endDay", 0)
    total_day = data.get("totalDay", 0)

    print(f"\n{'='*50}")
    print(f"Plan Name:  {plan_name}")
    if sub_plan_name:
        print(f"Sub-plan:   {sub_plan_name}")
    if start_day and end_day:
        print(f"Period:     {format_date(start_day)} ~ {format_date(end_day)} ({total_day} days)")
    print(f"{'='*50}\n")

    week_stages = data.get("weekStages", [])
    if week_stages:
        print("[Weekly Summary]")
        for ws in week_stages:
            stage_num = ws.get("stage", 0)
            stage_label = f"Week {stage_num}" if stage_num > 0 else "Other"
            print(f"--- {stage_label} ---")
            print(format_week_stage(ws))
            print()
        print()

    event_tags = data.get("eventTags", [])
    if event_tags:
        print("[Events]")
        for tag in event_tags:
            tag_day = tag.get("happenDay", 0)
            tag_name = tag.get("name", "")
            print(f"  {format_date(tag_day)} - {tag_name}")
        print()

    programs = data.get("programs", [])
    programs_map = {p.get("idInPlan", ""): p for p in programs}

    entities = data.get("entities", [])
    if not entities:
        print("No training schedule安排 found.")
        return

    print(f"[Training Schedule] ({len(entities)} days)")
    for i, entity in enumerate(entities, 1):
        print(f"\n--- Day {i} ---")
        print(format_schedule_entity(entity, programs_map))

    print()


if __name__ == "__main__":
    main()
