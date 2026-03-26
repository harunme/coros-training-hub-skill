---
name: coros-training-hub
description: "从 COROS 高驰训练中心获取用户的运动数据（跑步、健走、越野跑等）和训练日程计划，包括距离、配速、心率、训练负荷等指标，以及未来训练计划安排。当用户询问跑步数据、训练记录、高驰运动历史、训练计划、训练日程、训练模式分析、本周跑量、训练趋势，或需要分析训练效果时触发。"
---

# COROS Training Hub

从 COROS 高驰训练中心获取并展示用户的运动数据。

## 工作流

### Step 1 — 获取 accessToken

Token 需通过浏览器 DevTools 抓包获取（COROS 密码经过 bcrypt 前端哈希，无法在 Python 端直接复现）。

抓包步骤：

1. 打开 https://trainingcn.coros.com/login 并登录
2. 浏览器 F12 -> Network，找到 `login` 或 `account/login` 请求
3. 复制响应体中 `data.accessToken` 的值（约 32 字符，如 `LH6VND3MA20NQ63CHSKPMYR361T66IQY`）

### Step 2 — 调用脚本

```bash
python3 scripts/coros.py --token <accessToken> [--size <N>] [--page <N>]
```

可选参数：

- `--size <N>` — 每次获取的记录数，默认 20
- `--page <N>` — 页码，默认 1（最新数据）

### Step 3 — 展示结果

每条记录输出以下字段：

| 字段     | 说明                       |
| -------- | -------------------------- |
| 名称     | 运动名称（如"6k轻松跑"）   |
| 日期     | 运动日期（YYYY-MM-DD）     |
| 类型     | 跑步 / 越野跑 / 健走       |
| 距离     | 公里数（保留2位小数）      |
| 时长     | 总时长（H:MM:SS 或 MM:SS） |
| 配速     | 平均配速（min:sec /km）    |
| 平均心率 | bpm（如有）                |
| 最大心率 | bpm（如有）                |
| 平均步频 | spm（如有）                |
| 步数     | 总步数（如有）             |
| 训练负荷 | Training Load 数值         |
| 累计爬升 | 米                         |
| 累计下降 | 米                         |
| 热量     | 千卡（如有）               |
| 设备     | 手表型号                   |

## 字段换算规则

- `avgSpeed`：秒/公里 → `min:sec/km`
- `distance`：米 → 公里
- `totalTime`：秒 → `H:MM:SS`
- 数据按时间倒序排列，第1条为最新记录

## API 端点

- 登录：`POST https://teamcnapi.coros.com/account/login`（仅浏览器抓包用）
- 运动数据：`GET https://teamcnapi.coros.com/activity/query`
  - Header：`accesstoken: <accessToken>`（小写，非 Authorization）
  - 参数：`size`, `pageNumber`, `modeList`
- 训练日程：`GET https://teamcnapi.coros.com/training/schedule/query`
  - Header：`accesstoken: <accessToken>`（小写）
  - 参数：`startDate`（YYYYMMDD 格式，如 20260420）, `endDate`（YYYYMMDD 格式）, `supportRestExercise`（传 1）

## 训练日程查询

当用户询问训练计划、训练日程、接下来几天的训练安排、本周/本月训练计划时触发。

调用方式：

```bash
python3 scripts/coros.py --token <accessToken> schedule --start <YYYYMMDD> --end <YYYYMMDD>
```

参数说明：

- 子命令：`schedule`（必填）
- `--start`：查询开始日期（必填，YYYYMMDD，如 20260420）
- `--end`：查询结束日期（必填，YYYYMMDD，如 20260510）

日程展示字段：

| 字段     | 说明                             |
| -------- | -------------------------------- |
| 计划名称 | 整体计划名（如"全马330计划"）    |
| 日期     | 计划日期（YYYY-MM-DD + 星期）    |
| 状态     | 已完成 / 未开始 / 进行中         |
| 训练内容 | 当日训练项目（热身/主训练/拉伸） |
| 预计距离 | 计划总距离（米）                 |
| 预计时长 | 预计时长（秒 → H:MM:SS）         |
| 训练负荷 | Training Load 数值               |
| 赛事标记 | 如有"比赛"等事件标注             |

每周汇总展示：

- 本周计划总距离、总时长、总训练负荷
- 与上周对比（提升/下降百分比）

解析规则：

- `happenDay`：计划日期（YYYYMMDD 整数）
- `executeStatus`：0=未开始，1=已完成
- `exerciseType`：1=热身，2=主训练，3=拉伸
- `targetType=5`：距离类目标（米），`targetType=2`：时间类目标（秒）
- `weekStages`：每周汇总，含计划距离/时长/训练负荷

## 训练模式分析

当用户想了解近期训练规律、跑量趋势、配速分布、心率区间、周频次等时触发。不依赖训练日程 API，从近期运动记录实时分析。

调用方式：

```bash
python3 scripts/coros.py --token <accessToken> analyze [--days <N>] [--max-hr <N>]
```

参数说明：

- `--days`：分析天数窗口（默认 28 天）
- `--max-hr`：最大心率（默认 190，用于心率区间计算）

分析内容：

- **概览**：总跑量、总时长、总训练负荷、场均跑量、最长跑
- **周频次**：训练周期和场均周跑数
- **配速区间**：轻松跑 / 有氧跑 / 节奏跑 / 阈值跑 / 间歇（按实际配速划分）
- **心率区间**：Z1 恢复 ~ Z5 极限（按平均心率占最大心率比例划分）
- **周跑量趋势**：每周总距离和训练负荷变化

配速区间划分（秒/公里）：

- 轻松跑：≥ 6:00/km
- 有氧跑：5:00 ~ 6:00/km
- 节奏跑：4:30 ~ 5:00/km
- 阈值跑：4:00 ~ 4:30/km
- 间歇/比赛：< 4:00/km

心率区间划分（按最大心率比例）：

- Z1 < 60%、Z2 60-70%、Z3 70-80%、Z4 80-88%、Z5 > 88%
