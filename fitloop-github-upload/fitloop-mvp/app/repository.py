from datetime import date, timedelta
from uuid import UUID

from supabase import Client, create_client

from .config import Settings
from .schemas import FoodLogCreate, WorkoutLogCreate, WeeklyReviewConfirm


class FitLoopRepository:
    """Server-side gateway to the four Supabase tables already created."""

    def __init__(self, settings: Settings):
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError("缺少 SUPABASE_URL 或 SUPABASE_SERVICE_KEY。请先配置本地 .env。")
        self.client: Client = create_client(settings.supabase_url, settings.supabase_service_key)

    def get_profile(self, profile_id: UUID | str) -> dict:
        return self.client.table("profiles").select("*").eq("id", str(profile_id)).single().execute().data

    def get_daily_logs(self, profile_id: UUID | str, for_date: date) -> tuple[list[dict], list[dict]]:
        day_start = f"{for_date.isoformat()}T00:00:00+00:00"
        day_end = f"{for_date.isoformat()}T23:59:59+00:00"
        foods = self.client.table("food_logs").select("*").eq("profile_id", str(profile_id)).gte("logged_at", day_start).lte("logged_at", day_end).execute().data
        workouts = self.client.table("workout_logs").select("*").eq("profile_id", str(profile_id)).gte("logged_at", day_start).lte("logged_at", day_end).execute().data
        return foods, workouts

    def create_food_log(self, payload: FoodLogCreate) -> dict:
        record = {
            "profile_id": str(payload.profile_id), "meal_type": payload.meal_type,
            "food_text": payload.food_text, "calories": payload.calories,
            "protein_g": payload.protein_g, "carbs_g": payload.carbs_g,
            "fat_g": payload.fat_g, "confirmed": True,
        }
        if payload.log_date:
            record["logged_at"] = f"{payload.log_date.isoformat()}T12:00:00+00:00"
        return self.client.table("food_logs").insert(record).execute().data[0]

    def create_workout_log(self, payload: WorkoutLogCreate) -> dict:
        record = {"profile_id": str(payload.profile_id), "workout_name": payload.workout_name, "duration_min": payload.duration_min, "perceived_effort": payload.perceived_effort, "notes": payload.notes, "completed": True}
        if payload.log_date:
            record["logged_at"] = f"{payload.log_date.isoformat()}T12:00:00+00:00"
        return self.client.table("workout_logs").insert(record).execute().data[0]

    def get_weekly_logs(self, profile_id: UUID | str, week_start: date) -> tuple[list[dict], list[dict]]:
        start = f"{week_start.isoformat()}T00:00:00+00:00"
        end = f"{(week_start + timedelta(days=6)).isoformat()}T23:59:59+00:00"
        foods = self.client.table("food_logs").select("*").eq("profile_id", str(profile_id)).gte("logged_at", start).lte("logged_at", end).execute().data
        workouts = self.client.table("workout_logs").select("*").eq("profile_id", str(profile_id)).gte("logged_at", start).lte("logged_at", end).execute().data
        return foods, workouts

    def save_weekly_review(self, payload: WeeklyReviewConfirm) -> dict:
        record = payload.model_dump(mode="json")
        record["profile_id"] = str(payload.profile_id)
        return self.client.table("weekly_reviews").upsert(record, on_conflict="profile_id,week_start").execute().data[0]
