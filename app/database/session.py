from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

from sqlalchemy import text
def _migrate_db(eng):
    try:
        from app.database.base import Base
        import app.models
        Base.metadata.create_all(bind=eng)
        
        with eng.begin() as conn:
            res = conn.execute(text("PRAGMA table_info(projects)")).fetchall()
            if res:
                cols = [r[1] for r in res]
                if "continuity_key" not in cols:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN continuity_key VARCHAR(255)"))
                if "preferred_story_model" not in cols:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN preferred_story_model VARCHAR(255)"))
    except Exception as e:
        pass

_migrate_db(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
