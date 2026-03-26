#!/usr/bin/env python3
"""
COROS Training Hub - 使用 accessToken 获取运动数据、训练日程和训练模式分析

用法:
    python3 coros.py --token <accessToken> activities [--size N] [--page N]
    python3 coros.py --token <accessToken> schedule --start <YYYYMMDD> --end <YYYYMMDD>
    python3 coros.py --token <accessToken> analyze [--days N] [--max-hr N]

accessToken 获取方式（浏览器 DevTools 抓包）:
    POST https://teamcnapi.coros.com/account/login
    请求体: {"account": "手机号", "accountType": 2, "p1": "...", "p2": "..."}
    响应体 data.accessToken 即为 token
"""

import argparse
import sys
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    print("需要安装 requests 库: pip install requests")
    sys.exit(1)

# API 配置
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
    """将 YYYYMMDD 整数或 Unix 时间戳转换为可读日期，含星期"""
    weekday_cn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

    # 优先用 startTime（Unix 时间戳，更精确）
    if start_time:
        try:
            dt = datetime.fromtimestamp(int(start_time))
            return f"{dt.year}-{dt.month:02d}-{dt.day:02d} {weekday_cn[dt.weekday()]}"
        except (ValueError, OSError):
            pass

    # 回退到 date 整数
    s = str(date_int)
    try:
        dt = datetime(int(s[:4]), int(s[4:6]), int(s[6:8]))
        return f"{s[:4]}-{s[4:6]}-{s[6:8]} {weekday_cn[dt.weekday()]}"
    except (IndexError, ValueError):
        return str(date_int)


