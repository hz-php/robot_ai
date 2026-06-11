import threading
import ollama
import speech_recognition as sr

from config import OLLAMA_TEXT_MODEL


class AIAgent:
    """
    AI Agent v1
    - ChatGPT режим
    - команды отдельно
    - async LLM (НЕ БЛОКИРУЕТ)
    """

    def __init__(self, vision, voice, brain, tools):

        self.vision = vision
        self.voice = voice
        self.brain = brain
        self.tools = tools

        self.is_busy = False

        self.history = [{
            "role": "system",
            "content": """
Ты — AI агент уровня ChatGPT.

Правила:
- всегда отвечай как ChatGPT
- если есть команда — обрабатывай отдельно
- если команды нет — просто общайся
- используй контекст камеры и пользователя
"""
        }]

        # voice state
        self.recognizer = sr.Recognizer()
        self.stop_listening_fn = None

    # =========================
    # MAIN ENTRY
    # =========================
    def handle(self, text: str):

        if self.is_busy:
            return

        self.is_busy = True

        t = text.lower()

        # =========================
        # COMMANDS
        # =========================
        if "сделай фото" in t:
            self.voice.speak(self.vision.save_photo())
            self._finish()
            return

        if "запомни меня" in t:
            self.voice.speak("Спасибо! Как вас зовут?")
            self.vision.status = "WAITING_NAME..."

            def get_name():
                try:
                    # Слушаем имя пользователя
                    name = self.voice.listen_once_with_timeout(timeout=5)

                    if not name or len(name.strip()) < 2:
                        self.voice.speak("Не услышал имя, повторите пожалуйста")
                        self.vision.status = "IDLE"
                        self._finish()
                        return

                    name = name.strip()
                    self.voice.speak(f"Хорошо, {name}! Начинаю обучение")
                    self.vision.status = "TRAINING..."

                    # Получаем ID пользователя
                    user_id = self.vision.session.current_user_id
                    
                    # Обновляем имя в БД
                    current_user = self.vision.user_repo.get_by_id(user_id)
                    if current_user:
                        current_user.name = name
                        self.vision.db.commit()
                        self.vision.session.current_name = name
                        # Обновляем имя в Brain
                        self.brain.set_username(name)

                    # Обучаем лицо
                    self.vision.create_dataset(user_id)
                    self.voice.speak(f"Обучение завершено! Теперь я тебя узнаю, {name}")

                except Exception as e:
                    print(f"[NAME ERROR] {e}")
                    self.voice.speak("Ошибка при обучении")
                finally:
                    self.vision.status = "IDLE"
                    self._finish()

            threading.Thread(target=get_name, daemon=True).start()
            return

        if "запомни мой голос" in t:
            self.voice.speak("Начинаю запись голоса")
            self.vision.status = "VOICE_TRAINING..."

            def train_voice():
                try:
                    current_user = self.vision.session.current_user_id
                    if not current_user:
                        self.voice.speak("Сначала мне нужно вас узнать по лицу")
                        self._finish()
                        return

                    success = self.voice.record_voice_training(current_user, sample_count=5)

                    if success:
                        self.voice.speak("Запомнил ваш голос! Теперь я узнаю вас и по голосу")
                    else:
                        self.voice.speak("Ошибка при записи голоса")

                except Exception as e:
                    print(f"[VOICE TRAINING ERROR] {e}")
                    self.voice.speak("Ошибка при обучении голосу")
                finally:
                    self.vision.status = "IDLE"
                    self._finish()

            threading.Thread(target=train_voice, daemon=True).start()
            return

        # =========================
        # CHAT MODE
        # =========================
        self._ask_llm(text)

    # =========================
    # LLM (NON-BLOCKING)
    # =========================
    def _ask_llm(self, user_text):

        # 🔥 UI STATUS
        self.vision.status = "THINKING..."

        # Обновляем имя пользователя в Brain
        current_name = self.vision.session.current_name
        if current_name and current_name != "Unknown":
            self.brain.set_username(current_name)

        self.history.append({
            "role": "user",
            "content": user_text
        })

        def run():

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

                if len(self.history) > 12:
                    self.history = self.history[-12:]

            except Exception as e:
                print(f"[LLM ERROR]: {e}")
                self.voice.speak("Ошибка модели")

            finally:
                self.vision.status = "IDLE"
                self._finish()

        threading.Thread(target=run, daemon=True).start()

    # =========================
    # FINISH
    # =========================
    def _finish(self):

        self.is_busy = False

        # restart listener safely
        try:
            if self.voice.stop_listening_fn:
                self.voice.stop_listening_fn(wait_for_stop=False)

            self.voice.start_background_listener()

        except Exception:
            pass