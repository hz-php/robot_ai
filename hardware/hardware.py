import requests

class Hardware:
    """
    Подсистема Hardware v2.1 (Wi-Fi Bridge для Арчи с поддержкой серво-локатора)
    """
    def __init__(self, port=None, ip="192.168.4.1"):
        self.base_url = f"http://{ip}"
        print(f"[HARDWARE] Аппаратный модуль запущен! Целевой адрес точки доступа: {self.base_url}")

    def distance(self):
        """Быстрый запрос расстояния прямо (для вывода на экран в main.py)"""
        try:
            response = requests.get(f"{self.base_url}/distance", timeout=0.2)
            if response.status_code == 200:
                return float(response.text)
            return 999.0
        except Exception:
            return 999.0

    def get_distance(self):
        """Алиас для совместимости со старым кодом AIAgent"""
        return self.distance()

    def scan_sectors(self):
        """
        Заставляет сервопривод покрутить головой (Влево -> Прямо -> Вправо).
        Возвращает словарь: {'left': X, 'center': Y, 'right': Z}
        Таймаут увеличен до 1.5 сек, так как физическому мотору нужно время на поворот.
        """
        try:
            response = requests.get(f"{self.base_url}/scan", timeout=1.5)
            if response.status_code == 200:
                return response.json() # Автоматически превращает JSON от ESP32 в словарь Python
            return {"left": 999, "center": 999, "right": 999}
        except Exception as e:
            print(f"[HARDWARE ERROR] Ошибка сканирования локатора: {e}")
            return {"left": 999, "center": 999, "right": 999}

    def send_control(self, motor_speed=None, steer_state=None):
        """Отправляет пакет команд движения на WebServer ESP32"""
        params = {}
        if motor_speed is not None:
            params['motor'] = int(motor_speed)
        if steer_state is not None:
            params['steer'] = str(steer_state)

        if not params:
            return

        try:
            requests.get(f"{self.base_url}/control", params=params, timeout=0.3)
        except Exception as e:
            print(f"[HARDWARE ERROR] Не удалось отправить команду движения: {e}")