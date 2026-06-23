import cv2
import threading  # Для потокобезопасности при обработке голоса
import time       # Для микро-пауз аудиокарты

from database.db import SessionLocal
from database.repositories.user_repository import UserRepository
from database.repositories.voice_profiles_repository import VoiceProfileRepository

from vision.vision import CameraVision
from voice.voice import NeuroVoice
from ai.brain import Brain
from ai.agent import AIAgent
from ai.tools.tool_router import ToolRouter

# Импортируем нашу аппаратную подсистему
from hardware.hardware import Hardware

# Создаем глобальный замок для ИИ-агента, чтобы защитить аудио-микшер
agent_lock = threading.Lock()


def check_database():
    """Проверка и инициализация структуры БД"""
    try:
        print("[DB] Checking database structure...")
        db = SessionLocal()
        
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
    """Проверка существования Администратора systems"""
    db = SessionLocal()
    users = UserRepository(db)

    admin = users.get_by_name("Igor")
    if not admin:
        admin = users.create(name="Igor", role="ADMIN")
        print(f"[DB] Администратор {admin.name} создан с ID {admin.id}")
    else:
        print(f"[DB] Администратор {admin.name} найден в базе (ID: {admin.id})")

    db.close()
    return


if __name__ == "__main__":

    # 🔍 Проверяем структуру базы данных
    if not check_database():
        print("[ERROR] Please run: python migration_voice_profiles.py")
        exit(1)

    bootstrap()

    # Инициализация подсистем зрения и звука
    vision = CameraVision()
    voice_repo = VoiceProfileRepository(vision.db)
    voice = NeuroVoice(db=vision.db, voice_repo=voice_repo)

    # Инициализация ИИ-компонентов
    brain = Brain(username="Игорь")
    tools = ToolRouter(
        vision=vision,
        voice=voice,
        db=vision.db,
        face_repo=vision.face_repo,
        user_repo=vision.user_repo
    )

    # 🛠️ ШАГ 1: Инициализируем железную плату РОБОТА ДО создания агента
    # (так как у тебя COM6, Арчи бу
    # дет слать команды управления через этот порт)
    hardware = Hardware(ip="192.168.4.1")

    # 🛠️ ШАГ 2: Создаем агента Арчи и передаем ему управление железом (robot=hardware)
    agent = AIAgent(vision, voice, brain, tools, robot=hardware)

    # Обертка для микрофона, защищающая от одновременных вызовов
    def safe_voice_handle(text):
        with agent_lock:
            # Робот отвечает СТРОГО на то, что услышал в микрофон
            agent.handle(text)
            time.sleep(0.5) # Даем аудио-карте передышку после воспроизведения

    # Связываем подсистему звука с безопасным методом обработки
    voice.on_text = safe_voice_handle
    
    # Запускаем фоновый микрофон и сохраняем функцию отключения
    agent.stop_listening_fn = voice.start_background_listener()

    print("[SYSTEM] Робот запущен в интерактивном режиме. Арчи готов рулить и язвить...")

    # Главный видео-цикл робота
    while True:
        if not vision.update():
            break

        frame = vision.current_frame

        # Опрашиваем датчик расстояния для вывода на экран (инженерная телеметрия)
        dist = hardware.distance()
        
        if dist is not None:
            # 🛠️ ШАГ 3: Меняем порог безопасности на 35.0 см, чтобы соответствовать логике наката
            STOP_DISTANCE = 35.0
            is_obstacle_near = (0 < dist < STOP_DISTANCE)
            color = (0, 0, 255) if is_obstacle_near else (0, 255, 0)
            
            # Пишем статус дальномера на экран
            sonar_text = f"Sonar: {dist} cm" if dist != -1 else "Sonar: Clear / Out of range"
            cv2.putText(frame, sonar_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
            
            if is_obstacle_near:
                    hardware.send_control(motor_speed=0, steer_state="center")
                    cv2.putText(
                        frame, 
                        "WARNING: OBSTACLE NEAR ", 
                        (20, 70), 
                        cv2.FONT_HERSHEY_SIMPLEX,  # 4-й: Шрифт (теперь на месте)
                        0.6,                       # 5-й: Масштаб
                        (0, 0, 255),               # 6-й: Цвет BGR (Красный)
                        2,                         # 7-й: Толщина линии
                        cv2.LINE_AA                # 8-й: Сглаживание
                    )

        # Вывод окна детекции на экран (Обновили версию до 3.7)
        cv2.imshow("ARCHIE AI AGENT v3.7 (Drive Integrated)", frame)

        # Выход по клавише ESC (код 27)
        if cv2.waitKey(1) == 27:
            break

    # Корректное закрытие
    vision.release()
    cv2.destroyAllWindows()