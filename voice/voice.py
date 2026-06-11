import os
import time
import uuid
import pygame
import edge_tts
import speech_recognition as sr
import asyncio


class NeuroVoice:

    def __init__(self):

        pygame.mixer.init()

        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.2

        os.makedirs("voices", exist_ok=True)

        # 🔥 callback для AI Agent
        self.on_text = None

        # state lock (анти спам)
        self.is_listening = False

    # =====================================================
    # SPEAK (TTS FIXED + SAFE)
    # =====================================================
    def speak(self, text):

        try:
            filename = f"voices/voice_{uuid.uuid4().hex}.mp3"

            async def _run():
                tts = edge_tts.Communicate(
                    text,
                    "ru-RU-SvetlanaNeural"
                )
                await tts.save(filename)

            asyncio.run(_run())

            if not os.path.exists(filename):
                print("[VOICE ERROR] file not created")
                return

            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()

            # pygame.mixer.music.play()

            pygame.mixer.music.stop()
            pygame.mixer.music.unload()

            # 🔥 Windows file lock protection
            for _ in range(10):
                try:
                    os.remove(filename)
                    break
                except:
                    time.sleep(0.1)

        except Exception as e:
            print(f"[VOICE ERROR] {e}")

    # =====================================================
    # BACKGROUND LISTENER (AGENT READY)
    # =====================================================
    def start_background_listener(self):

        if self.is_listening:
            return

        self.is_listening = True

        def callback(recognizer, audio):

            try:
                text = recognizer.recognize_google(
                    audio,
                    language="ru-RU"
                )

                print(f"[VOICE]: {text}")

                if self.on_text:
                    self.on_text(text)

            except sr.UnknownValueError:
                pass

            except Exception as e:
                print(f"[VOICE ERROR] {e}")

        mic = sr.Microphone()

        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source)

        self.recognizer.listen_in_background(mic, callback)

        print("[AI] Voice active")

    # =====================================================
    # SINGLE LISTEN (DEBUG)
    # =====================================================
    def listen_once(self):

        try:
            with sr.Microphone() as source:

                print("[VOICE] Listening...")

                self.recognizer.adjust_for_ambient_noise(source, duration=1)

                audio = self.recognizer.listen(source, timeout=5)

                text = self.recognizer.recognize_google(
                    audio,
                    language="ru-RU"
                )

                print(f"[VOICE] {text}")

                return text

        except Exception:
            return None