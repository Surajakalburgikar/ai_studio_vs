from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.projects import router as projects_router
from app.api.stories import router as stories_router
from app.api.episodes import router as episodes_router
from app.api.scenes import router as scenes_router
from app.api.characters import router as characters_router
from app.api.scene_characters import router as scene_characters_router
from app.api.storyboard import router as storyboard_router
from app.api.prompts import router as prompts_router
from app.api.images import router as images_router
from app.api.assets import router as assets_router
from app.api.jobs import router as jobs_router
from app.blueprint.story_blueprint import router as blueprint_router
from app.api.orchestration import router as orchestration_router
from app.api.system import router as system_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(stories_router)
app.include_router(episodes_router)
app.include_router(scenes_router)
app.include_router(characters_router)
app.include_router(scene_characters_router)
app.include_router(storyboard_router)
app.include_router(prompts_router)
app.include_router(images_router)
app.include_router(assets_router)
app.include_router(jobs_router)
app.include_router(blueprint_router)
app.include_router(orchestration_router)
app.include_router(system_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {"message": "AI Studio Backend Running"}
