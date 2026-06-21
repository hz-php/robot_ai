import cv2
import numpy as np
import time
from hardware.network_manager import NetworkManager

# Инициализируем сетевой менеджер для работы с ESP32 по Wi-Fi
robot = NetworkManager(ip="192.168.4.1")

# === НАСТРОЙКА КАМЕРЫ ===
# 0 — встроенная или USB вебкамера ноутбука. 
# Для телефона через IP Webcam замени на: "http://IP_АДРЕС:8080/video"
camera_source = 0

cap = cv2.VideoCapture(camera_source)

if not cap.isOpened():
    print("❌ Не удалось запустить камеру. Интерфейс будет работать в режиме симуляции (без видео).")
    has_camera = False
else:
    print("✅ Камера успешно подключена и готова к работе!")
    has_camera = True

print("\n==================================================")
print("ИНСТРУКЦИЯ ПО ДИСТАНЦИОННОМУ УПРАВЛЕНИЮ (ДИСКРЕТНЫЙ РУЛЬ):")
print("1. Обязательно кликни мышкой по окну с видео, чтобы оно стало активным.")
print("2. Кнопки управления (работают и на RU, и на EN раскладке):")
print("   [W] / [Ц] — Вперед")
print("   [S] / [Ы] — Назад")
print("   [A] / [Ф] — Поворот колес налево (до упора)")
print("   [D] / [В] — Поворот колес направо (до упора)")
print("   [Пробел]  — Мгновенный СТОП и возврат руля в ЦЕНТР")
print("   [Esc]     — Завершить программу и заглушить робота")
print("==================================================\n")

current_speed = 0
current_steer = "center"  # Доступные состояния: "left", "right", "center"

# Создаем окно для отображения панели управления
cv2.namedWindow("Robot AI Control Panel")

try:
    while True:
        # 1. Опрашиваем датчик расстояния HC-SR04 по Wi-Fi
        distance = robot.get_distance()
        
        # 2. Захватываем кадр с камеры
        if has_camera:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Потерян сигнал с видеокамеры!")
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
        else:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # 3. Алгоритм безопасности (Аварийный тормоз на 10 см)
        if distance < 10 and current_speed > 0:
            print(f"⚠️ АВАРИЙНЫЙ СТОП! Обнаружено препятствие: {distance} см")
            current_speed = 0
            robot.send_control(motor_speed=0)

        # 4. Отрисовка телеметрии на экране
        # Если дистанция опасная (меньше 20 см) — подсвечиваем красным, если всё ок — зеленым
        text_color = (0, 0, 255) if distance < 20 else (0, 255, 0)
        
        cv2.putText(frame, f"Distance: {distance} cm", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
        cv2.putText(frame, f"Speed: {current_speed} | Steer: {current_steer.upper()}", (20, 85), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Показываем обновленное окно
        cv2.imshow("Robot AI Control Panel", frame)

        # 5. Считывание команд с клавиатуры (опрос каждые 30 мс)
        key = cv2.waitKey(30) & 0xFF

        if key == 27: # Клавиша Esc
            print("Запрос на выход принят.")
            break
            
        elif key == ord('w') or key == ord('ц'):  # Вперед
            current_speed = 220  # ШИМ-скорость (чуть выше, чтобы бодро ехать от аккумуляторов 6V)
            robot.send_control(motor_speed=current_speed)
            
        elif key == ord('s') or key == ord('ы'):  # Назад
            current_speed = -220
            robot.send_control(motor_speed=current_speed)
            
        elif key == ord('a') or key == ord('ф'):  # Налево
            current_steer = "left"
            robot.send_control(steer_state=current_steer)
            
        elif key == ord('d') or key == ord('в'):  # Направо
            current_steer = "right"
            robot.send_control(steer_state=current_steer)
            
        elif key == ord(' '):  # Пробел (Полный тормоз и выравнивание колес)
            current_speed = 0
            current_steer = "center"
            print("🛑 Стоп и выравнивание руля")
            robot.send_control(motor_speed=current_speed, steer_state=current_steer)

except KeyboardInterrupt:
    print("\nСкрипт остановлен сочетанием клавиш.")

finally:
    # Блок гарантированного отключения всех систем при закрытии скрипта
    print("Завершение работы: глушим моторы и закрываем окна...")
    try:
        robot.send_control(motor_speed=0, steer_state="center")
    except:
        pass
    
    if has_camera:
        cap.release()
    cv2.destroyAllWindows()