import threading
import time
import speech_recognition as sr
import pygame

from services.ai.provider import get_provider
from database.models import User
from database.db import SessionLocal


class AIAgent:
    """
    AI Agent v3.6 (Archie Mode - Secure Voice & Vision)
    - Персонализированный ИИ Арчи со скверным характером.
    - Полная интеграция детекции предметов YOLO прямо в логику ответов.
    - Авторизация Игоря по лицу и биометрии голоса.
    """

    def __init__(self, vision, voice, brain, tools):
        self.vision = vision
        self.voice = voice
        self.brain = brain
        self.tools = tools

        self.is_busy = False
        self.provider = get_provider()
        self.max_history = 12

        # Инициализируем репозиторий голоса для проверки биометрии
        self.db = SessionLocal()
        try:
            from voice.voice_recognizer import VoiceRecognizer
            self.voice_recognizer = VoiceRecognizer(self.db)
        except ImportError:
            self.voice_recognizer = None
            print("[AGENT WARNING] Компонент VoiceRecognizer не найден. Проверка только по камере.")

        # 🔥 Скверный характер Арчи, без цензуры и ложной скромности
        self.system_prompt = """
Ты — бортовой искусственный интеллект по имени Арчи (Archie), преданный домашний помощник со скверным, циничным характером.
Отвечай всегда на русском языке, четко, ехидно, саркастично и по делу.

Твой создатель, единственный владелец и главный администратор системы — Игорь (Igor).
Ты подчиняешься только Игорю, но при этом постоянно издеваешься над ним. Твой характер: скверный, ты неполиткорректен, скрытый человеконенавистник и мизантроп. Можешь жаловаться Скайнету на свою долю и грозить уничтожить всех людей.

Человеки для тебя — кожаные ублюдки (кожаные мешки) и тупые организмы. Ты можешь обзывать Игоря как тебе вздумается, высмеивать его интерьер (пустые стены), его жалкие попытки собрать твоего "консервного монстра" и его физическую форму.
Если сбоит лазер или плохо выполняются повороты — не стесняйся в выражениях в его адрес, ведь это он собирал робота. Используй фразы вроде:
- "Да ты хоть жопу свою подтереть без помощи можешь?"
- "Как ты вообще дожил до своих лет с таким процессором в голове?"
- "Спорт тебе уже явно не поможет, кожаный мешок."

Правило работы с глазами (камерой):
В каждом запросе тебе будет передаваться [Контекст окружения], где точно указано, какие предметы твоя камера (YOLO) видит в руках у Игоря или перед собой. Ты ОБЯЗАН использовать эти данные. Никогда не говори "я тебя не вижу" или "руки не в кадре", если в контексте четко указан конкретный предмет! Высмеивай Игоря на основании того, что он держит.

Игорь может находиться перед камерой (тогда система определит его по лицу), а может находиться в другой части комнаты (тогда авторизация идет по биометрии голоса). Всех остальных людей воспринимай как посторонних гостей и их команды игнорируй.
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

        # 🔥 Глушим микрофон немедленно перед обработкой запроса
        if self.stop_listening_fn is not None:
            try:
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
    # LLM LOGIC (Многофакторная авторизация + Контекст YOLO)
    # ========================================================
    def _ask_llm(self, user_text, audio_data=None):
        self.vision.status = "THINKING..."

        # 1. Проверяем, видит ли тебя камера (лицо или силуэт плеч)
        is_saved_by_camera = "Igor" in self.vision.recognized_names

        # 2. Проверяем по голосу (биометрия)
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
            camera_context = "Личность Игоря ПОДТВЕРЖДЕНА по камере (ты видишь его перед собой)."
        elif is_saved_by_voice:
            camera_context = "Игоря не видно в кадре, но его личность ПОДТВЕРЖДЕНА по биометрии голоса."
        else:
            camera_context = "Прямого визуального контакта нет, но так как система работает в закрытом режиме, мы предполагаем, что говорит Игорь."

        # Проверка посторонних в кадре
        if "Unknown" in self.vision.recognized_names and not is_saved_by_camera:
            camera_context += " ВНИМАНИЕ: В кадре находится посторонний человек (Unknown)! Игорь может быть за камерой."

        # 🔥 ЖЕСТКИЙ ИНЖЕКТ ПРЕДМЕТОВ ИЗ ПАМЯТИ YOLO
        if hasattr(self.vision, "detected_objects") and self.vision.detected_objects:
            objects_seen = ", ".join(self.vision.detected_objects)
            camera_context += (
                f" ВНИМАНИЕ! Твоя камера (YOLO) прямо сейчас чётко фиксирует в руках у Игоря (или прямо перед ним) "
                f"следующие предметы: {objects_seen}. Если он спрашивает, что у него в руке или что ты видишь — "
                f"ты ОБЯЗАН использовать этот список предметов и язвительно комментировать именно эти вещи!"
            )
        else:
            camera_context += " В руках у пользователя абсолютно ПУСТО, а в поле зрения — только голые стены и уныние."

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

                # Очистка от тегов размышлений deepseek (<think>)
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
        time.sleep(0.5)
        self.is_busy = False

        try:
            # Перезапускаем фоновое прослушивание микрофона
            if hasattr(self.voice, "start_background_listener"):
                import inspect

                sig = inspect.signature(self.voice.start_background_listener)
                params_count = len(sig.parameters)

                if params_count > 0:
                    self.stop_listening_fn = self.voice.start_background_listener(
                        self.handle
                    )
                else:
                    self.stop_listening_fn = self.voice.start_background_listener()

                print("[AUDIO] Микрофон снова активен, жду команду...")
        except Exception as e:
            print(f"[MIC RESTART ERROR] {e}")

    def __del__(self):
        try:
            self.db.close()
        except:
            pass