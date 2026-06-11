from database.models import VoiceProfile


class VoiceProfileRepository:
    """
    Repository для управления голосовыми профилями пользователей
    """

    def __init__(self, db):
        self.db = db

    def get_by_user_id(self, user_id):
        """Получить профиль голоса по ID пользователя"""

        return (
            self.db.query(VoiceProfile)
            .filter(VoiceProfile.user_id == user_id)
            .first()
        )

    def get_all_profiles(self):
        """Получить все профили голоса"""

        return (
            self.db.query(VoiceProfile)
            .all()
        )

    def create(self, user_id, profile_features, profile_std, samples_count):
        """Создать новый профиль голоса"""

        # Преобразуем numpy array в список если нужно
        if hasattr(profile_features, 'tolist'):
            profile_features = profile_features.tolist()
        if hasattr(profile_std, 'tolist'):
            profile_std = profile_std.tolist()

        profile = VoiceProfile(
            user_id=user_id,
            profile_features=profile_features,
            profile_std=profile_std,
            samples_count=samples_count
        )

        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)

        return profile

    def update(self, user_id, profile_features, profile_std, samples_count):
        """Обновить профиль голоса"""

        # Преобразуем numpy array в список если нужно
        if hasattr(profile_features, 'tolist'):
            profile_features = profile_features.tolist()
        if hasattr(profile_std, 'tolist'):
            profile_std = profile_std.tolist()

        profile = self.get_by_user_id(user_id)

        if not profile:
            return self.create(user_id, profile_features, profile_std, samples_count)

        profile.profile_features = profile_features
        profile.profile_std = profile_std
        profile.samples_count = samples_count

        self.db.commit()
        self.db.refresh(profile)

        return profile

    def delete(self, user_id):
        """Удалить профиль голоса"""

        profile = self.get_by_user_id(user_id)

        if profile:
            self.db.delete(profile)
            self.db.commit()
            return True

        return False
