import os
import json
import numpy as np
import librosa
import soundfile as sf
from scipy.spatial.distance import euclidean
from datetime import datetime


class VoiceRecognizer:
    """
    Voice Recognition Engine
    - Запоминание голоса пользователя
    - Распознавание говорящего
    - Speaker verification
    """

    def __init__(self, db_path="voices/voice_models"):

        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)

        self.voice_profiles = self._load_profiles()

        # MFCC параметры
        self.n_mfcc = 13
        self.hop_length = 512

    # =========================
    # LOAD/SAVE PROFILES
    # =========================
    def _load_profiles(self):
        """Загрузка профилей голосов из JSON"""

        profiles_file = os.path.join(self.db_path, "profiles.json")

        if os.path.exists(profiles_file):
            with open(profiles_file, "r") as f:
                return json.load(f)

        return {}

    def _save_profiles(self):
        """Сохранение профилей голосов"""

        profiles_file = os.path.join(self.db_path, "profiles.json")

        with open(profiles_file, "w") as f:
            json.dump(self.voice_profiles, f, indent=2)

    # =========================
    # RECORD SAMPLE
    # =========================
    def record_voice_sample(self, audio_data, user_id):
        """
        Сохранение аудио образца пользователя

        Args:
            audio_data: numpy array аудио
            user_id: ID пользователя
        """

        user_dir = os.path.join(self.db_path, f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)

        # Сохранение wav файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(user_dir, f"sample_{timestamp}.wav")

        # Assuming audio_data is at 16000 Hz
        sf.write(filename, audio_data, 16000)

        print(f"[VOICE SAMPLE] Saved: {filename}")

        return filename

    # =========================
    # EXTRACT FEATURES (MFCC)
    # =========================
    def extract_features(self, audio_data, sr=16000):
        """
        Извлечение MFCC коэффициентов
        """

        try:
            # Извлечение MFCC
            mfcc = librosa.feature.mfcc(
                y=audio_data,
                sr=sr,
                n_mfcc=self.n_mfcc,
                hop_length=self.hop_length
            )

            # Усреднение по времени для получения вектора признаков
            mfcc_mean = np.mean(mfcc, axis=1)
            mfcc_std = np.std(mfcc, axis=1)

            # Объединение mean и std
            features = np.concatenate([mfcc_mean, mfcc_std])

            return features

        except Exception as e:
            print(f"[FEATURE EXTRACTION ERROR] {e}")
            return None

    # =========================
    # TRAIN SPEAKER
    # =========================
    def train_speaker(self, user_id):
        """
        Обучение модели голоса пользователя
        """

        user_dir = os.path.join(self.db_path, f"user_{user_id}")

        if not os.path.exists(user_dir):
            print(f"[VOICE TRAIN ERROR] No samples for user {user_id}")
            return False

        samples = []
        all_features = []

        # Загрузка всех образцов
        for filename in os.listdir(user_dir):

            if not filename.endswith(".wav"):
                continue

            filepath = os.path.join(user_dir, filename)

            try:
                audio_data, sr = librosa.load(filepath, sr=16000, mono=True)

                if len(audio_data) < sr:  # минимум 1 секунда
                    continue

                features = self.extract_features(audio_data, sr)

                if features is not None:
                    all_features.append(features)
                    samples.append(filename)

            except Exception as e:
                print(f"[VOICE TRAIN ERROR] {filepath}: {e}")

        if len(all_features) < 2:
            print(f"[VOICE TRAIN ERROR] Недостаточно образцов для {user_id}")
            return False

        # Вычисление среднего профиля голоса
        voice_profile = np.mean(all_features, axis=0)
        voice_std = np.std(all_features, axis=0)

        # Сохранение профиля
        profile_data = {
            "user_id": user_id,
            "profile": voice_profile.tolist(),
            "std": voice_std.tolist(),
            "samples": len(all_features),
            "created_at": datetime.now().isoformat()
        }

        self.voice_profiles[str(user_id)] = profile_data

        self._save_profiles()

        print(f"[VOICE TRAIN] ✅ Trained speaker {user_id} on {len(all_features)} samples")

        return True

    # =========================
    # RECOGNIZE SPEAKER
    # =========================
    def recognize_speaker(self, audio_data, sr=16000, threshold=15.0):
        """
        Распознавание говорящего по голосу

        Args:
            audio_data: numpy array аудио
            sr: sample rate
            threshold: порог для идентификации (меньше = строже)

        Returns:
            (user_id, confidence) или (None, 0)
        """

        features = self.extract_features(audio_data, sr)

        if features is None:
            return None, 0

        best_match = None
        best_distance = float('inf')

        # Сравнение с каждым профилем
        for user_id_str, profile in self.voice_profiles.items():

            user_id = int(user_id_str)
            profile_features = np.array(profile["profile"])

            # Euclidean distance
            distance = euclidean(features, profile_features)

            print(f"[VOICE MATCH] User {user_id}: distance={distance:.2f}")

            if distance < best_distance:
                best_distance = distance
                best_match = user_id

        # Проверка порога
        if best_distance < threshold:
            confidence = 1.0 - (best_distance / threshold)
            print(f"[VOICE RECOGNIZED] User {best_match}, confidence={confidence:.2f}")
            return best_match, confidence

        else:
            print(f"[VOICE UNKNOWN] Distance {best_distance:.2f} > threshold {threshold}")
            return None, 0

    # =========================
    # DELETE PROFILE
    # =========================
    def delete_profile(self, user_id):
        """Удаление профиля голоса пользователя"""

        user_id_str = str(user_id)

        if user_id_str in self.voice_profiles:
            del self.voice_profiles[user_id_str]
            self._save_profiles()
            print(f"[VOICE] Deleted profile for user {user_id}")

        return True
