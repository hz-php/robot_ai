import cv2

from database.db import SessionLocal
from database.repositories.user_repository import UserRepository

from vision.vision import CameraVision
from voice.voice import NeuroVoice
from ai.brain import Brain
from ai.agent import AIAgent
from ai.tools.tool_router import ToolRouter


def bootstrap():

    db = SessionLocal()
    users = UserRepository(db)

    if not users.get_by_id(1):
        users.create(name="Igor", role="ADMIN")

    return db


if __name__ == "__main__":

    bootstrap()

    vision = CameraVision()
    voice = NeuroVoice()

    brain = Brain()

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
        cv2.putText(
            frame,
            vision.status,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )

        cv2.imshow("AI AGENT v1", frame)

        if cv2.waitKey(1) == 27:
            break

    vision.release()
    cv2.destroyAllWindows()