from database.models import FaceProfile


class FaceRepository:

    def __init__(self, db):
        self.db = db

    def get_by_label(self, label):

        return (
            self.db.query(FaceProfile)
            .filter(
                FaceProfile.face_label == label
            )
            .first()
        )

    def create(
        self,
        user_id,
        face_label
    ):

        profile = FaceProfile(
            user_id=user_id,
            face_label=face_label
        )

        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)

        return profile