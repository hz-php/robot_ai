import cv2
import os
import time
import numpy as np
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO  # 🔥 Импортируем YOLO

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
            "arial.ttf"
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

        # Каскад оставляем ТОЛЬКО для точного поиска лиц крупным планом
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        
        # 🔥 Вместо каскада силуэтов загружаем нейросеть YOLO (нано-версия, быстрая)
        print("[VISION] Загрузка нейросети YOLOv8...")
        self.yolo_model = YOLO("yolov8n.pt") 
        
        # Словарь перевода основных предметов на русский для вывода в интерфейс
        self.object_labels_ru = {
            "person": "Человек", "laptop": "Ноутбук", "cell phone": "Телефон",
            "cup": "Чашка", "chair": "Стул", "bottle": "Бутылка", 
            "backpack": "Рюкзак", "umbrella": "Зонт", "handbag": "Сумка",
            "tie": "Галстук", "suitcase": "Чемодан", "bird": "Птица", 
            "cat": "Кошка", "dog": "Собака", "mouse": "Мышь компьютерная",
            "keyboard": "Клавиатура", "tvmonitor": "Монитор/ТВ", "book": "Книга"
        }

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

        # По дефолту сессия жестко настроена на тебя
        self.session = FaceSession()
        self.session.current_user_id = 4
        self.session.current_name = "Igor"
        self.session.current_role = "ADMIN"

        self.status = "IDLE"
        self.current_frame = None
        self.telemetry = "USER=4 | Igor (ADMIN)"

        # Списки распознанного на текущем кадре
        self.recognized_names = []
        self.recognized_roles = []
        self.detected_objects = []  # 🔥 Список предметов для передачи в AI Agent

        os.makedirs("photos", exist_ok=True)

    @property
    def current_user_id(self):
        return 4

    @property
    def current_role(self):
        return "ADMIN"

    # ===================================================
    # ОСНОВНОЙ ЦИКЛ ОБРАБОТКИ
    # ===================================================
    def update(self):
        ret, frame = self.cap.read()
        if not ret:
            return False

        self.current_frame = frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. Сначала ищем лица каскадом Хаара для авторизации
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)

        self.recognized_names.clear()
        self.recognized_roles.clear()
        self.detected_objects.clear()

        texts_to_draw = [
            {"text": f"Статус: {self.status}", "x": 10, "y": 40, "color": (255, 255, 0)}
        ]

        # Обработка лиц Игоря / Гостей
        for (x, y, w, h) in faces:
            name = "Unknown"
            role = "GUEST"
            
            if self.is_model_loaded and self.recognizer is not None:
                roi = gray[y:y+h, x:x+w]
                if roi.size > 0:
                    roi = cv2.resize(roi, (200, 200))
                    try:
                        label, conf = self.recognizer.predict(roi)
                        if conf < 60:  # Строгий порог для лица
                            profile = self.face_repo.get_by_label(label)
                            if profile and profile.user_id == 4:
                                name = "Igor"
                                role = "ADMIN"
                    except Exception as e:
                        print(f"[VISION ERROR] Ошибка предикта лица: {e}")

            if name == "Igor":
                if "Igor" not in self.recognized_names:
                    self.recognized_names.append("Igor")
                    self.recognized_roles.append("ADMIN")
                rect_color = (0, 255, 0)
                label_text = "Igor (ADMIN)"
            else:
                self.recognized_names.append("Unknown")
                self.recognized_roles.append("GUEST")
                rect_color = (0, 0, 255)
                label_text = "Unknown Guest"

            cv2.rectangle(frame, (x, y), (x+w, y+h), rect_color, 2)
            texts_to_draw.append({"text": label_text, "x": x, "y": max(10, y - 30), "color": rect_color})

        # 2. 🔥 ЗАПУСКАЕМ ДЕТЕКЦИЮ ПРЕДМЕТОВ ЧЕРЕЗ YOLO
        # stream=True позволяет обрабатывать видеопоток быстрее
        yolo_results = self.yolo_model(frame, verbose=False, conf=0.4) # Порог уверенности 40%

        for result in yolo_results:
            boxes = result.boxes
            for box in boxes:
                # Получаем координаты предмета
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                # Получаем имя класса (на английском)
                class_id = int(box.cls[0])
                class_name = self.yolo_model.names[class_id]

                # Пропускаем "person", так как людей мы уже обработали каскадом лица отдельно
                if class_name == "person":
                    continue

                # Переводим на русский, если есть в нашем словаре
                display_name = self.object_labels_ru.get(class_name, class_name)
                
                # Добавляем в массив детекции (чтобы агент знал, что видит робот)
                if display_name not in self.detected_objects:
                    self.detected_objects.append(display_name)

                # Рисуем рамку предмета (синяя рамка для неодушевленных объектов)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 100, 0), 2)
                texts_to_draw.append({
                    "text": display_name,
                    "x": x1,
                    "y": max(10, y1 - 25),
                    "color": (255, 100, 0)
                })

        frame = self.draw_all_text(frame, text_list=texts_to_draw)
        self.current_frame = frame
        return True

    def draw_all_text(self, frame, text_list):
        if not text_list:
            return frame
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        for item in text_list:
            txt = str(item["text"])
            b, g, r = item["color"]
            draw.text((item["x"], item["y"]), txt, font=self.font, fill=(r, g, b))
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def save_photo(self):
        if self.current_frame is None:
            return None
        filename = f"photos/photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        success = cv2.imwrite(filename, self.current_frame)
        return filename if success else None

    def release(self):
        self.cap.release()
        self.db.close()