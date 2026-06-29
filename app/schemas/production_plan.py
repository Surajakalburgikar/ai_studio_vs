from datetime import datetime
from pydantic import BaseModel, Field
from app.models.production_plan import AnimationProfile, ProductionProfile, QualityProfile

class ProductionPlanUpdate(BaseModel):
    animation_profile: AnimationProfile = Field(..., description="Animation profile")
    production_profile: ProductionProfile = Field(..., description="Production profile")
    quality_profile: QualityProfile = Field(..., description="Quality profile")

class ProductionPlanResponse(BaseModel):
    id: int | None = Field(None, description="Production Plan ID")
    project_id: int = Field(..., description="Project ID")
    animation_profile: AnimationProfile = Field(..., description="Animation profile")
    production_profile: ProductionProfile = Field(..., description="Production profile")
    quality_profile: QualityProfile = Field(..., description="Quality profile")
    
    # Calculated estimates
    target_runtime_seconds: int = Field(..., description="Target runtime in seconds")
    estimated_scene_count: int = Field(..., description="Estimated scene count")
    estimated_shot_count: int = Field(..., description="Estimated shot count")
    estimated_keyframe_count: int = Field(..., description="Estimated keyframe count")
    estimated_image_count: int = Field(..., description="Estimated image count")
    estimated_narration_duration: float = Field(..., description="Estimated narration duration in seconds")
    estimated_storage_mb: float = Field(..., description="Estimated storage in MB")
    estimated_render_minutes: float = Field(..., description="Estimated rendering time in minutes")
    
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
