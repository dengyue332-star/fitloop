from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import build_daily_advice_graph, estimate_food, run_fitness_agent
from .config import get_settings
from .repository import FitLoopRepository
from .schemas import AgentRequest, DailyAdviceRequest, FoodLogCreate, WorkoutLogCreate, WeeklyReviewConfirm, WeeklyReviewDraftRequest

app = FastAPI(title="FitLoop MVP API", version="0.1.0")
allowed_origins = ["http://127.0.0.1:5173", "http://localhost:5173"]
if get_settings().frontend_origin:
    allowed_origins.append(get_settings().frontend_origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class FoodEstimateRequest(BaseModel):
    food_text: str = Field(min_length=2, max_length=500)


def repository() -> FitLoopRepository:
    try:
        return FitLoopRepository(get_settings())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "deepseek_configured": bool(settings.deepseek_api_key), "supabase_configured": bool(settings.supabase_url and settings.supabase_service_key), "langsmith_project": settings.langsmith_project}


@app.post("/food/estimate")
def food_estimate(payload: FoodEstimateRequest) -> dict:
    if not get_settings().deepseek_api_key:
        raise HTTPException(status_code=503, detail="缺少 DEEPSEEK_API_KEY，请先配置本地 .env。")
    try:
        return estimate_food(get_settings(), payload.food_text).model_dump()
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="模型返回格式异常，请稍后重试。") from exc


@app.post("/food-logs")
def save_food_log(payload: FoodLogCreate) -> dict:
    return repository().create_food_log(payload)


@app.post("/workout-logs")
def save_workout_log(payload: WorkoutLogCreate) -> dict:
    return repository().create_workout_log(payload)


@app.get("/weekly-reviews/{profile_id}")
def latest_weekly_review(profile_id: str) -> dict:
    data = repository().client.table("weekly_reviews").select("*").eq("profile_id", profile_id).order("week_start", desc=True).limit(1).execute().data
    if not data:
        raise HTTPException(status_code=404, detail="还没有周报，请先生成第一份复盘。")
    return data[0]


@app.post("/weekly-reviews/draft")
def weekly_review_draft(payload: WeeklyReviewDraftRequest) -> dict:
    foods, workouts = repository().get_weekly_logs(payload.profile_id, payload.week_start)
    food_days = len({item["logged_at"][:10] for item in foods})
    workout_count = len(workouts)
    protein_days = len({item["logged_at"][:10] for item in foods if float(item.get("protein_g") or 0) >= 25})
    score = min(100, workout_count * 20 + food_days * 8 + protein_days * 4)
    focus = "训练日把晚餐蛋白质补齐" if protein_days < 5 else "保持训练和饮食记录节奏"
    summary = f"本周完成 {workout_count} 次训练，记录饮食 {food_days} 天，蛋白质达标 {protein_days} 天。"
    return {"week_start": payload.week_start, "execution_score": score, "training_count": workout_count, "food_log_days": food_days, "protein_target_days": protein_days, "summary": summary, "next_week_focus": focus}


@app.post("/weekly-reviews/confirm")
def confirm_weekly_review(payload: WeeklyReviewConfirm) -> dict:
    return repository().save_weekly_review(payload)


@app.post("/daily-advice")
def daily_advice(payload: DailyAdviceRequest) -> dict:
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise HTTPException(status_code=503, detail="缺少 DEEPSEEK_API_KEY，请先配置本地 .env。")
    selected_date = payload.for_date or date.today()
    graph = build_daily_advice_graph(settings, repository())
    result = graph.invoke({"profile_id": str(payload.profile_id), "for_date": selected_date.isoformat()})
    return {
        "date": selected_date,
        "profile": {"nickname": result["profile"].get("nickname", "你")},
        "totals": result["totals"],
        "food_log_count": len(result["foods"]),
        "workouts": result["workouts"],
        "advice": result["advice"],
    }


@app.post("/agent/run")
def run_agent(payload: AgentRequest) -> dict:
    """Entry point for the tool-calling fitness-recording agent."""
    try:
        answer = run_fitness_agent(get_settings(), repository(), str(payload.profile_id), payload.message)
        return {"answer": answer}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
