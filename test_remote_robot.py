import cv2
import numpy as np
import time
import keyboard  # Отвечает за одновременное чтение нескольких клавиш
from hardware.network_manager import NetworkManager

# Инициализируем сетевой менеджер для работы с ESP32 по Wi-Fi
robot = NetworkManager(ip="192.168.4.1")

# === НАСТРОЙКА КАМЕРЫ ===
camera_source = 0
cap = cv2.VideoCapture(camera_source)

if not cap.isOpened():
    print("❌ Не удалось запустить камеру. Работа в режиме симуляции (без видео).")
    has_camera = False
else:
    print("✅ Камера успешно подключена!")
    has_camera = True

print("\n==================================================")
print("СИСТЕМА ПАРАЛЛЕЛЬНОГО УПРАВЛЕНИЯ АКТИВИРОВАНА:")
print("1. Зажмите [W]+[A] для плавного поворота в движении вперед.")
print("2. Зажмите [S]+[D] для плавного поворота при движении назад.")
print("3. ОТПУСТИТЕ ВСЕ КНОПКИ — машина сама плавно остановится и выровняет руль!")
print("==================================================\n")

# Переменные для кеширования прошлых команд (защита Wi-Fi от перегрузки)
last_speed = 0
last_steer = "center"

# === НАСТРОЙКА ДИСТАНЦИИ БЕЗОПАСНОСТИ ===
# Увеличьте это число (например, до 45), если машина все еще успевает докатиться до стены
STOP_DISTANCE = 35 

cv2.namedWindow("Robot AI Control Panel")

try:
    while True:
        # 1. Опрашиваем датчик расстояния HC-SR04 по Wi-Fi
        distance = robot.get_distance()
        
        # 2. Получаем кадр с камеры
        if has_camera:
            ret, frame = cap.read()
            if not ret:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
        else:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # 3. ПАРАЛЛЕЛЬНЫЙ ОПРОС КЛАВИАТУРЫ
        # По умолчанию (если ничего не нажато) — стоим прямо и не едем
        motor_speed = 0
        steer_state = "center"

        # Проверяем кнопки ДВИЖЕНИЯ
        if keyboard.is_pressed('w') or keyboard.is_pressed('ц'):
            motor_speed = 220  # Едем вперед
        elif keyboard.is_pressed('s') or keyboard.is_pressed('ы'):
            motor_speed = -220 # Едем назад

        # Проверяем кнопки ПОВОРОТА (работают параллельно с ходом!)
        if keyboard.is_pressed('a') or keyboard.is_pressed('ф'):
            steer_state = "left"   # Руль влево
        elif keyboard.is_pressed('d') or keyboard.is_pressed('в'):
            steer_state = "right"  # Руль вправо

        # 4. АЛГОРИТМ ПРЕДВАРИТЕЛЬНОГО ТОРМОЖЕНИЯ
        # Если до препятствия осталось меньше STOP_DISTANCE, а мы пытаемся ехать вперед:
        if distance < STOP_DISTANCE and motor_speed > 0:
            print(f"⚠️ РЕЖИМ УМНОГО ТОРМОЖЕНИЯ! Препятствие: {distance} см. Заблаговременно гасим мотор.")
            motor_speed = 0  # Принудительно отключаем мотор хода, чтобы машина гасила скорость накатом

        # 5. ОТПРАВКА ДАННЫХ ПАКЕТОМ (Только при изменении состояния!)
        # Если текущие команды не совпадают с прошлыми — отправляем их на робота
        if motor_speed != last_speed or steer_state != last_steer:
            robot.send_control(steer_state=steer_state, motor_speed=motor_speed)
            
            # Обновляем кэш состояний
            last_speed = motor_speed
            last_steer = steer_state

        # 6. Отрисовка телеметрии на экране
        text_color = (0, 0, 255) if distance < STOP_DISTANCE else (0, 255, 0)
        cv2.putText(frame, f"Distance: {distance} cm", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
        cv2.putText(frame, f"Speed: {motor_speed} | Steer: {steer_state.upper()}", (20, 85), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Robot AI Control Panel", frame)

        # Обработка закрытия программы по нажатию Esc на окне OpenCV
        if cv2.waitKey(10) & 0xFF == 27:
            print("Запрос на выход принят.")
            break

except KeyboardInterrupt:
    print("\nСкрипт остановлен.")

finally:
    print("Завершение работы: глушим все системы...")
    try:
        # Гарантированно обесточиваем все моторы при выходе
        robot.send_control(motor_speed=0, steer_state="center")
    except:
        pass
    if has_camera:
        cap.release()
    cv2.destroyAllWindows()