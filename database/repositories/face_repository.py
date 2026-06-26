"""
Репозиторий для работы с профилями лиц.
"""

from database.models import FaceProfile


class FaceRepository:
    """
    Repository для управления FaceProfile.
    
    Предоставляет операции для привязки пользователей к меткам LBPH.
    """

    def __init__(self, db):
        self.db = db

    def get_by_label(self, label):
        """
        Получить профиль по метке лица.
        
        Args:
            label: Метка для LBPH распознавателя
            
        Returns:
            FaceProfile или None
        """
        return (
            self.db.query(FaceProfile)
            .filter(
                FaceProfile.face_label == label
            )
            .first()
        )

    def create(self, user_id, face_label):
        """
        Создать профиль лица.
        
        Args:
            user_id: ID пользователя
            face_label: Метка для LBPH
            
        Returns:
            Созданный FaceProfile
        """
        profile = FaceProfile(
            user_id=user_id,
            face_label=face_label
        )

        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)

        return profile