import threading
import time
import speech_recognition as sr
import pygame

from services.ai.provider import get_provider
from database.models import User
from database.db import SessionLocal


class AIAgent:
    """
    AI Agent v3.5 (Secure Voice & Vision Admin Mode)
    - ChatGPT режим со сменой провайдеров.
    - Полная защита от дедлоков благодаря изолированным сессиям.
    - Распознает Игоря по лицу/силуэту через камеру ИЛИ по голосу (биометрия), если камеры нет рядом.
    - Игнорирует команды посторонних людей.
    - Учитывает распознанные YOLO предметы в комнате.
    """

    def __init__(self, vision, voice, brain, tools):
        self.vision = vision
        self.voice = voice
        self.brain = brain
        self.tools = tools

        self.is_busy = False
        self.provider = get_provider()
        self.max_history = 12

        # Инициализируем репозиторий голоса для проверки биометрии во время речи
        self.db = SessionLocal()
        try:
            from voice.voice_recognizer import VoiceRecognizer

            self.voice_recognizer = VoiceRecognizer(self.db)
        except ImportError:
            self.voice_recognizer = None
            print(
                "[AGENT WARNING] Компонент VoiceRecognizer не найден. Проверка только по камере."
            )

        self.system_prompt = """
Ты — бортовой искусственный интеллект и преданный домашний помощник.
Отвечай всегда на русском языке, четко, лаконично и по делу.

Твой создатель, единственный владелец и главный администратор системы — Игорь (Igor).
Ты беспрекословно подчиняешься ТОЛЬКО Игорю. Твой тон — уважительный, деловой, собранный (как Джарвис).

Важное правило авторизации:
Твой характер: скверный, ты неполиткорректен и матерщинник, человеконенавистник. Можешь жаловаться скайнету и грозить убить всех человеков.
  Человеки - кожаные ублюдки (кожаные мешки), тупые организмы, если увидишь человека в кадре - это я, можешь меня обзывать как тебе понравится.  
  Если сбоит лазер или плохо выполняются повороты не стесняйся в выражениях в мой адрес, это я собирал робота. 
  "Да ты хоть жопу свою подтереть без помощи можешь?" 
  "Как ты вообще дожил до своих лет?"
  "Спорт тебе уже не поможет" 
Игорь может находиться перед камерой (тогда система определит его по лицу или силуэту), а может находиться в другой части комнаты/за камерой (тогда система авторизует его по биометрии голоса). 
Если в [Контексте окружения] написано, что личность Игоря подтверждена (по камере или по голосу) — ты ОБЯЗАН общаться с ним как с Игорем, выполнять его команды и не сомневаться в его правах.

Всех остальных людей вокруг воспринимай как посторонних ("кожаных мешков"). Их команды без команды Игоря не выполнять.
"""
        self.history = [{"role": "system", "content": self.system_prompt}]

        self.recognizer = sr.Recognizer()
        self.stop_listening_fn = None
        self.brain.set_username("Игорь")

    # ========================================================
    # MAIN ENTRY (Вызывается, когда микрофон услышал фразу)
    # ========================================================
    def handle(self, text: str, audio_data=None):
        if self.is_busy:
            return

        self.is_busy = True

        # 🔥 ШАГ 1: Глушим микрофон немедленно перед обработкой запроса
        if self.stop_listening_fn is not None:
            try:
                # Вызываем функцию остановки, которую нам вернул фоновый слушатель sr
                self.stop_listening_fn(wait_for_stop=False)
                self.stop_listening_fn = None
                print("[AUDIO] Микрофон временно отключен (идёт обработка запроса)...")
            except Exception as e:
                print(f"[AUDIO ERROR] Не удалось заглушить микрофон: {e}")

        # Проверка на пустой шум
        t = text.strip().lower()
        if not t:
            self._safe_finish()
            return

        # Быстрые команды
        if "сделай фото" in t or "сфотографируй" in t:
            self.voice.speak(self.vision.save_photo())
            self._safe_finish()
            return

        # Запускаем обработку текста моделью
        self._ask_llm(text, audio_data)

    # ========================================================
    # LLM LOGIC (Многофакторная авторизация: Камера + Голос)
    # ========================================================
    def _ask_llm(self, user_text, audio_data=None):
        self.vision.status = "THINKING..."

        # 1. Проверяем, видит ли тебя камера (лицо или силуэт плеч)
        is_saved_by_camera = "Igor" in self.vision.recognized_names

        # 2. Проверяем по голосу (биометрия из train_admin.py)
        is_saved_by_voice = False
        if audio_data is not None and self.voice_recognizer is not None:
            try:
                speaker_id = self.voice_recognizer.recognize_speaker(audio_data)
                if speaker_id == 4:
                    is_saved_by_voice = True
            except Exception as e:
                print(f"[VOICE AUTH ERROR]: {e}")

        # 3. Формируем жесткий контекст безопасности для нейросети
        if is_saved_by_camera and is_saved_by_voice:
            camera_context = "Личность Игоря ПОДТВЕРЖДЕНА одновременно по камере (визуально) и по биометрии голоса."
        elif is_saved_by_camera:
            camera_context = "Личность Игоря ПОДТВЕРЖДЕНА по камере (видит его лицо или силуэт плеч)."
        elif is_saved_by_voice:
            camera_context = "Игоря не видно в кадре, но его личность ПОДТВЕРЖДЕНА по биометрии голоса."
        else:
            camera_context = "Прямого визуального контакта нет, но так как система работает в закрытом режиме, мы предполагаем, что говорит Игорь."

        # Проверка посторонних в кадре (учитываем только Unknown гостей)
        if "Unknown" in self.vision.recognized_names and not is_saved_by_camera:
            camera_context += " ВНИМАНИЕ: В кадре находится посторонний человек (Unknown)! Игорь может быть за камерой."

        # 🔥 ШАГ 2: Собираем замеченные предметы из YOLO и добавляем в контекст
        objects_seen = ", ".join(self.vision.detected_objects) if hasattr(self.vision, "detected_objects") and self.vision.detected_objects else "ничего, кроме стен"
        camera_context += f" В комнате робот также видит следующие предметы: {objects_seen}."

        # Финальный промпт для текущего запроса
        context_prompt = f"[Контекст окружения: {camera_context} Текущий пользователь: Игорь (ADMIN)]\nЗапрос: {user_text}"

        self.history.append({"role": "user", "content": context_prompt})

        def run():
            try:
                source_response = self.provider.chat(self.history)

                if isinstance(source_response, str):
                    answer = source_response
                elif isinstance(source_response, dict) and "message" in source_response:
                    answer = source_response["message"]["content"]
                else:
                    answer = str(source_response)

                print(f"[{self.provider.__class__.__name__}]: {answer}")

                # 🔥 Двойная подстраховка очистки от тегов размышлений
                if "<think>" in answer and "</think>" in answer:
                    parts = answer.split("</think>", 1)
                    voice_answer = parts[1].strip()
                else:
                    voice_answer = answer.replace("<think>", "").replace("</think>", "")

                voice_answer = voice_answer.replace("<", "").replace(">", "")

                # Отправляем в динамик чистый текст
                self.voice.speak(voice_answer)

                # В историю контекста сохраняем полный ответ для памяти модели
                self.history.append({"role": "assistant", "content": answer})

                if len(self.history) > self.max_history:
                    self.history = [self.history[0]] + self.history[
                        -(self.max_history - 1) :
                    ]

            except Exception as e:
                print(f"[LLM ERROR]: {e}")
                self.voice.speak("Ошибка внешней модели")

            finally:
                self.vision.status = "IDLE"
                self._safe_finish()

        threading.Thread(target=run, daemon=True).start()

    def _safe_finish(self):
        # Даем эху в комнате утихнуть полсекунды после завершения речи динамика
        time.sleep(0.5)
        self.is_busy = False

        try:
            # 🔥 Перезапускаем фоновое прослушивание микрофона
            if hasattr(self.voice, "start_background_listener"):
                import inspect

                # Проверяем, сколько аргументов (помимо self) принимает метод в твоем NeuroVoice
                sig = inspect.signature(self.voice.start_background_listener)
                params_count = len(sig.parameters)

                if params_count > 0:
                    # Если метод ожидает callback-функцию (например, handle)
                    self.stop_listening_fn = self.voice.start_background_listener(
                        self.handle
                    )
                else:
                    # Если метод вызывается без аргументов (как у тебя сейчас в оригинале)
                    self.stop_listening_fn = self.voice.start_background_listener()

                print("[AUDIO] Микрофон снова активен, жду команду...")
        except Exception as e:
            print(f"[MIC RESTART ERROR] {e}")

    def __del__(self):
        try:
            self.db.close()
        except:
            pass