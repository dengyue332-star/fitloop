# FitLoop MVP 后端

这是你的第一个“可跑通”的产品后端，不是网页模板。它连接三件事：

1. **Supabase**：保存用户、饮食、训练、周报。
2. **DeepSeek**：把用户的中文饮食记录变成估算，或基于当天真实数据生成陪练建议。
3. **LangGraph + LangSmith**：把“先取数据 → 再计算 → 最后由 AI 解释”的过程串起来，并可在 LangSmith 中查看轨迹。

## 当前可跑的 MVP

| 接口 | 它做什么 |
| --- | --- |
| `GET /health` | 检查三个服务有没有配置好，不暴露任何密钥。 |
| `POST /food/estimate` | DeepSeek 估算中文饮食描述；用户看完后才确认保存。 |
| `POST /food-logs` | 将用户确认过的饮食写入 Supabase。 |
| `POST /daily-advice` | LangGraph：取当天真实记录 → 代码计算总量 → DeepSeek 给一条简短建议。 |

## 先做这三步

### 1. 创建本地配置文件

在本文件夹中复制 `.env.example`，命名为 `.env`。然后只在 `.env` 中补齐：

- `DEEPSEEK_API_KEY`：你的 DeepSeek Key。
- `SUPABASE_SERVICE_KEY`：Supabase Dashboard → **Project Settings → API** 中的 server-side secret/service-role key。它只能放后端本地，不能放 Figma、前端或 GitHub。
- `LANGSMITH_API_KEY`：可选。填上以后，轨迹会进入 `my-first-agent` 项目。

`SUPABASE_URL` 已按你的 FitLoop 项目预填。

### 2. 安装依赖并启动

这台电脑默认 Python 可能是 3.9，而 LangChain 需要 3.10+。请用 Python 3.12：

```bash
cd "/Users/BING/Documents/Codex/2026-09-24/install-langchain-open-source-skills-from/outputs/fitloop-mvp"
/Users/BING/.local/bin/python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后打开：<http://127.0.0.1:8000/docs> 。这是自动生成的接口操作台。

### 3. 在 `/docs` 里验证

先点 `GET /health → Try it out → Execute`。看到 `status: ok` 后，再试 `POST /food/estimate`：

```json
{"food_text":"鸡胸肉 150g、米饭一碗、西兰花一份"}
```

它会先返回“估算”，**不会自动写数据库**。确认无误后，再把返回数字带入 `POST /food-logs`。

## 为什么这算 Agent，而不是普通聊天框？

```text
Supabase 中的真实记录
        ↓
代码做确定的营养合计（不会由 AI 猜）
        ↓
LangGraph 规定处理顺序
        ↓
DeepSeek 只负责理解和表达建议
        ↓
LangSmith 可查看这次决策过程
```

面试时你可以这样说：**数值、写库、安全规则由程序负责；AI 负责自然语言理解和个性化表达。**

## 下一阶段

1. 从 Figma 的“饮食记录”页调用 `/food/estimate` 和 `/food-logs`。
2. 加入营养数据库 API，让估算有可追溯的数据来源。
3. 接入 Supabase Auth，让每位真实用户只能读取自己的数据；当前 RLS 已开启，不能跳过。
4. 做每周复盘接口，并把“下周重点”写入 `weekly_reviews`。
