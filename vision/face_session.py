import time


class FaceSession:
    """
    🧠 FaceID Session Engine (iPhone-like)

    Задача:
    - стабилизация личности
    - анти-flicker
    - удержание пользователя
    """

    def __init__(self):

        # текущий пользователь
        self.current_user_id = None
        self.current_name = "Unknown"
        self.current_role = "UNKNOWN"

        # стабильность (голосование)
        self.hits = {}
        self.last_seen = 0

        # настройки
        self.vote_threshold = 5
        self.timeout = 3.0  # сек

    # =========================
    # 🔥 ВОТ ЭТО ТЫ ЗАБЫЛ
    # =========================
    def set_user(self, user_id, name="Unknown", role="UNKNOWN"):
        """
        Прямое назначение пользователя (если уверен на 100%)
        """

        self.current_user_id = user_id
        self.current_name = name
        self.current_role = role
        self.last_seen = time.time()
        self.hits.clear()

    # =========================
    # 🧠 основной апдейт
    # =========================
    def update(self, user_id, name, role, confidence):
        """
        Стабилизация лица (FaceID логика)
        """

        now = time.time()

        # если никого нет
        if user_id is None:
            if now - self.last_seen > self.timeout:
                self._logout()
            return

        # голосование
        self.hits[user_id] = self.hits.get(user_id, 0) + 1
        self.last_seen = now

        # если стабильно распознан
        if self.hits[user_id] >= self.vote_threshold:
            self.current_user_id = user_id
            self.current_name = name
            self.current_role = role

            # сброс других
            self.hits.clear()

            print(f"[FaceSession] LOGIN: {name}")

    # =========================
    # logout
    # =========================
    def _logout(self):
        if self.current_user_id is not None:
            print("[FaceSession] LOGOUT")

        self.current_user_id = None
        self.current_name = "Unknown"
        self.current_role = "UNKNOWN"
        self.hits.clear()