from sqlalchemy.orm import Session
from app.models.scene import Scene
from app.models.timeline_event import TimelineEvent
from app.storyboard.storyboard_generator import generate_storyboard
from app.schemas.scene_direction import TimelineEventCreate

def get_scene_direction(db: Session, scene_id: int) -> dict | None:
    """Generate a complete directing plan for a scene, merging saved events and dynamic defaults."""
    # 1. Fetch Scene
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return None
        
    # 2. Fetch Storyboard (provides shots)
    storyboard = generate_storyboard(db, scene_id)
    if not storyboard or "shots" not in storyboard:
        return None
        
    # 3. Fetch custom timeline events from DB
    db_events = db.query(TimelineEvent).filter(TimelineEvent.scene_id == scene_id).order_by(TimelineEvent.timestamp.asc()).all()
    
    # Group events by shot_number
    events_by_shot = {}
    for event in db_events:
        events_by_shot.setdefault(event.shot_number, []).append({
            "timestamp": event.timestamp,
            "category": event.category,
            "action": event.action,
            "parameters": event.parameters
        })
        
    directed_shots = []
    
    # 4. Direct each shot
    for shot in storyboard["shots"]:
        shot_num = shot["shot_number"]
        duration = shot["duration_seconds"]
        focus_chars = shot["focus_characters"]
        
        # Check if we have saved events in DB
        if shot_num in events_by_shot:
            timeline_events = events_by_shot[shot_num]
        else:
            # Generate default timeline events deterministically
            timeline_events = []
            
            # Camera Planning
            cam_action = "static"
            cam_params = {"speed": "normal", "focus": "auto"}
            if shot["shot_type"] == "Wide":
                cam_action = "pan"
                cam_params["speed"] = "slow"
            elif shot["shot_type"] == "Medium":
                cam_action = "push_in"
                cam_params["speed"] = "medium"
            elif shot["shot_type"] == "Close-up":
                cam_action = "static"
                cam_params["focus"] = "eyes"
                
            timeline_events.append({
                "timestamp": 0.0,
                "category": "camera",
                "action": cam_action,
                "parameters": cam_params
            })
            
            # Character Planning
            for idx, name in enumerate(focus_chars):
                char_action = "look_around" if idx % 2 == 0 else "walk"
                timeline_events.append({
                    "timestamp": 0.5,
                    "category": "character",
                    "action": char_action,
                    "parameters": {"character_name": name, "speed": "normal"}
                })
                
            # Environment Planning
            timeline_events.append({
                "timestamp": 0.0,
                "category": "environment",
                "action": "ambient_wind",
                "parameters": {"intensity": "low"}
            })
            
            # Cinematic Effects
            timeline_events.append({
                "timestamp": 0.0,
                "category": "effects",
                "action": "motion_blur",
                "parameters": {"strength": "medium"}
            })
            
            # Audio Cues
            timeline_events.append({
                "timestamp": 0.0,
                "category": "audio",
                "action": "ambient_noise",
                "parameters": {"volume": 0.4, "loop": True}
            })
            
        # 5. Calculate estimated keyframes
        estimated_keyframes = [
            {"id": 1, "timestamp": 0.0, "description": "Start of shot - Establishing composition"},
            {"id": 2, "timestamp": round(duration / 2.0, 2), "description": "Midpoint of shot - Motion peak"},
            {"id": 3, "timestamp": round(duration, 2), "description": "End of shot - Transition frame"}
        ]
        
        directed_shots.append({
            "shot_number": shot_num,
            "shot_type": shot["shot_type"],
            "camera_angle": shot["camera_angle"],
            "duration_seconds": duration,
            "focus_characters": focus_chars,
            "description": shot["description"],
            "transition": shot["transition"],
            "timeline": timeline_events,
            "estimated_keyframes": estimated_keyframes
        })
        
    return {
        "scene_id": scene.id,
        "scene_title": scene.title,
        "narration": scene.narration,
        "camera_notes": scene.camera_notes,
        "duration_seconds": scene.duration_seconds or 10.0,
        "shots": directed_shots
    }

def save_scene_direction(db: Session, scene_id: int, events: list[TimelineEventCreate]) -> list[TimelineEvent]:
    """Overwrite custom timeline events for a scene in the database."""
    # Delete existing events
    db.query(TimelineEvent).filter(TimelineEvent.scene_id == scene_id).delete()
    
    created_events = []
    for e in events:
        db_event = TimelineEvent(
            scene_id=scene_id,
            shot_number=e.shot_number,
            timestamp=e.timestamp,
            category=e.category,
            action=e.action,
            parameters=e.parameters
        )
        db.add(db_event)
        created_events.append(db_event)
        
    db.commit()
    return created_events
