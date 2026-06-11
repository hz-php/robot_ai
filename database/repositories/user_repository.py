from database.models import User


class UserRepository:

    def __init__(self, db):
        self.db = db

    def get_by_id(self, user_id):

        return (
            self.db.query(User)
            .filter(User.id == user_id)
            .first()
        )

    def get_by_name(self, name):

        return (
            self.db.query(User)
            .filter(User.name == name)
            .first()
        )

    def get_all(self):

        return (
            self.db.query(User)
            .all()
        )

    def create(
        self,
        name,
        role="GUEST"
    ):

        user = User(
            name=name,
            role=role
        )

        self.db.add(user)

        self.db.commit()

        self.db.refresh(user)

        return user

    def delete(self, user_id):

        user = self.get_by_id(user_id)

        if not user:
            return False

        self.db.delete(user)

        self.db.commit()

        return True