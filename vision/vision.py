import cv2
import os
import numpy as np
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

from database.db import SessionLocal
from database.repositories.user_repository import UserRepository
from database.repositories.face_repository import FaceRepository
from vision.face_session import FaceSession

def _init_face_recognizer():
    try:
        if not hasattr(cv2, 'face'):
            print("[CRITICAL] Модуль cv2.face отсутствует! Установите opencv-contrib-python")
            return None
        return cv2.face.LBPHFaceRecognizer_create()
    except Exception as e:
        print(f"[ERROR] Не удалось инициализировать LBPH: {e}")
        return None

class CameraVision:
    def __init__(self):
        print(f"[DEBUG] OpenCV version: {cv2.__version__}")
        
        # Загрузка шрифта
        self.font = ImageFont.load_default()
        try:
            self.font = ImageFont.truetype("arial.ttf", 20)
        except:
            pass

        self.db = SessionLocal()
        self.user_repo = UserRepository(self.db)
        self.face_repo = FaceRepository(self.db)

        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        
        print("[VISION] Загрузка нейросети YOLOv8...")
        self.yolo_model = YOLO("yolov8n.pt") 
        
        # 🔥 Полный словарь COCO (80 классов) для YOLOv8
        self.coco_ru = {
            "person": "человек", "bicycle": "велосипед", "car": "машина", "motorcycle": "мотоцикл", 
            "airplane": "самолет", "bus": "автобус", "train": "поезд", "truck": "грузовик", "boat": "лодка", 
            "traffic light": "светофор", "fire hydrant": "пожарный гидрант", "stop sign": "знак стоп", 
            "parking meter": "паркомат", "bench": "скамейка", "bird": "птица", "cat": "кошка", 
            "dog": "собака", "horse": "лошадь", "sheep": "овца", "cow": "корова", "elephant": "слон", 
            "bear": "медведь", "zebra": "зебра", "giraffe": "жираф", "backpack": "рюкзак", 
            "umbrella": "зонт", "handbag": "сумка", "tie": "галстук", "suitcase": "чемодан", 
            "frisbee": "фрисби", "skis": "лыжи", "snowboard": "сноуборд", "sports ball": "мяч", 
            "kite": "воздушный змей", "baseball bat": "бейсбольная бита", "baseball glove": "бейсбольная перчатка", 
            "skateboard": "скейтборд", "surfboard": "доска для серфинга", "tennis racket": "теннисная ракетка", 
            "bottle": "бутылка", "wine glass": "бокал", "cup": "чашка", "fork": "вилка", "knife": "нож", 
            "spoon": "ложка", "bowl": "миска", "banana": "банан", "apple": "яблоко", "sandwich": "сэндвич", 
            "orange": "апельсин", "broccoli": "брокколи", "carrot": "морковь", "hot dog": "хот-дог", 
            "pizza": "пицца", "donut": "пончик", "cake": "торт", "chair": "стул", "couch": "диван", 
            "potted plant": "комнатное растение", "bed": "кровать", "dining table": "обеденный стол", 
            "toilet": "унитаз", "tv": "телевизор", "laptop": "ноутбук", "mouse": "мышь", "remote": "пульт", 
            "keyboard": "клавиатура", "cell phone": "телефон", "microwave": "микроволновка", "oven": "духовка", 
            "toaster": "тостер", "sink": "раковина", "refrigerator": "холодильник", "book": "книга", 
            "clock": "часы", "vase": "ваза", "scissors": "ножницы", "teddy bear": "плюшевый медведь", 
            "hair drier": "фен", "toothbrush": "зубная щетка"
        }
        
        self.recognizer = _init_face_recognizer()
        self.model_path = "face_model.yml"
        self.is_model_loaded = False
        
        if self.recognizer and os.path.exists(self.model_path):
            try:
                self.recognizer.read(self.model_path)
                self.is_model_loaded = True
                print("[VISION] Модель лиц успешно загружена")
            except Exception as e:
                print(f"[VISION WARNING] Не удалось загрузить модель лиц: {e}")

        self.session = FaceSession()
        self.status = "IDLE"
        self.current_frame = None
        self.frame_counter = 0

        self.recognized_names = []
        self.detected_objects = []

    def update(self):
        ret, frame = self.cap.read()
        if not ret: return False

        self.current_frame = frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.frame_counter += 1

        # 1. Распознавание лиц
        faces = self.face_cascade.detectMultiScale(gray, 1.2, 5)
        self.recognized_names.clear()

        for (x, y, w, h) in faces:
            name, color = "Unknown", (0, 0, 255)
            if self.is_model_loaded:
                roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
                label, conf = self.recognizer.predict(roi)
                if conf < 70:
                    profile = self.face_repo.get_by_label(label)
                    if profile and profile.user_id == 4:
                        name, color = "Igor", (0, 255, 0)
            
            self.recognized_names.append(name)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        # 2. Детекция предметов (YOLO работает каждый второй кадр)
        if self.frame_counter % 2 == 0:
            results = self.yolo_model(frame, verbose=False, conf=0.45) # Чуть снизил порог для лучшей видимости
            self.detected_objects.clear()
            
            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    eng_name = self.yolo_model.names[cls]
                    
                    if eng_name != "person":
                        # Переводим на русский, если слова нет в словаре - оставляем английский
                        ru_name = self.coco_ru.get(eng_name, eng_name)
                        
                        if ru_name not in self.detected_objects:
                            self.detected_objects.append(ru_name)
                            # 🔥 ЛОГИРУЕМ В КОНСОЛЬ
                            print(f"[VISION-YOLO] Обнаружено: {ru_name} (уверенность: {float(box.conf[0]):.2f})")
                        
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 100, 0), 2)
                        # Добавляем подпись на видео
                        #cv2.putText(frame, ru_name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 0), 2)
                        # ВСТАВЬ ВМЕСТО НЕЁ:
                        frame = self.put_russian_text(frame, ru_name, x1, max(0, y1-25), (255, 100, 0))
        self.current_frame = frame
        return True

    def release(self):
        self.cap.release()
        self.db.close()
        
    def put_russian_text(self, frame, text, x, y, color):
        # Преобразуем кадр из формата OpenCV в формат PIL
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        # OpenCV использует цвета BGR, а PIL - RGB, поэтому меняем местами
        b, g, r = color
        draw.text((x, y), text, font=self.font, fill=(r, g, b))
        
        # Возвращаем кадр обратно в формат OpenCV
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)