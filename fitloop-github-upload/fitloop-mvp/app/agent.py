import json
from datetime import date
from typing import TypedDict

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from .config import Settings
from .repository import FitLoopRepository
from .schemas import FoodEstimate, FoodLogCreate, WeeklyReviewConfirm, WorkoutLogCreate

SYSTEM_PROMPT = """你是 FitLoop 的日常健身陪练，服务中国的减脂和塑形用户。
只给出非医疗性质、可执行、友善且不过度承诺的建议。不要诊断疾病、不要开药、不要鼓励极端节食。
若用户提及晕厥、胸痛、严重疼痛、进食障碍、怀孕或未成年人，请建议其停止自行调整并咨询医生或专业人士。
建议限制为：一句观察 + 一条今天可完成的小行动，总共不超过 90 个中文字符。"""

TOOL_AGENT_SYSTEM_PROMPT = """你是 FitLoop 的工具调用健身记录助手。
你只能在工具返回成功结果后说“已保存”或“已生成”。
当用户明确陈述当天吃了什么及份量时，必须调用 save_food_log；没有提供食物时必须追问，不能编造记录。
当用户提供了明确训练类型和时长并要求记录时，必须调用 save_workout_log；缺少训练类型或时长时必须追问。
当用户要求查看、生成或保存本周复盘时，必须调用 generate_weekly_review。
食物没有明确热量时，save_food_log 的 calories 传 0；该工具会先估算四项营养并写入。只有工具返回 nutrition_status=pending 时，才说明营养数据待补充。
工具返回 ok=false 时，明确告知保存失败及错误信息，不能假装成功。
当用户消息明确写着“不要调用工具”时，绝对不要调用工具，只根据消息给出回答。
只给出非医疗性质建议；不要诊断疾病、开药或鼓励极端节食。"""


class DailyState(TypedDict, total=False):
    profile_id: str
    for_date: str
    profile: dict
    foods: list[dict]
    workouts: list[dict]
    totals: dict
    advice: str


def _totals(foods: list[dict]) -> dict:
    return {
        "calories": round(sum(float(x.get("calories") or 0) for x in foods), 0),
        "protein_g": round(sum(float(x.get("protein_g") or 0) for x in foods), 1),
        "carbs_g": round(sum(float(x.get("carbs_g") or 0) for x in foods), 1),
        "fat_g": round(sum(float(x.get("fat_g") or 0) for x in foods), 1),
    }


