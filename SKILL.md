---
name: coros-training-hub
description: "从 COROS 高驰训练中心获取用户的运动数据（跑步、健走、越野跑等）和训练日程计划，包括距离、配速、心率、训练负荷等指标。当用户询问跑步数据、训练记录、高驰运动历史、训练计划、训练日程时触发。"
---

# COROS Training Hub

从 COROS 高驰训练中心获取并展示用户的运动数据。

## 工作流

### Step 1 — 获取 accessToken

Token 需通过浏览器 DevTools 抓包获取（COROS 密码经过 bcrypt 前端哈希，无法在 Python 端直接复现）。

抓包步骤：

1. 打开 https://trainingcn.coros.com/login 并登录
2. 浏览器 F12 -> Application/Cookies，复制 `CPL-coros-token` 的值（约 32 字符）

### Step 2 — 调用脚本

```bash
python3 scripts/coros.py --token <accessToken> activities [--size N] [--page N]
python3 scripts/coros.py --token <accessToken> schedule --start <YYYYMMDD> --end <YYYYMMDD>
```

### Step 3 — 展示结果

#### 运动记录

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
| 热量     | 千卡                       |
| 设备     | 手表型号                   |

#### 训练日程

| 字段     | 说明                             |
| -------- | -------------------------------- |
| 计划名称 | 整体计划名（如"全马330计划"）    |
| 计划序号 | 计划第 N 天                      |
| 日期     | 计划日期（YYYY-MM-DD + 星期）    |
| 状态     | 已完成 / 未开始                  |
| 训练项目 | 当日训练项目名称                 |
| 训练内容 | 当日训练项目（热身/主训练/拉伸） |
| 预计距离 | 计划总距离（米 → 公里）          |
| 预计时长 | 预计时长（秒 → H:MM:SS）         |
| 训练负荷 | Training Load 数值               |
| 赛事标记 | 如有"比赛"等事件标注             |

每周汇总展示本周计划距离、计划时长、计划训练负荷、ATI/CTI，以及已完成部分的实际距离和实际负荷。

## 字段换算规则

- `avgSpeed`：秒/公里 → `min:sec/km`
- `distance`：米 → 公里
- `totalTime`：秒 → `H:MM:SS`
- 数据按时间倒序排列，第1条为最新记录

## API 端点

- 运动数据：`GET https://teamcnapi.coros.com/activity/query`
  - Header：`accesstoken: <accessToken>`（小写，非 Authorization）
  - 参数：`size`, `pageNumber`
- 训练日程：`GET https://teamcnapi.coros.com/training/schedule/query`
  - Header：`accesstoken: <accessToken>`（小写）
  - 参数：`startDate`（YYYYMMDD 格式，如 20260420）, `endDate`（YYYYMMDD 格式）, `supportRestExercise`（传 1）

## 日程解析规则

- `happenDay`：计划日期（YYYYMMDD 整数）
- `executeStatus`：0=未开始，1=已完成
- `exerciseType`：1=热身，2=主训练，3=拉伸
- `targetType=5`：距离类目标（米），`targetType=2`：时间类目标（秒）
- `weekStages`：每周汇总，含计划距离/时长/训练负荷/ATI/CTI 及实际完成数据
