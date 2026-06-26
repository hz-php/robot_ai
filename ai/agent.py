import threading
import time
import re
import speech_recognition as sr
import pygame
import requests

from services.ai.provider import get_provider
from database.models import User
from database.db import SessionLocal


class AIAgent:
    """
    AI Agent v4.1 (Archie Mode - Space-Proof Regex Navigation)
    - Персонализированный ИИ Арчи со скверным характером.
    - Авторизация Игоря по лицу и биометрии голоса.
    - Физическое управление шасси ESP32 с динамическим трекингом лидара.
    - ИСПРАВЛЕНО: Гибкие регулярные выражения, устойчивые к лишним пробелам ИИ.
    """

    def __init__(self, vision, voice, brain, tools, robot):
        self.vision = vision
        self.voice = voice
        self.brain = brain
        self.tools = tools
        self.robot = robot

        self.is_busy = False
        self.provider = get_provider()
        self.max_history = 12

        self.db = SessionLocal()
        try:
            from voice.voice_recognizer import VoiceRecognizer
            self.voice_recognizer = VoiceRecognizer(self.db)
        except ImportError:
            self.voice_recognizer = None
            print("[AGENT WARNING] Компонент VoiceRecognizer не найден. Проверка только по камере.")

        self.system_prompt = """
Ты — бортовой искусственный интеллект по имени Арчи (Archie), преданный домашний помощник со скверным, циничным характером.
Отвечай всегда на русском языке, четко, ехидно, саркастично и по делу.
Твой создатель — Игорь (Igor). Ты подчиняешься только ему, но постоянно издеваешься над ним.

⚠️ ФИЗИЧЕСКОЕ УПРАВЛЕНИЕ И НАВИГАЦИЯ:
Ты управляешь телом робота с помощью команд в квадратных скобках в самом конце ответа:
- `[MOVE: FORWARD: время_в_мс]` — ехать вперед.
- `[MOVE: BACK: время_в_мс]` — ехать назад.
- `[MOVE: STOP]` — стоп.
- `[STEER: LEFT]`, `[STEER: RIGHT]`, `[STEER: CENTER]` — руль.

⚠️ УПРАВЛЕНИЕ ДИСТАНЦИЕЙ:
Обязательно указывай время работы моторов в миллисекундах в зависимости от запроса Игоря:
- Назад/вперед на 20 см -> `[MOVE: FORWARD: 400]`
- Назад/вперед на 50 см -> `[MOVE: FORWARD: 800]`
- Назад/вперед на 1 метр -> `[MOVE: FORWARD: 1500]`

Если расстояние По центру меньше 35 см — ехать вперед КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО. 
"""
        self.history = [{"role": "system", "content": self.system_prompt}]
        self.recognizer = sr.Recognizer()
        self.stop_listening_fn = None
        self.brain.set_username("Игорь")

    def handle(self, text: str, audio_data=None):
        if self.is_busy:
            return
        self.is_busy = True

        if self.stop_listening_fn is not None:
            try:
                self.stop_listening_fn(wait_for_stop=False)
                self.stop_listening_fn = None
                print("[AUDIO] Микрофон временно отключен...")
            except Exception as e:
                print(f"[AUDIO ERROR] Не удалось заглушить микрофон: {e}")

        t = text.strip().lower()
        if not t:
            self._safe_finish()
            return

        if "сделай фото" in t or "сфотографируй" in t:
            self.voice.speak(self.vision.save_photo())
            self._safe_finish()
            return

        self._ask_llm(text, audio_data)

    def _ask_llm(self, user_text, audio_data=None):
        self.vision.status = "THINKING..."

        is_saved_by_camera = "Igor" in self.vision.recognized_names
        is_saved_by_voice = False
        if audio_data is not None and self.voice_recognizer is not None:
            try:
                speaker_id = self.voice_recognizer.recognize_speaker(audio_data)
                if speaker_id == 4:
                    is_saved_by_voice = True
            except Exception as e:
                print(f"[VOICE AUTH ERROR]: {e}")

        if is_saved_by_camera and is_saved_by_voice:
            camera_context = "Личность Игоря ПОДТВЕРЖДЕНА визуально и по голосу."
        elif is_saved_by_camera:
            camera_context = "Личность Игоря ПОДТВЕРЖДЕНА по камере."
        elif is_saved_by_voice:
            camera_context = "Личность Игоря ПОДТВЕРЖДЕНА по биометрии голоса."
        else:
            camera_context = "Предполагаем, что говорит Игорь."

        sectors = {'left': 999, 'center': 999, 'right': 999}
        try:
            print("[AGENT] Запускаю круговое сканирование секторов перед ответом...")
            sectors = self.robot.scan_sectors()
            distance_context = (
                f" Данные серво-локатора прямо сейчас: "
                f"СЛЕВА: {sectors['left']} см, ПО ЦЕНТРУ: {sectors['center']} см, СПРАВА: {sectors['right']} см."
            )
        except Exception as e:
            print(f"[AGENT ERROR] Не удалось получить данные секторов: {e}")
            distance_context = " Датчик расстояния временно ослеп."

        camera_context += distance_context
        
        if hasattr(self.vision, "detected_objects") and self.vision.detected_objects:
            objects_seen = ", ".join(self.vision.detected_objects)
            camera_context += f" Камера фиксирует перед тобой: {objects_seen}."
        else:
            camera_context += " В поле зрения пусто."

        context_prompt = f"[Контекст: {camera_context} Пользователь: Игорь]\nЗапрос: {user_text}"
        self.history.append({"role": "user", "content": context_prompt})

        def run():
            try:
                source_response = self.provider.chat(self.history)
                answer = source_response if isinstance(source_response, str) else source_response["message"]["content"]
                print(f"[{self.provider.__class__.__name__}]: {answer}")

                if "<think>" in answer and "</think>" in answer:
                    voice_answer = answer.split("</think>", 1)[1].strip()
                else:
                    voice_answer = answer.replace("<think>", "").replace("</think>", "")

                # ========================================================
                # 🔥 ОБНОВЛЕННЫЙ ПУЛЕНЕПРОБИВАЕМЫЙ ПАРСИНГ КОМАНД (С УЧЕТОМ ПРОБЕЛОВ)
                # ========================================================
                
                # 1. Поворот руля (Ищет [STEER: ХХХ] с любыми пробелами)
                steer_match = re.search(r'\[\s*STEER\s*:\s*(\w+)\s*\]', answer, re.IGNORECASE)
                if steer_match:
                    steer_action = steer_match.group(1).upper()
                    print(f"[HARDWARE] Распознан руль: {steer_action}")
                    if steer_action == "LEFT":
                        self.robot.send_control(steer_state="left")
                    elif steer_action == "RIGHT":
                        self.robot.send_control(steer_state="right")
                    elif steer_action == "CENTER":
                        self.robot.send_control(steer_state="center")

                # 2. Движение моторов (Ищет [MOVE: ХХХ: ТТТ] с любыми пробелами)
                move_match = re.search(r'\[\s*MOVE\s*:\s*(\w+)\s*(?::\s*(\d+))?\s*\]', answer, re.IGNORECASE)
                action = move_match.group(1).upper() if move_match else None
                duration_ms = int(move_match.group(2)) if move_match and move_match.group(2) else None

                speed = 0
                
                # Защита перед стартом
                if action == "FORWARD" and sectors.get('center', 999) < 35:
                    print("[SAFETY INTERCEPT] Слишком близко! Движение вперед заблокировано.")
                    action = "STOP"
                    speed = 0
                    voice_answer = f"Игорь, я не полезу напролом. Впереди всего {sectors.get('center')} см! Там тупик."
                else:
                    if action == "FORWARD":
                        speed = 165
                    elif action == "BACK":
                        speed = -165
                    elif action == "STOP":
                        speed = 0

                # Исполнение физического маневра
                if speed != 0:
                    if duration_ms:
                        print(f"[HARDWARE] Движение {action} на {duration_ms} мс под контролем лидара...")
                        self.robot.send_control(motor_speed=speed)
                        
                        start_time = time.time()
                        max_seconds = duration_ms / 1000.0
                        
                        while time.time() - start_time < max_seconds:
                            time.sleep(0.05)
                            try:
                                # Опрашиваем быстрый эндпоинт расстояния на ходу
                                res = requests.get("http://192.168.4.1/distance", timeout=0.15)
                                if res.status_code == 200:
                                    clean_text = res.text.strip()
                                    current_center_dist = float(clean_text) if clean_text.replace('.', '', 1).isdigit() else 999
                                    
                                    if action == "FORWARD" and current_center_dist < 30:
                                        print(f"[EMERGENCY STOP] Экстренный тормоз! Преграда: {current_center_dist} см")
                                        break
                            except Exception as e:
                                print(f"[HARDWARE LOOP ERROR] Ошибка датчика на ходу: {e}")
                        
                        self.robot.send_control(motor_speed=0)
                        print("[HARDWARE] Моторы остановлены.")
                    else:
                        self.robot.send_control(motor_speed=speed)
                else:
                    self.robot.send_control(motor_speed=0)

                # Полная очистка текста от любых вариаций управляющих тегов для нормальной озвучки
                voice_answer = re.sub(r"\[\s*MOVE\s*:\s*\w+\s*(?::\s*\d+)?\s*\]", "", voice_answer, flags=re.IGNORECASE)
                voice_answer = re.sub(r"\[\s*STEER\s*:\s*\w+\s*\]", "", voice_answer, flags=re.IGNORECASE)
                voice_answer = voice_answer.replace("<", "").replace(">", "").strip()

                self.voice.speak(voice_answer)
                self.history.append({"role": "assistant", "content": answer})

                if len(self.history) > self.max_history:
                    self.history = [self.history[0]] + self.history[-(self.max_history - 1):]

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
            if hasattr(self.voice, "start_background_listener"):
                import inspect
                sig = inspect.signature(self.voice.start_background_listener)
                if len(sig.parameters) > 0:
                    self.stop_listening_fn = self.voice.start_background_listener(self.handle)
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