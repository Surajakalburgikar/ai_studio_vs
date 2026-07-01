"""
FastAPI endpoints for Gemini Model Router information, statistics, and health.
"""

from fastapi import APIRouter
import time
from app.services.ai.providers.gemini_model_router import GeminiModelRouter

router = APIRouter(prefix="/system/gemini", tags=["System Gemini"])


@router.get("/router")
def get_router_info() -> dict:
    """Returns the current state, active model, and configuration of the Gemini model router."""
    r = GeminiModelRouter()
    
    try:
        current_active = r.get_active_model()
    except Exception:
        current_active = None
        
    cooldown_models = []
    now = time.time()
    for model in r.get_priority_list():
        cooldown_until = r.cooldowns.get(model, 0)
        if cooldown_until > now:
            cooldown_models.append(model)
            
    return {
        "current_active_model": current_active,
        "cooldown_models": cooldown_models,
        "priority_order": r.get_priority_list(),
        "statistics": r.stats
    }


@router.get("/stats")
def get_stats_info() -> dict:
    """Returns detailed per-model and overall statistics of the router."""
    r = GeminiModelRouter()
    return r.get_stats_summary()


@router.get("/health")
def get_health_info() -> dict:
    """Returns the health status of configured models and the router."""
    r = GeminiModelRouter()
    
    priority_list = r.get_priority_list()
    healthy_models = []
    models_on_cooldown = []
    now = time.time()
    
    for model in priority_list:
        cooldown_until = r.cooldowns.get(model, 0)
        if cooldown_until > now:
            models_on_cooldown.append(model)
        else:
            healthy_models.append(model)
            
    if len(models_on_cooldown) == 0:
        status = "healthy"
    elif len(healthy_models) > 0:
        status = "degraded"
    else:
        status = "unavailable"
        
    return {
        "healthy_models": healthy_models,
        "models_on_cooldown": models_on_cooldown,
        "unavailable_models": models_on_cooldown,
        "router_status": status
    }
