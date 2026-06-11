class ToolRouter:

    def __init__(self, vision, voice, db, face_repo, user_repo):

        self.vision = vision
        self.voice = voice

        self.db = db
        self.face_repo = face_repo
        self.user_repo = user_repo

    # =========================
    # EXECUTE TOOL
    # =========================
    def run(self, tool_name, payload=None):

        payload = payload or {}

        # -------------------------
        # PHOTO
        # -------------------------
        if tool_name == "take_photo":
            path = self.vision.save_photo()
            return f"Фото сохранено: {path}"

        # -------------------------
        # USER INFO
        # -------------------------
        if tool_name == "who_am_i":

            user = self.vision.session.current_user_id

            if not user:
                return "Пользователь не распознан"

            db_user = self.user_repo.get_by_id(user)

            return f"Ты {db_user.name}, роль {db_user.role}"

        # -------------------------
        # FACE TRAINING
        # -------------------------
        if tool_name == "train_face":

            user_id = payload.get("user_id")

            self.vision.create_dataset(user_id)

            return "Обучение завершено"

        return "Неизвестный инструмент"