def format_pace(seconds_per_km):
    """将秒/公里转换为 min:sec/km"""
    if not seconds_per_km or seconds_per_km <= 0:
        return "--:--"
    mins = int(seconds_per_km // 60)
    secs = int(seconds_per_km % 60)
    return f"{mins}:{secs:02d}"


def format_duration(seconds):
    """将秒数转换为 H:MM:SS 或 MM:SS"""
    if seconds is None or seconds < 0:
        return "--:--"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_distance(meters):
    """将米转换为公里，保留2位小数"""
    if meters is None:
        return "0.00"
    return f"{meters / 1000:.2f}"


def format_distance_raw(meters):
    """将米转换为公里（保留1位小数）"""
    if meters is None:
        return "0"
    return f"{meters / 1000:.1f}"


def exercise_type_name(exercise_type):
    """根据 exerciseType 返回中文名称"""
    mapping = {
        1: "热身",
        2: "主训练",
        3: "拉伸",
    }
    return mapping.get(exercise_type, f"类型{exercise_type}")


def format_target(target_type, target_value):
    """格式化目标值（根据 targetType 单位）"""
    if target_type == 2:  # 时间（秒）
        return format_duration(target_value)
    if target_type == 5:  # 距离（米）
        return f"{format_distance_raw(target_value)} km"
    if target_type == 1:  # 次数
        return str(target_value)
    return str(target_value)


def schedule_status(execute_status):
    """根据 executeStatus 返回中文状态"""
    mapping = {
        0: "未开始",
        1: "已完成",
    }
    return mapping.get(execute_status, str(execute_status))


def format_exercise_summary(bar_chart):
    """将 exerciseBarChart 格式化为一行简述"""
    if not bar_chart:
        return "无"
    parts = []
    for ex in bar_chart:
        name = ex.get("name", "?")
        etype = ex.get("exerciseType", 0)
        ttype = ex.get("targetType", 0)
        tval = ex.get("targetValue", 0)
        parts.append(f"{exercise_type_name(etype)} {name}({format_target(ttype, tval)})")
    return " / ".join(parts)


def format_schedule_entity(entity, programs_map):
    """将单个日程条目格式化为易读字符串"""
    happen_day = entity.get("happenDay", 0)
    day_no = entity.get("dayNo", 0)
    status = schedule_status(entity.get("executeStatus", 0))
    bar_chart = entity.get("exerciseBarChart", [])

    # 查找对应 program
    program_id = entity.get("planProgramId", "")
    program = programs_map.get(program_id, {})
    plan_distance = program.get("distance", 0) or entity.get("totalDistance", 0)
    duration = program.get("duration", 0)
    training_load = program.get("trainingLoad", 0)
    program_name = program.get("name", "未知")

    lines = []
    lines.append(f"  日期:       {format_date(happen_day)}")
    lines.append(f"  计划序号:   第 {day_no} 天")
    lines.append(f"  状态:       {status}")
    lines.append(f"  训练项目:   {program_name}")
    lines.append(f"  训练内容:   {format_exercise_summary(bar_chart)}")
    if plan_distance:
        lines.append(f"  预计距离:   {format_distance_raw(plan_distance)} km")
    if duration:
        lines.append(f"  预计时长:   {format_duration(duration)}")
    if training_load:
        lines.append(f"  训练负荷:   {training_load}")
    return "\n".join(lines)


def format_week_stage(stage):
    """将 weekStages 中的单周数据格式化"""
    first_day = stage.get("firstDayInWeek", 0)
    train_sum = stage.get("trainSum", {})
    sum_by_type = stage.get("sumByType", [])

    plan_distance = train_sum.get("planDistance", "0")
    plan_duration = train_sum.get("planDuration", 0)
    plan_load = train_sum.get("planTrainingLoad", 0)
    actual_distance = train_sum.get("actualDistance", "0")
    actual_load = train_sum.get("actualTrainingLoad", 0)
    plan_ati = train_sum.get("planAti", 0)
    plan_cti = train_sum.get("planCti", 0)

    # 转换计划距离字符串
    if isinstance(plan_distance, str):
        plan_dist_val = float(plan_distance.replace(",", "").replace("\"", ""))
    else:
        plan_dist_val = float(plan_distance)

    lines = []
    lines.append(f"  周起始:   {format_date(first_day)}")
    lines.append(f"  计划距离: {format_distance_raw(plan_dist_val)} km")
    lines.append(f"  计划时长: {format_duration(plan_duration)}")
    lines.append(f"  计划负荷: {plan_load}  |  ATI {plan_ati} / CTI {plan_cti}")
    if actual_load > 0:
        lines.append(f"  实际距离: {format_distance_raw(float(str(actual_distance).replace(',','').replace('"','')))} km")
        lines.append(f"  实际负荷: {actual_load}")
    return "\n".join(lines)


def fetch_schedule(token, start_date, end_date):
    """获取训练日程"""
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


# ---- 训练模式分析 ----

def pace_zone(sec_per_km):
    """根据配速判断训练区间"""
    if not sec_per_km or sec_per_km <= 0:
        return "未知"
    if sec_per_km >= 360:   # >= 6:00/km
        return "轻松跑"
    if sec_per_km >= 300:   # >= 5:00/km
        return "有氧跑"
    if sec_per_km >= 270:   # >= 4:30/km
        return "节奏跑"
    if sec_per_km >= 240:   # >= 4:00/km
        return "阈值跑"
    return "间歇/比赛"


def hr_zone(avg_hr, max_hr):
    """根据平均心率占最大心率比例判断区间（默认最大心率=220-年龄≈190）"""
    if not avg_hr or not max_hr or max_hr <= 0:
        return "未知"
    ratio = avg_hr / max_hr
    if ratio < 0.60:
        return "Z1 恢复"
    if ratio < 0.70:
        return "Z2 有氧"
    if ratio < 0.80:
        return "Z3  tempo"
    if ratio < 0.88:
        return "Z4 阈值"
    return "Z5 极限"


def week_key(date_int, start_time=None):
    """返回日期所属周起始日（YYYYMMDD），以周一为起始"""
    if start_time:
        try:
            dt = datetime.fromtimestamp(int(start_time))
        except (ValueError, OSError):
            s = str(date_int)
            dt = datetime(int(s[:4]), int(s[4:6]), int(s[6:8]))
    else:
        s = str(date_int)
        dt = datetime(int(s[:4]), int(s[4:6]), int(s[6:8]))
    # weekday(): Mon=0, Sun=6
    monday = dt - timedelta(days=dt.weekday())
    return int(monday.strftime("%Y%m%d"))


def analyze_activities(activities):
    """从运动记录列表中分析训练模式"""
    from datetime import timedelta

    # 按周分组
    weeks = {}
    pace_zones = {}
    hr_zones = {}
    total_distance = 0
    total_time = 0
    total_load = 0
    total_count = 0
    max_distance = 0
    max_distance_run = None
    load_trend = []   # (week_key, avg_load)

    for a in activities:
        sport_type = a.get("sportType", 100)
        mode       = a.get("mode", 0)
        name       = a.get("name", "未知")
        date_int   = a.get("date")
        start_time = a.get("startTime")
        distance   = float(a.get("distance") or 0)
        total_time_s = a.get("totalTime", 0)
        avg_speed  = a.get("avgSpeed", 0)    # 秒/公里
        avg_hr     = a.get("avgHr", 0)
        max_hr     = a.get("maxHr", 0) or 190
        training_load = a.get("trainingLoad", 0)
        ascent     = a.get("ascent", 0)

        if distance < 500:   # 过滤短距离
            continue

        wk = week_key(date_int, start_time)
        if wk not in weeks:
            weeks[wk] = {"count": 0, "distance": 0, "time": 0, "load": 0, "runs": []}
        weeks[wk]["count"] += 1
        weeks[wk]["distance"] += distance
        weeks[wk]["time"] += total_time_s
        weeks[wk]["load"] += training_load
        weeks[wk]["runs"].append(a)

        total_count += 1
        total_distance += distance
        total_time += total_time_s
        total_load += training_load

        if distance > max_distance:
            max_distance = distance
            max_distance_run = a

        # 配速区间
        pz = pace_zone(avg_speed)
        pace_zones[pz] = pace_zones.get(pz, 0) + 1

        # 心率区间
        hrz = hr_zone(avg_hr, max_hr)
        hr_zones[hrz] = hr_zones.get(hrz, 0) + 1

    # 周跑量趋势
    for wk in sorted(weeks.keys()):
        load_trend.append((wk, weeks[wk]["load"], weeks[wk]["distance"]))

    return {
        "weeks": weeks,
        "pace_zones": pace_zones,
        "hr_zones": hr_zones,
        "total_distance": total_distance,
        "total_time": total_time,
        "total_load": total_load,
        "total_count": total_count,
        "max_distance_run": max_distance_run,
        "load_trend": load_trend,
    }


def format_analysis(activities, max_hr=190):
    """将训练模式分析格式化为易读字符串"""
    from datetime import timedelta

    r = analyze_activities(activities)

    lines = []
    lines.append("=" * 50)
    lines.append("               训练模式分析报告")
    lines.append("=" * 50)

    if r["total_count"] == 0:
        lines.append("暂无足够的运动数据进行分析")
        return "\n".join(lines)

    # 总体概览
    lines.append(f"\n【概览】（共 {r['total_count']} 条有效跑步记录）")
    lines.append(f"  总跑量:   {r['total_distance']/1000:.1f} km")
    lines.append(f"  总时长:   {format_duration(r['total_time'])}")
    lines.append(f"  总训练负荷: {r['total_load']}")
    lines.append(f"  平均跑量/次: {r['total_distance']/r['total_count']/1000:.1f} km")
    if r['total_time'] > 0:
        lines.append(f"  平均配速: {format_pace(r['total_distance']/(r['total_time']/1000))} /km")

    # 最长跑
    if r["max_distance_run"]:
        lr = r["max_distance_run"]
        lr_dist = float(lr.get("distance") or 0)
        lr_date = format_date(lr.get("date"), lr.get("startTime"))
        lr_name = lr.get("name", "未知")
        lines.append(f"  最长跑:   {lr_dist/1000:.1f} km（{lr_date} {lr_name}）")

    # 周频次
    week_count = len(r["weeks"])
    avg_runs_per_week = r["total_count"] / max(week_count, 1)
    lines.append(f"  训练周期: {week_count} 周，场均 {avg_runs_per_week:.1f} 跑/周")

    # 配速区间分布
    if r["pace_zones"]:
        lines.append("\n【配速区间分布】")
        order = ["轻松跑", "有氧跑", "节奏跑", "阈值跑", "间歇/比赛", "未知"]
        zone_map = r["pace_zones"]
        for z in order:
            cnt = zone_map.get(z, 0)
            if cnt > 0:
                pct = cnt / r["total_count"] * 100
                lines.append(f"  {z}: {cnt} 次 ({pct:.0f}%)")

    # 心率区间分布
    if r["hr_zones"]:
        lines.append("\n【心率区间分布】（假设最大心率 190 bpm）")
        order = ["Z1 恢复", "Z2 有氧", "Z3  tempo", "Z4 阈值", "Z5 极限", "未知"]
        zone_map = r["hr_zones"]
        for z in order:
            cnt = zone_map.get(z, 0)
            if cnt > 0:
                pct = cnt / r["total_count"] * 100
                lines.append(f"  {z}: {cnt} 次 ({pct:.0f}%)")

    # 周跑量趋势
    if r["load_trend"]:
        lines.append("\n【周跑量趋势】")
        for wk, load, dist in r["load_trend"]:
            lines.append(f"  {format_date(wk)}: {dist/1000:.1f} km  负荷 {load}")

    return "\n".join(lines)


def sport_type_name(sport_type, mode):
    """根据运动类型返回中文名称"""
    mapping = {
        (100, 8):  "跑步",
        (100, 6):  "跑步",
        (100, 15): "越野跑",
        (100, 31): "健走",
        (102, 15): "越野跑",
        (900, 31): "健走",
    }
    return mapping.get((sport_type, mode), "跑步")


def format_activity(a):
    """将单条运动数据格式化为易读字符串"""
    sport_type = a.get("sportType", 100)
    mode       = a.get("mode", 0)
    name       = a.get("name", "未知")
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
    lines.append(f"  名称:     {name}")
    lines.append(f"  日期:     {format_date(date_int, start_time)}")
    lines.append(f"  类型:     {sport_type_name(sport_type, mode)}")
    lines.append(f"  距离:     {format_distance(distance)} km")
    lines.append(f"  时长:     {format_duration(total_time)}")
    lines.append(f"  配速:     {format_pace(avg_speed)} /km")
    if avg_hr:
        lines.append(f"  平均心率: {avg_hr} bpm")
    if max_hr:
        lines.append(f"  最大心率: {max_hr} bpm")
    if avg_cadence:
        lines.append(f"  平均步频: {avg_cadence} spm")
    if step:
        lines.append(f"  步数:     {step}")
    lines.append(f"  训练负荷: {training_load}")
    lines.append(f"  累计爬升: {ascent} m")
    lines.append(f"  累计下降: {descent} m")
    if calorie:
        # COROS 返回单位偏大 1000 倍
        lines.append(f"  热量:     {calorie // 1000:,} kcal")
    if device:
        lines.append(f"  设备:     {device}")
    return "\n".join(lines)


def fetch_activities(token, size=20, page=1, mode_list=""):
    """获取运动数据列表"""
    headers = {
        **BASE_HEADERS,
        "accesstoken": token,
    }
    params = {
        "size": size,
        "pageNumber": page,
        "modeList": mode_list,
    }
    resp = requests.get(API_ACTIVITY_URL, params=params, headers=headers)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(
        description="COROS Training Hub - 获取高驰运动数据"
    )
    parser.add_argument(
        "--token",
        required=True,
        help="COROS accessToken（从浏览器 DevTools 抓包获取）",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 运动数据查询
    act_parser = subparsers.add_parser("activities", help="查询运动记录")
    act_parser.add_argument("--size", type=int, default=20, help="每次获取的记录数（默认20）")
    act_parser.add_argument("--page", type=int, default=1, help="页码（默认1，即最新数据）")

    # 训练日程查询
    sch_parser = subparsers.add_parser("schedule", help="查询训练日程")
    sch_parser.add_argument("--start", required=True, help="开始日期（YYYYMMDD，如 20260420）")
    sch_parser.add_argument("--end", required=True, help="结束日期（YYYYMMDD，如 20260510）")

    # 训练模式分析
    ana_parser = subparsers.add_parser("analyze", help="从近期运动记录分析训练模式")
    ana_parser.add_argument("--days", type=int, default=28, help="分析天数窗口（默认28天）")
    ana_parser.add_argument("--max-hr", type=int, default=190, help="最大心率（默认190）")

    args = parser.parse_args()

    # 默认行为：查询运动数据（兼容旧用法）
    if args.command is None:
        command = "activities"
        args.size = vars(args).get("size", 20)
        args.page = vars(args).get("page", 1)
    else:
        command = args.command

    if command == "activities":
        _cmd_activities(args)
    elif command == "schedule":
        _cmd_schedule(args)
    elif command == "analyze":
        _cmd_analyze(args)


def _cmd_activities(args):
    """处理运动数据查询"""
    print(f"正在获取最近 {args.size} 条运动数据（第 {args.page} 页）...", file=sys.stderr)
    try:
        result = fetch_activities(args.token, size=args.size, page=args.page)
    except Exception as e:
        print(f"获取数据失败: {e}", file=sys.stderr)
        sys.exit(1)

    result_code = result.get("result", "")
    if result_code != "0000":
        print(f"API 返回错误: {result.get('message', result)}", file=sys.stderr)
        sys.exit(1)

    data        = result.get("data", {})
    total_count = data.get("count", 0)
    data_list   = data.get("dataList", [])

    if not data_list:
        print("暂无运动数据")
        return

    total_pages  = data.get("totalPage", 1)
    current_page = data.get("pageNumber", 1)

    print(
        f"\n共 {total_count} 条运动记录，第 {current_page}/{total_pages} 页\n",
        file=sys.stderr,
    )

    for i, activity in enumerate(data_list, 1):
        print(f"--- 记录 {i} ---")
        print(format_activity(activity))
        print()


def _cmd_schedule(args):
    """处理训练日程查询"""
    print(f"正在查询训练日程 {args.start} ~ {args.end}...", file=sys.stderr)
    try:
        result = fetch_schedule(args.token, args.start, args.end)
    except Exception as e:
        print(f"获取训练日程失败: {e}", file=sys.stderr)
        sys.exit(1)

    result_code = result.get("result", "")
    if result_code != "0000":
        print(f"API 返回错误: {result.get('message', result)}", file=sys.stderr)
        sys.exit(1)

    data = result.get("data", {})
    if not data:
        print("该时间段内暂无训练日程")
        return

    # 计划概览
    plan_name = data.get("name", "未知计划")
    sub_plans = data.get("subPlans", [])
    sub_plan_name = sub_plans[0].get("name", "") if sub_plans else ""
    start_day = data.get("startDay", 0)
    end_day = data.get("endDay", 0)
    total_day = data.get("totalDay", 0)

    print(f"\n{'='*50}")
    print(f"计划名称: {plan_name}")
    if sub_plan_name:
        print(f"子计划:   {sub_plan_name}")
    if start_day and end_day:
        print(f"计划周期: {format_date(start_day)} ~ {format_date(end_day)}（共 {total_day} 天）")
    print(f"{'='*50}\n")

    # 每周汇总
    week_stages = data.get("weekStages", [])
    if week_stages:
        print("【每周汇总】")
        for ws in week_stages:
            stage_num = ws.get("stage", 0)
            if stage_num > 0:
                stage_label = f"第 {stage_num} 周"
            else:
                stage_label = "其他周"
            print(f"--- {stage_label} ---")
            print(format_week_stage(ws))
            print()
        print()

    # 事件标记（比赛等）
    event_tags = data.get("eventTags", [])
    if event_tags:
        print("【赛事 / 事件】")
        for tag in event_tags:
            tag_day = tag.get("happenDay", 0)
            tag_name = tag.get("name", "")
            print(f"  {format_date(tag_day)} - {tag_name}")
        print()

    # 构建 program 映射
    programs = data.get("programs", [])
    programs_map = {p.get("idInPlan", ""): p for p in programs}

    # 日程列表
    entities = data.get("entities", [])
    if not entities:
        print("该时间段内暂无训练日程安排")
        return

    print(f"【训练日程】（共 {len(entities)} 天）")
    for i, entity in enumerate(entities, 1):
        print(f"\n--- 第 {i} 天 ---")
        print(format_schedule_entity(entity, programs_map))

    print()


def _cmd_analyze(args):
    """从近期运动记录分析训练模式"""
    days = args.days
    max_hr = args.max_hr

    # 计算时间窗口
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp()) + 86400

    print(f"正在分析最近 {days} 天的训练数据...", file=sys.stderr)

    # 分页获取所有记录（最多取 200 条）
    all_activities = []
    total_pages = 1
    for page in range(1, total_pages + 1):
        try:
            result = fetch_activities(args.token, size=50, page=page)
        except Exception as e:
            print(f"获取数据失败: {e}", file=sys.stderr)
            sys.exit(1)

        result_code = result.get("result", "")
        if result_code != "0000":
            print(f"API 返回错误: {result.get('message', result)}", file=sys.stderr)
            sys.exit(1)

        data = result.get("data", {})
        data_list = data.get("dataList", [])
        total_pages = data.get("totalPage", 1)

        # 过滤时间窗口内
        for a in data_list:
            st = a.get("startTime", 0)
            if st and st >= start_ts and st <= end_ts:
                all_activities.append(a)
            elif st and st < start_ts:
                # 已超出时间窗口，停止获取
                break

        if st and st < start_ts:
            break

    if not all_activities:
        print(f"最近 {days} 天内暂无运动数据（仅分析 ≥500m 的跑步记录）")
        return

    # 渲染分析报告
    print(format_analysis(all_activities, max_hr=max_hr))


if __name__ == "__main__":
    main()
