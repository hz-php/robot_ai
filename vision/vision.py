import cv2
import os
import time
import numpy as np
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from database.db import SessionLocal
from database.models import User
from database.repositories.user_repository import UserRepository
from database.repositories.face_repository import FaceRepository
from vision.face_session import FaceSession


def _init_face_recognizer():
    """Инициализация LBPH распознавателя с несколькими вариантами fallback"""
    try:
        return cv2.face.LBPHFaceRecognizer_create()
    except AttributeError:
        pass
    
    try:
        return cv2.face.createLBPHFaceRecognizer()
    except AttributeError:
        pass
    
    try:
        return cv2.LBPHFaceRecognizer_create()
    except AttributeError:
        pass
    
    print("[WARNING] Не удалось инициализировать LBPH Face Recognizer")
    print("[WARNING] Убедитесь, что установлен opencv-contrib-python:")
    print("[WARNING] pip install opencv-contrib-python --upgrade")
    return None


class CameraVision:

    def __init__(self):
        # --------------------------------------------------
        # Гарантированная загрузка шрифта с поддержкой UTF-8
        # --------------------------------------------------
        font_loaded = False
        possible_fonts = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "arial.ttf"  # если файл лежит прямо в корне проекта
        ]
        
        for font_path in possible_fonts:
            try:
                self.font = ImageFont.truetype(font_path, 20)
                font_loaded = True
                break
            except IOError:
                continue
                
        if not font_loaded:
            print("[VISION WARNING] Не удалось найти TrueType шрифт. Кириллица может отображаться некорректно!")
            self.font = ImageFont.load_default()

        # --------------------------------------------------
        # База данных и репозитории
        # --------------------------------------------------
        self.db = SessionLocal()
        self.user_repo = UserRepository(self.db)
        self.face_repo = FaceRepository(self.db)

        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        self.recognizer = _init_face_recognizer()
        self.model_path = "face_model.yml"
        self.is_model_loaded = False
        
        if self.recognizer is not None and os.path.exists(self.model_path):
            try:
                self.recognizer.read(self.model_path)
                self.is_model_loaded = True
                print("[VISION] Модель лиц успешно загружена")
            except Exception as e:
                print(f"[VISION WARNING] Не удалось загрузить модель лиц: {e}")
        else:
            if self.recognizer is None:
                print("[VISION WARNING] Распознаватель лиц не инициализирован")

        self.session = FaceSession()

        # 🔥 Сглаживание мерцания (Flicker Fix)
        self.last_seen = {}
        self.smooth_threshold = 5

        # Статус для UI ассистента
        self.status = "IDLE"

        self.current_frame = None
        self.telemetry = ""

        # Списки для хранения распознанных за текущий кадр данных
        self.recognized_names = []
        self.recognized_roles = []

        os.makedirs("dataset", exist_ok=True)
        os.makedirs("photos", exist_ok=True)

    # ===================================================
    # Свойства динамической авторизации (для ai_core.py)
    # ===================================================
    @property
    def current_user_id(self):
        """Возвращает ID первого распознанного пользователя в кадре"""
        for name in self.recognized_names:
            if name != "Unknown":
                user = self.user_repo.db.query(User).filter(User.name == name).first()
                if user:
                    return user.id
        return None

    @property
    def current_role(self):
        """Возвращает роль первого распознанного пользователя или GUEST"""
        for role in self.recognized_roles:
            if role != "UNKNOWN":
                return role
        return "GUEST"

    # ===================================================
    # ОСНОВНОЙ ЦИКЛ ОБРАБОТКИ
    # ===================================================
    def update(self):
        ret, frame = self.cap.read()
        if not ret:
            return False

        self.current_frame = frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)

        # Очищаем результаты предыдущего кадра
        self.recognized_names.clear()
        self.recognized_roles.clear()

        # Очередь текстов для отрисовки (чтобы не гонять PIL по кругу внутри циклов)
        texts_to_draw = [
            # {"text": f"Пользователь: {self.session.current_name}", "x": 10, "y": 10, "color": (0, 255, 0)},
            {"text": f"Статус: {self.status}", "x": 10, "y": 40, "color": (255, 255, 0)}
        ]

        for (x, y, w, h) in faces:
            name = "Unknown"
            role = "UNKNOWN"
            user_id = None
            conf = 100  # Дефолтное расстояние (100 = неизвестный)

            if self.is_model_loaded and self.recognizer is not None:
                face = gray[y:y+h, x:x+w]
                if face.size == 0:
                    continue

                face = cv2.resize(face, (200, 200))

                try:
                    label, conf = self.recognizer.predict(face)
                    if conf < 75:
                        profile = self.face_repo.get_by_label(label)
                        if profile:
                            user = self.user_repo.get_by_id(profile.user_id)
                            if user:
                                user_id = user.id
                                name = user.name
                                role = user.role
                                self._smooth_identity(user_id)
                except Exception as e:
                    print(f"[VISION ERROR] Ошибка распознавания лица: {e}")

            # Сохраняем результаты детекции для свойств авторизации ИИ
            self.recognized_names.append(name)
            self.recognized_roles.append(role)

            # Обновляем состояние сессии лица
            self.session.update(user_id, name, role, conf)

            # Цвет рамки в OpenCV (формат BGR): Зеленый для своих, Красный для чужих
            rect_color = (0, 255, 0) if user_id else (0, 0, 255)
            
            # 1. Быстро рисуем рамку средствами OpenCV
            cv2.rectangle(frame, (x, y), (x+w, y+h), rect_color, 2)

            # 2. Добавляем имя над рамкой в очередь на отрисовку через PIL
            texts_to_draw.append({
                "text": name,
                "x": x,
                "y": y - 30,
                "color": rect_color
            })

        # Накладываем весь собранный текст на кадр за ОДИН проход
        frame = self.draw_all_text(frame, text_list=texts_to_draw)
        self.current_frame = frame

        self.telemetry = f"USER={self.session.current_user_id} | {self.session.current_name}"
        return True

    # ===================================================
    # ОДНОПРОХОДНЫЙ ВЫВОД ТЕКСТА (PIL + КИРИЛЛИЦА FIX)
    # ===================================================
    def draw_all_text(self, frame, text_list):
        """Накладывает массив текстов на кадр без потерь производительности"""
        if not text_list:
            return frame

        # Переводим кадр из OpenCV (BGR) в PIL (RGB)
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)

        for item in text_list:
            txt = str(item["text"])
            # Раскладываем OpenCV BGR цвет и разворачиваем его в RGB для PIL
            b, g, r = item["color"]
            
            draw.text(
                (item["x"], item["y"]),
                txt,
                font=self.font,
                fill=(r, g, b)
            )

        # Возвращаем массив обратно в OpenCV (BGR)
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    # ===================================================
    # СГЛАЖИВАНИЕ МЕРЦАНИЯ ИДЕНТИФИКАЦИИ
    # ===================================================
    def _smooth_identity(self, user_id):
        self.last_seen[user_id] = self.last_seen.get(user_id, 0) + 1

        # Уменьшаем счетчик для остальных пользователей
        for k in list(self.last_seen.keys()):
            if k != user_id:
                self.last_seen[k] -= 1
                if self.last_seen[k] <= 0:
                    del self.last_seen[k]

        # Если лицо стабильно распознается, фиксируем его в сессии
        if self.last_seen[user_id] >= self.smooth_threshold:
            self.session.set_user(user_id)

    # ===================================================
    # ФОТО
    # ===================================================
    def save_photo(self):
        if self.current_frame is None:
            print("[VISION ERROR] Нет кадра для сохранения")
            return None

        filename = f"photos/photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        success = cv2.imwrite(filename, self.current_frame)

        if success:
            print(f"[PHOTO SAVED] {filename}")
            return filename
        else:
            print(f"[PHOTO ERROR] Ошибка записи файла {filename}")
            return None

    # ===================================================
    # СОЗДАНИЕ ДАТАСЕТА
    # ===================================================
    def create_dataset(self, user_id):
        if user_id is None:
            print("[DATASET ERROR] Не передан user_id")
            return False

        dataset_path = f"dataset/{user_id}"
        os.makedirs(dataset_path, exist_ok=True)

        count = 0
        target = 30
        print(f"[DATASET] Запуск захвата лиц для пользователя {user_id}...")

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

                print(f"[DATASET] Снимок {count + 1}/{target}")
                count += 1

                if count >= target:
                    break

            time.sleep(0.1)

        if count >= target:
            print(f"[DATASET] ✅ Датасет успешно создан для пользователя {user_id}")
            self.train_model()
            return True
        else:
            print(f"[DATASET] ⚠️ Записано только {count}/{target} образцов")
            return False

    # ===================================================
    # ОБУЧЕНИЕ МОДЕЛИ LBPH
    # ===================================================
    def train_model(self):
        if self.recognizer is None:
            print("[TRAINING ERROR] Распознаватель LBPH не инициализирован!")
            return False

        images = []
        labels = []
        label_map = {}
        next_label = 0

        print("[TRAINING] Сканирование директорий датасетов...")

        for user_folder in os.listdir("dataset"):
            user_path = os.path.join("dataset", user_folder)
            if not os.path.isdir(user_path):
                continue

            try:
                user_id = int(user_folder)
            except ValueError:
                continue

            if user_id not in label_map:
                label_map[user_id] = next_label
                next_label += 1

            label = label_map[user_id]

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
                    print(f"[TRAINING ERROR] Файл {img_path}: {e}")

        if len(images) < 2:
            print("[TRAINING ERROR] Недостаточно изображений для обучения!")
            return False

        print(f"[TRAINING] Обучение на {len(images)} изображениях для {len(label_map)} пользователей...")

        try:
            self.recognizer.train(images, np.array(labels))
            self.recognizer.write(self.model_path)
            self.is_model_loaded = True

            # Синхронизация связей меток и ID пользователей в БД
            for user_id, label in label_map.items():
                existing = self.face_repo.get_by_label(label)
                if not existing:
                    self.face_repo.create(user_id, label)

            print(f"[TRAINING] ✅ Модель обновлена и сохранена в: {self.model_path}")
            return True
        except Exception as e:
            print(f"[TRAINING ERROR] Ошибка сохранения модели: {e}")
            return False

    # ===================================================
    # СБРОС И ЗАКРЫТИЕ ПОДКЛЮЧЕНИЙ
    # ===================================================
    def release(self):
        self.cap.release()
        self.db.close()