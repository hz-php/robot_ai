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
            print("[VISION ERROR] No frame to save")
            return None

        filename = f"photos/photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        success = cv2.imwrite(filename, self.current_frame)

        if success:
            print(f"[PHOTO SAVED] {filename}")
            return filename
        else:
            print(f"[PHOTO ERROR] Failed to save {filename}")
            return None

    # =========================
    # CREATE DATASET (TRAINING)
    # =========================
    def create_dataset(self, user_id):
        """
        Запись 30 образцов лица пользователя
        """

        if user_id is None:
            print("[DATASET ERROR] No user_id")
            return False

        dataset_path = f"dataset/{user_id}"
        os.makedirs(dataset_path, exist_ok=True)

        count = 0
        target = 30
        
        print(f"[DATASET] Starting face capture for user {user_id}...")

        while count < target:

            ret, frame = self.cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)

            for (x, y, w, h) in faces:

                face = gray[y:y+h, x:x+w]
                if face.size == 0:
                    continue

                face = cv2.resize(face, (200, 200))

                filename = f"{dataset_path}/face_{count:03d}.jpg"
                cv2.imwrite(filename, face)

                print(f"[DATASET] Captured {count + 1}/{target}")

                count += 1

                if count >= target:
                    break

            time.sleep(0.1)

        if count >= target:
            print(f"[DATASET] ✅ Dataset created for user {user_id}")
            self.train_model()
            return True
        else:
            print(f"[DATASET] ⚠️ Only captured {count}/{target} samples")
            return False

    # =========================
    # TRAIN MODEL
    # =========================
    def train_model(self):
        """
        Обучение LBPH распознавателя на всех датасетах
        """

        images = []
        labels = []
        label_map = {}
        next_label = 0

        print("[TRAINING] Starting model training...")

        # Сканирование всех датасетов
        for user_folder in os.listdir("dataset"):

            user_path = os.path.join("dataset", user_folder)

            if not os.path.isdir(user_path):
                continue

            try:
                user_id = int(user_folder)
            except:
                continue

            if user_id not in label_map:
                label_map[user_id] = next_label
                next_label += 1

            label = label_map[user_id]

            # Загрузка всех лиц пользователя
            for img_name in os.listdir(user_path):

                img_path = os.path.join(user_path, img_name)

                if not img_name.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue

                try:
                    image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

                    if image is None or image.size == 0:
                        continue

                    images.append(image)
                    labels.append(label)

                except Exception as e:
                    print(f"[TRAINING ERROR] {img_path}: {e}")

        if len(images) < 2:
            print("[TRAINING ERROR] Недостаточно образцов для обучения")
            return False

        print(f"[TRAINING] Training on {len(images)} images, {len(label_map)} users")

        try:
            self.recognizer.train(images, np.array(labels))
            self.recognizer.write(self.model_path)
            self.is_model_loaded = True

            # Сохранение маппинга в БД
            for user_id, label in label_map.items():

                existing = self.face_repo.get_by_label(label)

                if not existing:
                    self.face_repo.create(user_id, label)

            print(f"[TRAINING] ✅ Model saved: {self.model_path}")
            return True

        except Exception as e:
            print(f"[TRAINING ERROR] {e}")
            return False

    # =========================
    # RELEASE
    # =========================
    def release(self):
        self.cap.release()
        self.db.close()