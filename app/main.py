from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.projects import router as projects_router
from app.api.stories import router as stories_router
from app.api.episodes import router as episodes_router
from app.api.scenes import router as scenes_router
from app.blueprint.story_blueprint import router as blueprint_router
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
app.include_router(blueprint_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {"message": "AI Studio Backend Running"}
