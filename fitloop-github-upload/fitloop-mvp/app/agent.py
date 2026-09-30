import json
from datetime import date
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from .config import Settings
from .repository import FitLoopRepository
from .schemas import FoodEstimate

SYSTEM_PROMPT = """你是 FitLoop 的日常健身陪练，服务中国的减脂和塑形用户。
只给出非医疗性质、可执行、友善且不过度承诺的建议。不要诊断疾病、不要开药、不要鼓励极端节食。
若用户提及晕厥、胸痛、严重疼痛、进食障碍、怀孕或未成年人，请建议其停止自行调整并咨询医生或专业人士。
建议限制为：一句观察 + 一条今天可完成的小行动，总共不超过 90 个中文字符。"""


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


def build_daily_advice_graph(settings: Settings, repo: FitLoopRepository):
    """Flow: retrieve facts -> calculate deterministic totals -> let LLM explain."""
    model = _model(settings)

    def load_data(state: DailyState) -> dict:
        profile = repo.get_profile(state["profile_id"])
        foods, workouts = repo.get_daily_logs(state["profile_id"], date.fromisoformat(state["for_date"]))
        return {"profile": profile, "foods": foods, "workouts": workouts}

    def calculate(state: DailyState) -> dict:
        return {"totals": _totals(state["foods"])}

    def coach(state: DailyState) -> dict:
        facts = {"profile": state["profile"], "foods": state["foods"], "workouts": state["workouts"], "totals": state["totals"]}
        answer = model.invoke([("system", SYSTEM_PROMPT), ("human", f"请只根据这些事实给今日建议：{facts}")])
        return {"advice": str(answer.content)}

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
