import cv2
import os
import time
import numpy as np
from datetime import datetime

from database.db import SessionLocal
from database.repositories.user_repository import UserRepository
from database.repositories.face_repository import FaceRepository
from vision.face_session import FaceSession


class CameraVision:

    def __init__(self):

        self.db = SessionLocal()
        self.user_repo = UserRepository(self.db)
        self.face_repo = FaceRepository(self.db)

        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.model_path = "face_model.yml"

        self.is_model_loaded = os.path.exists(self.model_path)

        if self.is_model_loaded:
            self.recognizer.read(self.model_path)

        self.session = FaceSession()

        # 🔥 FIX FLICKER
        self.last_seen = {}
        self.smooth_threshold = 5

        # STATUS FOR UI
        self.status = "IDLE"

        self.current_frame = None
        self.telemetry = ""

        os.makedirs("dataset", exist_ok=True)
        os.makedirs("photos", exist_ok=True)

    # =========================
    # MAIN LOOP
    # =========================
    def update(self):

        ret, frame = self.cap.read()
        if not ret:
            return False

        self.current_frame = frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)

        for (x, y, w, h) in faces:

            name = "Unknown"
            role = "UNKNOWN"
            user_id = None

            if self.is_model_loaded:

                face = gray[y:y+h, x:x+w]

                if face.size == 0:
                    continue

                face = cv2.resize(face, (200, 200))

                label, conf = self.recognizer.predict(face)

                if conf < 75:

                    profile = self.face_repo.get_by_label(label)

                    if profile:
                        user = self.user_repo.get_by_id(profile.user_id)

                        if user:

                            user_id = user.id
                            name = user.name
                            role = user.role

                            # 🔥 STABILITY FIX
                            self._smooth_identity(user_id)

            # session update
            self.session.update(user_id, name, role, conf)

            color = (0, 255, 0) if user_id else (0, 0, 255)

            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

            cv2.putText(frame, name, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        self.telemetry = f"USER={self.session.current_user_id} | {self.session.current_name}"

        return True

    # =========================
    # FLICKER FIX CORE
    # =========================
    def _smooth_identity(self, user_id):

        self.last_seen[user_id] = self.last_seen.get(user_id, 0) + 1

        # reset others
        for k in list(self.last_seen.keys()):
            if k != user_id:
                self.last_seen[k] -= 1
                if self.last_seen[k] <= 0:
                    del self.last_seen[k]

        # commit stable identity
        if self.last_seen[user_id] >= self.smooth_threshold:
            self.session.set_user(user_id)

    # =========================
    # PHOTO
    # =========================
    def save_photo(self):

        if self.current_frame is None:
            return None

        filename = f"photos/photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(filename, self.current_frame)

        return filename

    # =========================
    # RELEASE
    # =========================
    def release(self):
        self.cap.release()
        self.db.close()