def _model(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(model=settings.deepseek_model, api_key=settings.deepseek_api_key, base_url="https://api.deepseek.com", temperature=0.3)


def _weekly_review_payload(repo: FitLoopRepository, profile_id: str, week_start: date) -> WeeklyReviewConfirm:
    foods, workouts = repo.get_weekly_logs(profile_id, week_start)
    food_days = len({item["logged_at"][:10] for item in foods})
    workout_count = len(workouts)
    protein_days = len({item["logged_at"][:10] for item in foods if float(item.get("protein_g") or 0) >= 25})
    focus = "训练日把晚餐蛋白质补齐" if protein_days < 5 else "保持训练和饮食记录节奏"
    summary = f"本周完成 {workout_count} 次训练，记录饮食 {food_days} 天，蛋白质达标 {protein_days} 天。"
    return WeeklyReviewConfirm(
        profile_id=profile_id,
        week_start=week_start,
        training_completion_rate=min(100, workout_count * 33.3),
        protein_target_days=protein_days,
        summary=summary,
        next_week_focus=focus,
    )


def build_fitness_tools(settings: Settings, repo: FitLoopRepository, profile_id: str):
    """Create the three tools available to one FitLoop user's agent session."""

    @tool
    def save_food_log(food_name: str, calories: float = 0, log_date: str = "", meal_type: str = "午餐") -> str:
        """Save one food record when the user explicitly gives a food or meal to record.

        Use this after the user supplies the food name. If calories is not supplied, the
        tool estimates calories and macros before saving. log_date is YYYY-MM-DD and may
        be empty to mean today.
        """
        args = {"food_name": food_name, "calories": calories, "log_date": log_date, "meal_type": meal_type}
        print(f"[TOOL CALL] tool_name=save_food_log, args={args}", flush=True)
        try:
            selected_date = date.fromisoformat(log_date) if log_date else date.today()
            estimated = estimate_food(settings, food_name)
            nutrition = {
                "calories": calories if calories > 0 else estimated.calories,
                "protein_g": estimated.protein_g,
                "carbs_g": estimated.carbs_g,
                "fat_g": estimated.fat_g,
                "nutrition_status": "estimated",
            }
        except Exception as exc:
            nutrition = {
                "calories": calories if calories > 0 else 0,
                "protein_g": 0,
                "carbs_g": 0,
                "fat_g": 0,
                "nutrition_status": "pending",
                "nutrition_error": str(exc),
            }
        try:
            result = repo.create_food_log(FoodLogCreate(
                profile_id=profile_id,
                meal_type=meal_type if meal_type in {"早餐", "午餐", "晚餐", "加餐"} else "午餐",
                food_text=food_name,
                calories=nutrition["calories"],
                protein_g=nutrition["protein_g"],
                carbs_g=nutrition["carbs_g"],
                fat_g=nutrition["fat_g"],
                log_date=selected_date,
            ))
            payload = {
                "ok": True,
                "id": result.get("id"),
                "logged_at": result.get("logged_at"),
                "calories": result.get("calories"),
                "protein_g": result.get("protein_g"),
                "carbs_g": result.get("carbs_g"),
                "fat_g": result.get("fat_g"),
                "nutrition_status": nutrition["nutrition_status"],
            }
            if nutrition["nutrition_status"] == "pending":
                payload["nutrition_error"] = nutrition["nutrition_error"]
        except Exception as exc:  # Tool failures must be returned to the model, not hidden.
            payload = {"ok": False, "error": str(exc)}
        print(f"[TOOL RESULT] tool_name=save_food_log, result={payload}", flush=True)
        return json.dumps(payload, ensure_ascii=False, default=str)

    @tool
    def save_workout_log(training_type: str, duration_min: int, log_date: str = "", perceived_effort: str = "刚好") -> str:
        """Save one completed workout when the user explicitly gives a training type and duration.

        Do not call this when either the training type or duration is missing. log_date is
        YYYY-MM-DD and may be empty to mean today.
        """
        args = {"training_type": training_type, "duration_min": duration_min, "log_date": log_date, "perceived_effort": perceived_effort}
        print(f"[TOOL CALL] tool_name=save_workout_log, args={args}", flush=True)
        try:
            selected_date = date.fromisoformat(log_date) if log_date else date.today()
            result = repo.create_workout_log(WorkoutLogCreate(
                profile_id=profile_id,
                workout_name=training_type,
                duration_min=duration_min,
                perceived_effort=perceived_effort if perceived_effort in {"轻松", "刚好", "很累"} else "刚好",
                log_date=selected_date,
            ))
            payload = {"ok": True, "id": result.get("id"), "logged_at": result.get("logged_at"), "duration_min": result.get("duration_min")}
        except Exception as exc:
            payload = {"ok": False, "error": str(exc)}
        print(f"[TOOL RESULT] tool_name=save_workout_log, result={payload}", flush=True)
        return json.dumps(payload, ensure_ascii=False, default=str)

    @tool
    def generate_weekly_review(week_start: str = "") -> str:
        """Generate and save the user's weekly review when they ask to review this week or a specified week.

        week_start is the Monday in YYYY-MM-DD format and may be empty to use this week's Monday.
        """
        args = {"week_start": week_start}
        print(f"[TOOL CALL] tool_name=generate_weekly_review, args={args}", flush=True)
        try:
            selected_date = date.fromisoformat(week_start) if week_start else date.today()
            monday = selected_date.fromordinal(selected_date.toordinal() - selected_date.weekday())
            payload = repo.save_weekly_review(_weekly_review_payload(repo, profile_id, monday))
            result = {"ok": True, "week_start": payload.get("week_start"), "summary": payload.get("summary"), "next_week_focus": payload.get("next_week_focus")}
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        print(f"[TOOL RESULT] tool_name=generate_weekly_review, result={result}", flush=True)
        return json.dumps(result, ensure_ascii=False, default=str)

    return [save_food_log, save_workout_log, generate_weekly_review]


def run_fitness_agent(settings: Settings, repo: FitLoopRepository, profile_id: str, message: str) -> str:
    """Run the LangChain tool-calling agent and return its final natural-language answer."""
    agent = create_agent(
        model=_model(settings),
        tools=build_fitness_tools(settings, repo, profile_id),
        system_prompt=TOOL_AGENT_SYSTEM_PROMPT,
    )
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config={"recursion_limit": 8},
    )
    return str(result["messages"][-1].content)


def build_daily_advice_graph(settings: Settings, repo: FitLoopRepository):
    """Flow: retrieve facts -> calculate deterministic totals -> let LLM explain."""
    def load_data(state: DailyState) -> dict:
        profile = repo.get_profile(state["profile_id"])
        foods, workouts = repo.get_daily_logs(state["profile_id"], date.fromisoformat(state["for_date"]))
        return {"profile": profile, "foods": foods, "workouts": workouts}

    def calculate(state: DailyState) -> dict:
        return {"totals": _totals(state["foods"])}

    def coach(state: DailyState) -> dict:
        facts = {"profile": state["profile"], "foods": state["foods"], "workouts": state["workouts"], "totals": state["totals"]}
        answer = run_fitness_agent(
            settings,
            repo,
            state["profile_id"],
            f"不要调用工具。请只根据这些事实给一句今日建议：{facts}",
        )
        return {"advice": answer}

    builder = StateGraph(DailyState)
    builder.add_node("load_data", load_data)
    builder.add_node("calculate", calculate)
    builder.add_node("coach", coach)
    builder.add_edge(START, "load_data")
    builder.add_edge("load_data", "calculate")
    builder.add_edge("calculate", "coach")
    builder.add_edge("coach", END)
    return builder.compile()


def estimate_food(settings: Settings, food_text: str) -> FoodEstimate:
    """Estimate first; the product saves only after the user confirms."""
    # DeepSeek's OpenAI-compatible endpoint does not consistently support the
    # response_format used by LangChain's with_structured_output. Ask for JSON
    # explicitly, then validate it with Pydantic on our side.
    prompt = SYSTEM_PROMPT + "\n用户记录了：" + food_text + "\n估算这一整餐的能量和三大营养素。信息不足时可以估算，但须写出假设。只返回合法 JSON，不要 Markdown。JSON 字段必须是 calories、protein_g、carbs_g、fat_g、assumptions（中文字符串数组）。"
    response = _model(settings).invoke(prompt)
    raw = str(response.content).strip()
    if raw.startswith("```json"):
        raw = raw.removeprefix("```json").removesuffix("```").strip()
    return FoodEstimate.model_validate(json.loads(raw))
