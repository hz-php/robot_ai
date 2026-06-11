import cv2

from database.db import SessionLocal
from database.repositories.user_repository import UserRepository
from database.repositories.voice_profiles_repository import VoiceProfileRepository

from vision.vision import CameraVision
from voice.voice import NeuroVoice
from ai.brain import Brain
from ai.agent import AIAgent
from ai.tools.tool_router import ToolRouter


def check_database():
    """Проверка и инициализация БД"""
    
    try:
        print("[DB] Checking database structure...")
        
        db = SessionLocal()
        
        # Проверяем существование нужных колонок в voice_profiles
        from sqlalchemy import text, inspect
        from database.db import engine
        
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('voice_profiles')]
        
        required_columns = ['profile_features', 'profile_std', 'samples_count']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"[DB WARNING] Missing columns in voice_profiles: {missing_columns}")
            print("[DB WARNING] Run: python migration_voice_profiles.py")
            return False
        
        print("[DB] ✅ Database structure OK")
        return True
        
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return False


def bootstrap():


    db = SessionLocal()
    users = UserRepository(db)

    if not users.get_by_id(1):
        users.create(name="Igor", role="ADMIN")

    return db


if __name__ == "__main__":

    # 🔍 Check database structure
    if not check_database():
        print("[ERROR] Please run: python migration_voice_profiles.py")
        exit(1)

    bootstrap()

    vision = CameraVision()
    
    # 🎤 Voice repository for database storage
    voice_repo = VoiceProfileRepository(vision.db)
    
    voice = NeuroVoice(db=vision.db, voice_repo=voice_repo)

    # Инициализация Brain с именем Unknown
    brain = Brain(username="Unknown")

    tools = ToolRouter(
        vision=vision,
        voice=voice,
        db=vision.db,
        face_repo=vision.face_repo,
        user_repo=vision.user_repo
    )

    agent = AIAgent(vision, voice, brain, tools)

    voice.on_text = agent.handle
    voice.start_background_listener()

    while True:

        if not vision.update():
            break

        frame = vision.current_frame

        # 🔥 STATUS TEXT
        # cv2.putText(
        #     frame,
        #     vision.status,
        #     (20, 40),
        #     cv2.FONT_HERSHEY_SIMPLEX,
        #     1,
        #     (0, 255, 255),
        #     2
        # )

        cv2.imshow("AI AGENT v1", frame)

        if cv2.waitKey(1) == 27:
            break

    vision.release()
    cv2.destroyAllWindows()