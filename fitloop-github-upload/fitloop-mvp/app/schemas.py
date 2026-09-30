from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class FoodLogCreate(BaseModel):
    profile_id: UUID
    meal_type: str = Field(pattern="^(早餐|午餐|晚餐|加餐)$")
    food_text: str = Field(min_length=2, max_length=500)
    calories: float = Field(ge=0, le=5000)
    protein_g: float = Field(ge=0, le=500)
    carbs_g: float = Field(ge=0, le=1000)
    fat_g: float = Field(ge=0, le=500)


class DailyAdviceRequest(BaseModel):
    profile_id: UUID
    for_date: date | None = None


class WorkoutLogCreate(BaseModel):
    profile_id: UUID
    workout_name: str = Field(min_length=2, max_length=100)
    duration_min: int = Field(ge=1, le=300)
    perceived_effort: str = Field(pattern="^(轻松|刚好|很累)$")
    notes: str | None = Field(default=None, max_length=500)


class WeeklyReviewDraftRequest(BaseModel):
    profile_id: UUID
    week_start: date


class WeeklyReviewConfirm(BaseModel):
    profile_id: UUID
    week_start: date
    training_completion_rate: float = Field(ge=0, le=100)
    protein_target_days: int = Field(ge=0, le=7)
    summary: str = Field(min_length=1, max_length=1000)
    next_week_focus: str = Field(min_length=1, max_length=300)


class FoodEstimate(BaseModel):
    calories: float = Field(description="Estimated kcal for the whole meal")
    protein_g: float = Field(description="Estimated protein grams for the whole meal")
    carbs_g: float = Field(description="Estimated carbohydrate grams for the whole meal")
    fat_g: float = Field(description="Estimated fat grams for the whole meal")
    assumptions: list[str] = Field(description="Short Chinese assumptions used for the estimate")
