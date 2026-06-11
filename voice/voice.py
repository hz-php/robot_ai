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

VOICE_RECOGNITION_AVAILABLE = False
VoiceRecognizer = None

try:
    import librosa
    VOICE_RECOGNITION_AVAILABLE = True
except ImportError:
    print("[WARNING] librosa not installed - voice recognition disabled")


class NeuroVoice:

    def __init__(self, db=None, voice_repo=None):

        # Initialize pygame mixer if available
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                print("[AUDIO] pygame mixer initialized")
            except Exception as e:
                print(f"[AUDIO WARNING] Could not initialize pygame mixer: {e}")
                print("[AUDIO] Using system audio playback")
        else:
            print("[AUDIO] Using system audio playback (pygame not available)")

        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.2

        os.makedirs("voices", exist_ok=True)

        # 🔥 callback для AI Agent
        self.on_text = None

        # state lock (анти спам)
        self.is_listening = False

        # Database connection
        self.db = db
        self.voice_repo = voice_repo

        # 🎤 Voice Recognition Engine (lazy load)
        self.voice_recognizer = None

    # =====================================================
    # SYSTEM AUDIO PLAYBACK (fallback)
    # =====================================================
    def _play_with_system(self, filename):
        """Use system commands to play audio file"""
        try:
            if platform.system() == "Windows":
                os.startfile(filename)
                # Give system time to play the file
                import mimetypes
                # Rough estimate: wait for file to play
                file_size = os.path.getsize(filename)
                # Rough estimate: ~128kbps for mp3
                estimated_duration = (file_size / (128 * 1024)) * 8
                time.sleep(max(1, min(estimated_duration, 10)))
            elif platform.system() == "Darwin":
                subprocess.run(["afplay", filename], check=False)
            else:  # Linux
                subprocess.run(["mpg123", filename], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[AUDIO ERROR] System playback failed: {e}")

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

            # Try pygame first if available
            if PYGAME_AVAILABLE and pygame is not None:
                try:
                    pygame.mixer.music.load(filename)
                    pygame.mixer.music.play()

                    # ✅ Wait for playback to finish
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)

                    pygame.mixer.music.unload()
                except Exception as e:
                    print(f"[AUDIO WARNING] pygame playback failed: {e}")
                    print("[AUDIO] Falling back to system playback")
                    self._play_with_system(filename)
            else:
                # Use system playback
                self._play_with_system(filename)

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
                # 🎤 Try to recognize speaker first
                try:
                    user_id, confidence = self.recognize_speaker(audio.get_raw_data())
                    if user_id:
                        print(f"[VOICE AUTH] Recognized user {user_id} (confidence: {confidence:.2f})")
                except Exception as e:
                    print(f"[VOICE RECOGNITION] {e}")

                # 📝 Then recognize speech
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

        self.stop_listening_fn = self.recognizer.listen_in_background(mic, callback)

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

    # =====================================================
    # LISTEN WITH TIMEOUT (FOR NAME INPUT)
    # =====================================================
    def listen_once_with_timeout(self, timeout=5):
        """
        Слушание с заданным таймаутом (для ввода имени)
        """

        try:
            with sr.Microphone() as source:

                print(f"[VOICE] Listening for {timeout}s...")

                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

                audio = self.recognizer.listen(source, timeout=timeout)

                text = self.recognizer.recognize_google(
                    audio,
                    language="ru-RU"
                )

                print(f"[VOICE] Heard: {text}")

                return text

        except sr.UnknownValueError:
            print("[VOICE] Could not understand audio")
            return None
        except sr.RequestError:
            print("[VOICE] API error")
            return None
        except Exception as e:
            print(f"[VOICE ERROR] {e}")
            return None

    # =====================================================
    # RECORD VOICE TRAINING (SPEAKER RECOGNITION)
    # =====================================================
    def record_voice_training(self, user_id, sample_count=5):
        """
        Запись голосовых образцов для обучения

        Args:
            user_id: ID пользователя
            sample_count: количество образцов для записи
        """

        if not VOICE_RECOGNITION_AVAILABLE:
            print("[VOICE ERROR] librosa not installed - voice recognition unavailable")
            return False

        # Lazy load VoiceRecognizer
        if self.voice_recognizer is None:
            from voice.voice_recognizer import VoiceRecognizer
            self.voice_recognizer = VoiceRecognizer(
                db=self.db,
                voice_repo=self.voice_repo
            )

        print(f"[VOICE TRAINING] Starting recording {sample_count} samples...")

        recorded = 0

        for i in range(sample_count):

            try:
                with sr.Microphone() as source:

                    print(f"[VOICE] Recording sample {i+1}/{sample_count}... Speak now!")

                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

                    # Запись 3-5 секунд
                    audio = self.recognizer.listen(source, timeout=5)

                    # Преобразование в numpy array
                    audio_data = np.frombuffer(audio.get_raw_data(), dtype=np.int16).astype(float) / 32768.0

                    # Сохранение образца
                    self.voice_recognizer.record_voice_sample(audio_data, user_id)

                    recorded += 1

                    print(f"[VOICE] Sample {i+1} recorded ✅")

                    time.sleep(0.5)

            except sr.RequestError:
                print(f"[VOICE ERROR] API error on sample {i+1}")
                continue

            except sr.UnknownValueError:
                print(f"[VOICE ERROR] Could not understand audio for sample {i+1}, retrying...")
                continue

            except Exception as e:
                print(f"[VOICE ERROR] {e}")
                continue

        if recorded >= 2:
            print(f"[VOICE TRAINING] Recorded {recorded} samples. Training model...")
            self.voice_recognizer.train_speaker(user_id)
            return True
        else:
            print(f"[VOICE TRAINING ERROR] Only {recorded} samples recorded, need at least 2")
            return False

    # =====================================================
    # RECOGNIZE SPEAKER FROM AUDIO
    # =====================================================
    def recognize_speaker(self, audio_data):
        """
        Распознавание говорящего из аудио

        Args:
            audio_data: raw audio data

        Returns:
            (user_id, confidence) или (None, 0)
        """

        if not VOICE_RECOGNITION_AVAILABLE or self.voice_recognizer is None:
            return None, 0

        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(float) / 32768.0

        user_id, confidence = self.voice_recognizer.recognize_speaker(audio_array, sr=16000)

        return user_id, confidence