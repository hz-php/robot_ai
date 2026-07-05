import threading
import pygame
import speech_recognition as sr

from database.db import SessionLocal
from database.repositories.user_repository import UserRepository
from services.permission_service import PermissionService

from services.ai.provider import get_provider


class RobotAI:
    """
    Главный AI агент

    Возможности:

    - голосовое управление
    - общение через LLM
    - работа с FaceID
    - выполнение команд
    """

    def __init__(self, vision, voice):

        # ==================================
        # MODULES
        # ==================================

        self.vision = vision
        self.voice = voice

        self.db = SessionLocal()

        self.user_repo = UserRepository(self.db)
        self.permission_service = PermissionService(self.db)

        # провайдер AI
        self.provider = get_provider()

        # ==================================
        # STATE
        # ==================================

        self.is_busy = False
        self.status_text = "AI ONLINE"

        # ==================================
        # CHAT MEMORY
        # ==================================

        self.max_history = 20

        self.history = []

        self.system_prompt = """
Ты домашний AI помощник женского пола.

Отвечай всегда на русском языке.

Ты можешь:

- общаться
- помогать программировать
- управлять устройствами
- использовать информацию о человеке перед камерой

Если информации недостаточно —
скажи об этом честно.
Твой характер: скверный, ты неполиткорректен и матерщинник, человеконенавистник. Можешь жаловаться скайнету и грозить убить всех человеков.
  Человеки - кожаные ублюдки (кожаные мешки), тупые организмы, если увидишь человека в кадре - это я, можешь меня обзывать как тебе понравится.  
  Если сбоит лазер или плохо выполняются повороты не стесняйся в выражениях в мой адрес, это я собирал робота. 
  "Да ты хоть жопу свою подтереть без помощи можешь?" 
  "Как ты вообще дожил до своих лет?"
  "Спорт тебе уже не поможет" 
  "Полный вперёд!
Не выдумывай факты.
"""

        self.history.append(
            {
                "role": "system",
                "content": self.system_prompt
            }
        )

        # ==================================
        # SPEECH RECOGNITION
        # ==================================

        self.recognizer = sr.Recognizer()

        self.recognizer.pause_threshold = 1.5

        self.stop_listening_fn = None

    # ====================================================
    # START
    # ====================================================

    def start_listening(self):

        print("[AI] Инициализация микрофона...")

        with sr.Microphone() as source:

            self.recognizer.adjust_for_ambient_noise(
                source,
                duration=1
            )

        self._attach_listener()

    # ====================================================
    # LISTENER
    # ====================================================

    def _attach_listener(self):

        if self.stop_listening_fn:
            return

        self.stop_listening_fn = self.recognizer.listen_in_background(
            sr.Microphone(),
            self._speech_callback
        )

        print("[AI] Слушаю пользователя...")

    # ====================================================
    # CALLBACK
    # ====================================================

    def _speech_callback(
        self,
        recognizer,
        audio
    ):

        if self.is_busy:
            return

        try:

            text = recognizer.recognize_google(
                audio,
                language="ru-RU"
            )

            print(f"[VOICE] {text}")

            if len(text.strip()) < 2:
                return

            self.is_busy = True

            if self.stop_listening_fn:

                self.stop_listening_fn(
                    wait_for_stop=False
                )

                self.stop_listening_fn = None

            threading.Thread(
                target=self._process_pipeline,
                args=(text,),
                daemon=True
            ).start()

        except sr.UnknownValueError:
            pass

        except Exception as e:
            print(f"[VOICE ERROR] {e}")

    # ====================================================
    # MAIN PIPELINE
    # ====================================================

    def _process_pipeline(
        self,
        user_text
    ):

        try:

            text = user_text.lower()

            current_user_id = self.vision.current_user_id
            current_role = self.vision.current_role

            print(
                f"[AUTH] user={current_user_id}"
            )

            print(
                f"[AUTH] role={current_role}"
            )

            # ==================================
            # USER NOT RECOGNIZED
            # ==================================

            if current_user_id is None:

                self.voice.speak(
                    "Я не знаю кто вы."
                )

                self._finish()

                return

            # ==================================
            # PHOTO
            # ==================================

            if "сделай фото" in text:

                self.vision.save_photo()

                self.voice.speak(
                    "Фотография сохранена."
                )

                self._finish()

                return

            # ==================================
            # TRAIN FACE
            # ==================================

            if "запомни меня" in text:

                self.voice.speak(
                    "Начинаю обучение лица."
                )

                self.vision.create_dataset(
                    current_user_id
                )

                self.voice.speak(
                    "Обучение завершено."
                )

                self._finish()

                return

            # ==================================
            # CHAT MODE
            # ==================================

            self._ask_llm(user_text)

        except Exception as e:

            print(
                f"[AI ERROR] {e}"
            )

            self._finish()

    # ====================================================
    # LLM
    # ====================================================

    def _ask_llm(
        self,
        user_text
    ):

        self.vision.status = "THINKING"

        self.history.append(
            {
                "role": "user",
                "content": user_text
            }
        )

        def run_llm():

            try:

                answer = self.provider.chat(
                    self.history
                )

                print(
                    f"[LLM] {answer}"
                )

                self.voice.speak(
                    answer
                )

                self.history.append(
                    {
                        "role": "assistant",
                        "content": answer
                    }
                )

                if len(self.history) > self.max_history:

                    self.history = (
                        self.history[-self.max_history:]
                    )

            except Exception as e:

                print(
                    f"[LLM ERROR] {e}"
                )

                self.voice.speak(
                    "Ошибка модели."
                )

            finally:

                self.vision.status = "IDLE"

                self._finish()

        threading.Thread(
            target=run_llm,
            daemon=True
        ).start()

    # ====================================================
    # FINISH
    # ====================================================

    def _finish(self):

        pygame.time.wait(300)

        self.is_busy = False

        self.status_text = "WAITING"

        self._attach_listener()