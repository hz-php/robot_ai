import requests

class NetworkManager:
    def __init__(self, ip="192.168.4.1"):
        self.base_url = f"http://{ip}"
        self.session = requests.Session()  # Оптимизирует скорость частых HTTP-запросов

    def send_control(self, steer_state=None, motor_speed=None):
        params = {}
        if steer_state is not None:
            params['steer'] = steer_state  # Передаем 'left', 'right' или 'center'
        if motor_speed is not None:
            params['motor'] = motor_speed
            
        try:
            # Ставим очень короткий таймаут (0.1 сек), чтобы питон не зависал, ожидая ответа от ESP32
            self.session.get(f"{self.base_url}/control", params=params, timeout=0.1)
        except requests.exceptions.RequestException:
            pass

    def get_distance(self):
        try:
            response = self.session.get(f"{self.base_url}/distance", timeout=0.1)
            return int(response.text)
        except:
            return 999  # Если связь оборвалась, возвращаем безопасное "далекое" расстояние