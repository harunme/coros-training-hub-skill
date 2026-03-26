# COROS Training Hub

从 COROS 高驰训练中心获取并展示用户的运动数据。

## 安装

```bash
pip install requests
```

## 获取 accessToken

Token 需通过浏览器 DevTools 抓包获取（COROS 密码经过 bcrypt 前端哈希，无法在 Python 端直接复现）。

1. 打开 https://trainingcn.coros.com/login 并登录
2. 浏览器 F12 -> Application/Cookies，复制 `CPL-coros-token` 的值（约 32 字符）

## 使用方式

### 运动记录

```bash
python3 scripts/coros.py --token <accessToken> activities [--size N] [--page N]
```

- `--size`：每页记录数（默认 20）
- `--page`：页码，1 = 最新数据（默认 1）

### 训练日程

```bash
python3 scripts/coros.py --token <accessToken> schedule --start <YYYYMMDD> --end <YYYYMMDD>
```

- `--start`：必需，开始日期（如 20260420）
- `--end`：必需，结束日期（如 20260510）

## 输出

### 运动记录

| 字段     | 说明                       |
| -------- | -------------------------- |
| 名称     | 运动名称                   |
| 日期     | 日期（YYYY-MM-DD）         |
| 类型     | 跑步 / 越野跑 / 健走       |
| 距离     | 公里数（保留2位小数）       |
| 时长     | 总时长（H:MM:SS 或 MM:SS） |
| 配速     | 平均配速（min:sec /km）     |
| 平均心率 | bpm（如有）                |
| 最大心率 | bpm（如有）                |
| 平均步频 | spm（如有）                |
| 步数     | 总步数（如有）             |
| 训练负荷 | Training Load 数值         |
| 累计爬升 | 米                         |
| 累计下降 | 米                         |
| 热量     | 千卡                       |
| 设备     | 手表型号                   |

### 训练日程

| 字段         | 说明                             |
| ------------ | -------------------------------- |
| 计划名称     | 整体计划名                       |
| 计划序号     | 计划第 N 天                      |
| 日期         | 日期（YYYY-MM-DD + 星期）        |
| 状态         | 已完成 / 未开始                  |
| 训练项目     | 当日训练项目名称                 |
| 训练内容     | 热身 / 主训练 / 拉伸             |
| 预计距离     | 计划总距离（公里）               |
| 预计时长     | 预计时长                         |
| 训练负荷     | Training Load 数值               |
| 赛事标记     | 赛事/事件标注                    |

每周汇总展示本周计划距离、计划时长、计划训练负荷、ATI/CTI，以及已完成部分的实际距离和实际负荷。

## 字段换算规则

- `avgSpeed`：秒/公里 -> min:sec/km
- `distance`：米 -> 公里（保留2位小数）
- `totalTime`：秒 -> H:MM:SS 或 MM:SS
- 数据按时间倒序排列，第1条为最新记录
