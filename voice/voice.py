"""
Голосовой интерфейс NeuroVoice.

Предоставляет функции синтеза речи (TTS) и распознавания речи (STT).
"""

import os
import time
import uuid
import edge_tts
import speech_recognition as sr
import asyncio
import subprocess
import platform

# Попытка импорта pygame для воспроизведения аудио
PYGAME_AVAILABLE = False
pygame = None
try:
    import pygame
    PYGAME_AVAILABLE = True
    print("[AUDIO] pygame available for audio playback")
except ImportError:
    print("[WARNING] pygame not available - using system audio playback")


class NeuroVoice:
    """
    Голосовой интерфейс для робота.
    
    Обеспечивает распознавание речи (Google STT) и синтез речи (Edge TTS).
    """

    def __init__(self, db=None, voice_repo=None):
        """
        Инициализация голосового модуля.
        
        Args:
            db: Сессия БД (опционально)
            voice_repo: Репозиторий голосовых профилей (опционально)
        """
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                print("[AUDIO] pygame mixer initialized")
            except Exception as e:
                print(f"[AUDIO WARNING] Could not initialize pygame mixer: {e}")

        self.recognizer = sr.Recognizer()
        # 🔥 КРИТИЧЕСКИ ВАЖНО: Адаптация к шуму окружающей среды
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 1000  # Настрой под свой микрофон
        self.recognizer.pause_threshold = 1.0

        os.makedirs("voices", exist_ok=True)
        self.on_text = None      # Callback для полученного текста
        self.is_listening = False
        self.is_speaking = False

    def speak(self, text):
        """
        Синтез и воспроизведение речи.
        
        Args:
            text: Текст для озвучивания
        """
        try:
            self.is_speaking = True  # Блокируем микрофон во время речи
            
            # Генерируем уникальное имя файла
            filename = f"voices/voice_{uuid.uuid4().hex}.mp3"

            # Асинхронно сохраняем речь через Edge TTS
            async def _run():
                tts = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
                await tts.save(filename)

            asyncio.run(_run())

            if not os.path.exists(filename):
                return

            # Воспроизводим через pygame
            if PYGAME_AVAILABLE and pygame is not None:
                try:
                    pygame.mixer.music.load(filename)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    pygame.mixer.music.unload()
                except Exception as e:
                    print(f"[AUDIO WARNING] pygame failed: {e}")
            
            # 🔥 ПАУЗА ПОСЛЕ РЕЧИ, чтобы эхо утихло
            time.sleep(0.5) 
            
            # Удаляем временный файл
            if os.path.exists(filename):
                os.remove(filename)

        except Exception as e:
            print(f"[VOICE ERROR] {e}")
        finally:
            self.is_speaking = False  # Разблокируем микрофон

    def start_background_listener(self):
        """
        Запуск фонового микрофона для прослушивания речи.
        
        Returns:
            Функция остановки прослушивания
        """
        if self.is_listening:
            return

        self.is_listening = True

        def callback(recognizer, audio):
            # 🔥 ЖЕСТКАЯ БЛОКИРОВКА, если робот сейчас говорит
            if self.is_speaking:
                return

            try:
                text = recognizer.recognize_google(audio, language="ru-RU")
                # 🔥 Игнорируем короткие случайные шумы (меньше 2 слов)
                if len(text.split()) < 2:
                    return
                
                print(f"[VOICE]: {text}")
                if self.on_text:
                    self.on_text(text)
            except sr.UnknownValueError:
                pass  # Шум не распознан
            except Exception as e:
                print(f"[VOICE ERROR] {e}")

        mic = sr.Microphone()
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

        self.stop_listening_fn = self.recognizer.listen_in_background(mic, callback)
        print("[AUDIO] Voice active")