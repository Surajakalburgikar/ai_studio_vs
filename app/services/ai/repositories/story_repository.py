"""
Story repository to persist generated stories, episodes, and scenes into database.
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.story import Story
from app.models.episode import Episode
from app.models.scene import Scene
from app.services.ai.exceptions import RepositoryError

logger = logging.getLogger("ai_studio")


class StoryRepository:
    """Manages database persistence for the Story generation hierarchy."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def save_story(self, project_id: int, story_data: dict) -> Story:
        """Save story, episodes, and scenes in a single transaction.

        Args:
            project_id: The ID of the project this story belongs to.
            story_data: Validated story dictionary.

        Returns:
            The persisted Story SQLAlchemy model instance.

        Raises:
            RepositoryError: If saving to the database fails.
        """
        # Ensure we run this in a transaction block
        try:
            # 1. Create Story
            story = Story(
                project_id=project_id,
                title=story_data["title"],
                genre=story_data["genre"],
                summary=story_data["summary"],
                story_text=story_data["story_text"],
                status="draft",
                version=1
            )
            self.db.add(story)
            self.db.flush()  # Populates story.id

            # 2. Iterate and create Episodes
            for ep_data in story_data["episodes"]:
                episode = Episode(
                    story_id=story.id,
                    episode_number=ep_data["episode_number"],
                    title=ep_data["title"],
                    summary=ep_data["summary"],
                    status="draft"
                )
                self.db.add(episode)
                self.db.flush()  # Populates episode.id

                # 3. Iterate and create Scenes
                for sc_data in ep_data["scenes"]:
                    scene = Scene(
                        episode_id=episode.id,
                        scene_number=sc_data["scene_number"],
                        title=sc_data["title"],
                        narration=sc_data["narration"],
                        camera_notes=sc_data["camera_notes"],
                        duration_seconds=sc_data["duration_seconds"],
                        status="draft"
                    )
                    self.db.add(scene)

            # Commit the transaction
            self.db.commit()
            self.db.refresh(story)
            logger.info(f"Successfully persisted story '{story.title}' (ID: {story.id}) in database.")
            return story

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error while saving story hierarchy: {e}")
            raise RepositoryError(f"Failed to persist story hierarchy in database: {str(e)}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error while saving story hierarchy: {e}")
            raise RepositoryError(f"Unexpected error during story persistence: {str(e)}")
