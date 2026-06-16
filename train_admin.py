import cv2
import os
import time
import numpy as np
import speech_recognition as sr
from database.db import SessionLocal
from database.models import FaceProfile, User

def train_admin_profile():
    print("[TRAINING] Запуск комплексного обучения Администратора (Игорь, ID: 4)...")
    
    # ========================================================
    # 1. ПРОВЕРКА И НАСТРОЙКА БАЗЫ ДАННЫХ
    # ========================================================
    db = SessionLocal()
    admin_user = db.query(User).filter(User.id == 4).first()
    if not admin_user:
        print("[DB WARNING] Пользователь с ID 4 не найден в таблице users!")
        admin_user = User(id=4, name="Igor", role="admin")
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print("[DB] Создан администратор Игорь с ID 4.")
    else:
        print(f"[DB] Найден администратор: {admin_user.name} (ID: {admin_user.id})")

    profile = db.query(FaceProfile).filter(FaceProfile.user_id == 4).first()
    if profile:
        face_label = profile.face_label
    else:
        last_profile = db.query(FaceProfile).order_by(FaceProfile.face_label.desc()).first()
        face_label = (last_profile.face_label + 1) if (last_profile and last_profile.face_label is not None) else 1
        
        new_profile = FaceProfile(user_id=4, face_label=face_label, model_path="face_model.yml")
        db.add(new_profile)
        db.commit()
    
    db.close()

    # ========================================================
    # 2. ОБУЧЕНИЕ ГОЛОСА (SPEAKER RECOGNITION)
    # ========================================================
    print("\n=== ЭТАП 1: ЗАПИСЬ ОБРАЗЦОВ ГОЛОСА ===")
    try:
        import librosa
        from voice.voice_recognizer import VoiceRecognizer
        
        voice_recognizer = VoiceRecognizer(db=SessionLocal())
        recognizer = sr.Recognizer()
        sample_count = 5
        recorded = 0

        print(f"Необходимо записать {sample_count} фраз для построения слепка голоса.")
        print("Говори спокойно, обычным голосом, когда появится надпись 'Говорите!'.")
        time.sleep(2)

        for i in range(sample_count):
            try:
                with sr.Microphone() as source:
                    print(f"\n[ГОЛОС] Запись образца {i+1}/{sample_count}... Говорите!")
                    recognizer.adjust_for_ambient_noise(source, duration=0.6)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)
                    
                    # Переводим в массив numpy для librosa
                    audio_data = np.frombuffer(audio.get_raw_data(), dtype=np.int16).astype(float) / 32768.0
                    voice_recognizer.record_voice_sample(audio_data, user_id=4)
                    recorded += 1
                    print(f"[ГОЛОС] Образец {i+1} успешно сохранен ✅")
                    time.sleep(0.5)
            except Exception as e:
                print(f"[ГОЛОС ERROR] Ошибка записи семпла: {e}. Повторяем шаг...")
                
        if recorded >= 2:
            print("[ГОЛОС] Сбор семплов завершен. Извлечение признаков и обучение модели...")
            voice_recognizer.train_speaker(user_id=4)
            print("[ГОЛОС] ✅ Слепок голоса Игоря успешно сохранен в системе!")
        else:
            print("[ГОЛОС ERROR] Не удалось записать достаточно голосовых данных.")
    except ImportError:
        print("[WARNING] Библиотека librosa не установлена. Пропускаем биометрию голоса.")
    except Exception as e:
        print(f"[VOICE TRAINING SCRIPT ERROR] {e}")

    # ========================================================
    # 3. СБОР ЛИЦА И СИЛУЭТА (UPPERBODY / FACE)
    # ========================================================
    print("\n=== ЭТАП 2: ЗАПИСЬ СИЛУЭТА И ЛИЦА ===")
    dataset_path = "dataset/4"
    os.makedirs(dataset_path, exist_ok=True)

    # Загружаем каскады: лица И силуэта (голова + плечи)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    upperbody_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_upperbody.xml")
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    print("Сейчас откроется камера. Сначала сядь близко, затем немного отодвинься, чтобы робот запомнил силуэт.")
    time.sleep(2)

    count = 0
    target_samples = 60

    while count < target_samples:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Находим и лица, и верхнюю часть туловища
        faces = face_cascade.detectMultiScale(gray, 1.1, 5)
        bodies = upperbody_cascade.detectMultiScale(gray, 1.1, 3)

        # Объединяем зоны детекции для датасета
        regions = []
        for (x, y, w, h) in faces:
            regions.append((x, y, w, h, (0, 255, 0), "Face"))
        for (x, y, w, h) in bodies:
            # Силуэт берем чуть шире, но для модели распознавания вырежем верхнюю часть (голову)
            regions.append((x, y, w, int(h*0.6), (255, 0, 0), "Silhouette"))

        for (x, y, w, h, color, tag) in regions:
            roi = gray[y:y+h, x:x+w]
            if roi.size == 0:
                continue

            roi = cv2.resize(roi, (200, 200))
            filename = f"{dataset_path}/admin_{count:03d}.jpg"
            cv2.imwrite(filename, roi)
            
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, f"{tag} {count+1}/{target_samples}", (x, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            count += 1
            if count >= target_samples:
                break

        cv2.imshow("Admin Comprehensive Training...", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        time.sleep(0.04)

    cap.release()
    cv2.destroyAllWindows()

    # ========================================================
    # 4. СБОРКА И ПЕРЕОБУЧЕНИЕ ОБЩЕЙ МОДЕЛИ LBPH
    # ========================================================
    print("\n=== ЭТАП 3: КОМПИЛЯЦИЯ КАРТЫ СИЛУЭТОВ ===")
    try:
        recognizer = None
        for builder in [getattr(cv2, 'face', None), cv2]:
            if builder and hasattr(builder, 'LBPHFaceRecognizer_create'):
                recognizer = builder.LBPHFaceRecognizer_create()
                break
        
        if recognizer is None:
            print("[ERROR] Не найден LBPHFaceRecognizer.")
            return

        images = []
        labels = []

        for img_name in os.listdir(dataset_path):
            if not img_name.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            img_path = os.path.join(dataset_path, img_name)
            image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if image is None or image.size == 0:
                continue
            images.append(image)
            labels.append(int(face_label))

        recognizer.train(images, np.array(labels))
        recognizer.write("face_model.yml")
        print("\n[SUCCESS] ✅ Полная модель (Голос + Лицо + Силуэт) успешно обновлена!")

    except Exception as e:
        print(f"[TRAINING ERROR] {e}")

if __name__ == "__main__":
    train_admin_profile()