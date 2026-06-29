from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.production_plan import ProductionPlan, AnimationProfile, ProductionProfile, QualityProfile

def get_production_plan_by_project_id(db: Session, project_id: int) -> dict | None:
    """Calculate and return the production plan for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None
        
    plan = project.production_plan
    if plan is None:
        # Use default profiles but do not write to DB
        animation_profile = AnimationProfile.STANDARD
        production_profile = ProductionProfile.LONG_FORM
        quality_profile = QualityProfile.STANDARD
        plan_id = None
        created_at = None
        updated_at = None
    else:
        animation_profile = plan.animation_profile
        production_profile = plan.production_profile
        quality_profile = plan.quality_profile
        plan_id = plan.id
        created_at = plan.created_at
        updated_at = plan.updated_at
        
    # Perform calculations
    target_duration = project.target_duration_seconds
    
    # 1. Production Profile factors
    if production_profile == ProductionProfile.SHORTS:
        avg_scene_duration = 5.0
    elif production_profile == ProductionProfile.REEL:
        avg_scene_duration = 6.0
    elif production_profile == ProductionProfile.SERIES:
        avg_scene_duration = 20.0
    else:  # LONG_FORM
        avg_scene_duration = 15.0
        
    estimated_scene_count = max(1, round(target_duration / avg_scene_duration))
    
    # 2. Animation Profile factors
    if animation_profile == AnimationProfile.BASIC:
        shots_per_scene = 2
        keyframes_per_shot = 1
        base_render_time = 0.5
    elif animation_profile == AnimationProfile.HIGH:
        shots_per_scene = 6
        keyframes_per_shot = 4
        base_render_time = 5.0
    elif animation_profile == AnimationProfile.CINEMA:
        shots_per_scene = 8
        keyframes_per_shot = 8
        base_render_time = 15.0
    else:  # STANDARD
        shots_per_scene = 4
        keyframes_per_shot = 2
        base_render_time = 2.0
        
    estimated_shot_count = estimated_scene_count * shots_per_scene
    estimated_keyframe_count = estimated_shot_count * keyframes_per_shot
    estimated_image_count = estimated_keyframe_count
    
    # 3. Quality Profile factors
    if quality_profile == QualityProfile.DRAFT:
        base_size = 0.2
        render_mult = 0.5
    elif quality_profile == QualityProfile.HIGH:
        base_size = 4.0
        render_mult = 2.0
    elif quality_profile == QualityProfile.ULTRA:
        base_size = 16.0
        render_mult = 4.0
    else:  # STANDARD
        base_size = 1.0
        render_mult = 1.0
        
    estimated_storage_mb = round(estimated_image_count * base_size, 2)
    estimated_narration_duration = round(target_duration * 0.9, 1)
    
    total_render_seconds = estimated_image_count * base_render_time * render_mult
    estimated_render_minutes = round(total_render_seconds / 60.0, 2)
    
    return {
        "id": plan_id,
        "project_id": project.id,
        "animation_profile": animation_profile,
        "production_profile": production_profile,
        "quality_profile": quality_profile,
        "target_runtime_seconds": target_duration,
        "estimated_scene_count": estimated_scene_count,
        "estimated_shot_count": estimated_shot_count,
        "estimated_keyframe_count": estimated_keyframe_count,
        "estimated_image_count": estimated_image_count,
        "estimated_narration_duration": estimated_narration_duration,
        "estimated_storage_mb": estimated_storage_mb,
        "estimated_render_minutes": estimated_render_minutes,
        "created_at": created_at,
        "updated_at": updated_at
    }

def save_production_plan(
    db: Session,
    project_id: int,
    animation_profile: AnimationProfile,
    production_profile: ProductionProfile,
    quality_profile: QualityProfile
) -> ProductionPlan:
    """Save or update custom profiles for a project's production plan."""
    plan = db.query(ProductionPlan).filter(ProductionPlan.project_id == project_id).first()
    if plan:
        plan.animation_profile = animation_profile
        plan.production_profile = production_profile
        plan.quality_profile = quality_profile
    else:
        plan = ProductionPlan(
            project_id=project_id,
            animation_profile=animation_profile,
            production_profile=production_profile,
            quality_profile=quality_profile
        )
        db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan
