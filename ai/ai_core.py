import threading
import ollama
import pygame
import speech_recognition as sr

from database.db import SessionLocal
from database.repositories.user_repository import UserRepository
from services.permission_service import PermissionService
from config import OLLAMA_TEXT_MODEL


class RobotAI:
    """
    🧠 AI Agent v1

    - ChatGPT режим общения
    - команды отдельно
    - доступ к FaceID (vision)
    """

    def __init__(self, vision, voice):

        # =========================
        # MODULES
        # =========================
        self.vision = vision
        self.voice = voice

        self.db = SessionLocal()
        self.user_repo = UserRepository(self.db)
        self.permission_service = PermissionService(self.db)

        # =========================
        # STATE
        # =========================
        self.is_busy = False
        self.status_text = "AI ONLINE"

        # =========================
        # CHAT MEMORY
        # =========================
        self.history = []
        self.max_history = 10

        self.system_prompt = """
Ты — AI агент уровня ChatGPT.

Ты умеешь:
- отвечать на вопросы
- выполнять команды
- использовать контекст пользователя

ПРАВИЛА:
1. Всегда отвечай как ChatGPT (развернуто, понятно)
2. Если есть команда — выполняй её отдельно
3. Если команды нет — просто общайся
4. У тебя есть доступ к:
   - камере (vision)
   - базе данных пользователей
   - голосу
"""

        self.history.append({
            "role": "system",
            "content": self.system_prompt
        })

        # =========================
        # VOICE
        # =========================
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.8
        self.stop_listening_fn = None

    # ===================================================
    # START LISTENING
    # ===================================================
    def start_listening(self):

        print("[AI] Microphone ready")

        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

        self._attach_listener()

    def _attach_listener(self):

        self.stop_listening_fn = self.recognizer.listen_in_background(
            sr.Microphone(),
            self._speech_callback
        )

        print("[AI] Voice active")

    # ===================================================
    # SPEECH CALLBACK
    # ===================================================
    def _speech_callback(self, recognizer, audio):

        if self.is_busy:
            return

        try:
            text = recognizer.recognize_google(audio, language="ru-RU")

            print(f"[VOICE]: {text}")

            if len(text.strip()) < 2:
                return

            self.is_busy = True

            if self.stop_listening_fn:
                self.stop_listening_fn(wait_for_stop=False)

            thread = threading.Thread(
                target=self._process_pipeline,
                args=(text,)
            )
            thread.daemon = True
            thread.start()

        except sr.UnknownValueError:
            pass
        except Exception as e:
            print(f"[VOICE ERROR]: {e}")

    # ===================================================
    # MAIN PIPELINE
    # ===================================================
    def _process_pipeline(self, user_text):

        try:
            text = user_text.lower()

            current_user_id = self.vision.current_user_id
            current_role = self.vision.current_role

            print(f"[AUTH] USER={current_user_id}")
            print(f"[AUTH] ROLE={current_role}")

            # =========================
            # NO USER
            # =========================
            if current_user_id is None:
                self.voice.speak("Я не знаю кто вы.")
                self._finish()
                return

            # =========================
            # COMMAND MODE
            # =========================
            if "сделай фото" in text:
                self.vision.save_photo()
                self.voice.speak("Фото сохранено")
                self._finish()
                return

            if "запомни меня" in text:
                self.voice.speak("Начинаю обучение лица")
                self.vision.create_dataset(current_user_id)
                self._finish()
                return

            # =========================
            # CHAT MODE (ChatGPT)
            # =========================
            self._ask_llm(user_text)

        except Exception as e:
            print(f"[AI ERROR]: {e}")

        self._finish()

    # ===================================================
    # LLM (ChatGPT mode)
    # ===================================================
    def _ask_llm(self, user_text):

        # 🔥 UI STATUS (камера показывает "thinking")
        self.vision.status = "THINKING"

        # добавляем в память
        self.history.append({
            "role": "user",
            "content": user_text
        })

        def run_llm():

            try:
                response = ollama.chat(
                    model=OLLAMA_TEXT_MODEL,
                    messages=self.history
                )

                answer = response["message"]["content"]

                print(f"[LLM]: {answer}")

                self.voice.speak(answer)

                self.history.append({
                    "role": "assistant",
                    "content": answer
                })

                # ограничение памяти
                if len(self.history) > self.max_history:
                    self.history = self.history[-self.max_history:]

            except Exception as e:
                print(f"[OLLAMA ERROR]: {e}")
                self.voice.speak("Ошибка модели")

            finally:
                self.vision.status = "IDLE"
                self._finish()

        # 🔥 ВАЖНО: запуск в отдельном потоке
        threading.Thread(target=run_llm, daemon=True).start()

    # ===================================================
    # FINISH
    # ===================================================
    def _finish(self):

        pygame.time.wait(300)

        self.is_busy = False

        self.status_text = "WAITING"

        self._attach_listener()