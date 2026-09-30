# FitLoop MVP：产品与技术蓝图

## 1. 产品一句话

面向中国减脂塑形人群的 AI 健身陪练：通过饮食记录、训练打卡和每周复盘，帮助用户持续执行计划。

## 2. MVP 用户与边界

**首批用户**：20–35 岁、每周训练 2–4 次、有减脂塑形目标、但饮食与训练执行不稳定的中国用户。

**解决的问题**：用户不知道每天的饮食和训练是否接近目标，以及下一步该做什么。

**不做的事**：医疗诊断、疾病治疗、药物或补剂剂量建议、紧急健康决策。

## 3. MVP 成功闭环

```text
建档 → 记录一餐/一次训练 → 查询真实数据 → 保存记录
→ 生成今日建议 → 一周后生成复盘 → 用户确认下周重点
```

## 4. Figma 原型与真实产品的关系

Figma 原型用于展示用户点击路径；真实产品需要把每个按钮连接到后端接口和数据库。

| Figma 页面 | 真实产品需要做的事 |
| --- | --- |
| 首次建档 | 保存目标、体重、训练频率、饮食偏好 |
| 今日主页 | 读取当天饮食和训练汇总，展示建议 |
| 饮食记录 | 查询营养 API，用户确认后保存 |
| 训练打卡 | 保存动作、组数、次数、重量、疲劳感 |
| 每周复盘 | 汇总 7 天数据，生成下周重点 |

## 5. 推荐技术架构

```text
网页前端（Next.js / React）
          ↓
后端 API（FastAPI / Python）
          ↓
数据库与登录（Supabase / PostgreSQL）
          ↓
LangGraph 工作流 + 大模型 API
          ↓
营养 API / 动作库 API / LangSmith
```

**职责原则**：程序负责计算、保存和安全规则；大模型负责理解用户输入和解释建议。

## 6. 需要接入的 API

| API | 用途 | MVP 是否必须 |
| --- | --- | --- |
| OpenAI、Anthropic 或 Gemini | 理解用户输入、写建议 | 必须 |
| USDA FoodData Central | 食物 → 热量、蛋白质、碳水、脂肪 | 必须 |
| wger | 动作和训练动作库 | 建议 |
| Supabase | 登录、用户数据、饮食/训练记录 | 必须 |
| LangSmith | 记录 Agent 的工具调用与输出 | 必须 |
| Google Calendar | 用户确认后加入训练日程 | 第二阶段 |

## 7. 最小数据库设计

```text
users
  id, nickname, goal, current_weight, target_weight,
  workouts_per_week, dietary_preferences

food_logs
  id, user_id, logged_at, meal_type, food_text,
  calories, protein_g, carbs_g, fat_g, confirmed

workout_logs
  id, user_id, logged_at, workout_name, duration_min,
  perceived_effort

workout_sets
  id, workout_log_id, exercise_name, sets, reps, weight_kg

weekly_reviews
  id, user_id, week_start, training_completion_rate,
  protein_target_days, summary, next_week_focus
```

## 8. 最小后端接口

```text
POST /profile              创建或更新用户建档
POST /food/estimate        文字食物 → 营养 API 查询与估算（先不保存）
POST /food-logs            用户确认后保存饮食记录
POST /workout-logs         保存训练打卡
GET  /daily-summary        获取今日营养、训练和建议
POST /weekly-reviews       生成本周复盘
```

## 9. Agent 工作流

### 饮食记录

```text
用户输入“鸡胸肉 150g、米饭一碗”
  ↓
大模型提取食物与份量（结构化 JSON）
  ↓
FoodData API 查询营养
  ↓
程序累计当天热量与蛋白质
  ↓
Agent 解释结果和下一步建议
  ↓
用户确认后，才写入数据库
```

### 每周复盘

```text
读取过去 7 天饮食和训练数据
  ↓
程序计算训练完成率、记录天数、蛋白质达标天数
  ↓
安全规则检查
  ↓
Agent 输出“本周总结 + 一个下周重点”
  ↓
用户确认
```

## 10. 安全规则

- 任何医疗、急性疼痛、晕厥、胸痛等问题：建议咨询医生，不生成训练处方。
- 不自动改变用户的热量目标或训练计划；先给建议，等待用户确认。
- 清楚标注营养结果为估算值。
- 只收集完成 MVP 必需的数据；用户体重、饮食、训练数据需要保护。

## 11. 开发顺序

1. 搭建 Supabase 数据库和用户表。
2. 建 FastAPI，先做 `POST /profile` 和 `POST /food/estimate`。
3. 接 FoodData API，跑通“食物文字 → 营养结果”。
4. 接大模型，跑通“营养结果 → 今日建议”。
5. 接 LangSmith，查看每次 Agent 调用。
6. 做训练打卡与周报接口。
7. 最后开发网页前端，接入已有 Figma 页面。

## 12. 面试展示清单

- 产品 Brief 和 Figma 原型；
- 一条真实的饮食记录 API 调用；
- LangSmith Trace（模型调用与工具调用）；
- 模拟用户 7 天数据与生成的周报；
- MVP 取舍、安全边界和指标设计。

## 13. 原型迭代规则

当交互不合适时，先改 Figma，再判断影响范围：

1. 仅改文案/颜色/布局：只改 Figma。
2. 改按钮跳转：同时改 Figma 点击连线和用户流程文档。
3. 改数据或功能：同步修改 Figma、接口、数据库字段和 Agent 工作流。

开发后，Figma 仍是体验设计的参考；真正的运行逻辑以代码、API 和数据库为准。
