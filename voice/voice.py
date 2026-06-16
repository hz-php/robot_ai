import os
import time
import uuid
import edge_tts
import speech_recognition as sr
import asyncio
import numpy as np
import subprocess
import platform

# Try to import pygame for audio playback
PYGAME_AVAILABLE = False
pygame = None
try:
    import pygame
    PYGAME_AVAILABLE = True
    print("[AUDIO] pygame available for audio playback")
except ImportError:
    print("[WARNING] pygame not available - using system audio playback")


class NeuroVoice:

    def __init__(self, db=None, voice_repo=None):

        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                print("[AUDIO] pygame mixer initialized")
            except Exception as e:
                print(f"[AUDIO WARNING] Could not initialize pygame mixer: {e}")
        else:
            print("[AUDIO] Using system audio playback (pygame not available)")

        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.2

        os.makedirs("voices", exist_ok=True)

        self.on_text = None
        self.is_listening = False
        self.is_speaking = False

        self.db = db
        self.voice_repo = voice_repo

    def _play_with_system(self, filename):
        """Fallback-воспроизведение через системные утилиты"""
        try:
            if platform.system() == "Windows":
                os.startfile(filename)
                file_size = os.path.getsize(filename)
                estimated_duration = (file_size / (128 * 1024)) * 8
                time.sleep(max(1, min(estimated_duration, 10)))
            elif platform.system() == "Darwin":
                subprocess.run(["afplay", filename], check=False)
            else:
                subprocess.run(["mpg123", filename], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[AUDIO ERROR] System playback failed: {e}")

    def speak(self, text):
        try:
            self.is_speaking = True
            filename = f"voices/voice_{uuid.uuid4().hex}.mp3"

            async def _run():
                tts = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
                await tts.save(filename)

            asyncio.run(_run())

            if not os.path.exists(filename):
                return

            if PYGAME_AVAILABLE and pygame is not None:
                try:
                    pygame.mixer.music.load(filename)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    pygame.mixer.music.unload()
                except Exception as e:
                    print(f"[AUDIO WARNING] pygame failed: {e}")
                    self._play_with_system(filename)
            else:
                self._play_with_system(filename)

            for _ in range(10):
                try:
                    os.remove(filename)
                    break
                except:
                    time.sleep(0.1)
        except Exception as e:
            print(f"[VOICE ERROR] {e}")
        finally:
            self.is_speaking = False

    def start_background_listener(self):
        if self.is_listening:
            return
        self.is_listening = True

        def callback(recognizer, audio):
            if self.is_speaking:
                return

            try:
                # Напрямую распознаем текст без биометрических проверок голоса
                text = recognizer.recognize_google(audio, language="ru-RU")
                print(f"[VOICE]: {text}")

                if self.is_speaking:
                    return

                if self.on_text:
                    self.on_text(text)
            except sr.UnknownValueError:
                pass
            except Exception as e:
                print(f"[VOICE ERROR] {e}")

        mic = sr.Microphone()
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source)

        self.stop_listening_fn = self.recognizer.listen_in_background(mic, callback)
        print("[AUDIO] Voice active")

    def listen_once(self):
        try:
            with sr.Microphone() as source:
                print("[VOICE] Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self.recognizer.listen(source, timeout=5)
                text = self.recognizer.recognize_google(audio, language="ru-RU")
                print(f"[VOICE] {text}")
                return text
        except Exception:
            return None

    def listen_once_with_timeout(self, timeout=10, phrase_time_limit=4):
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                text = self.recognizer.recognize_google(audio, language="ru-RU")
                return text
        except Exception:
            return None