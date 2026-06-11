from database.repositories.user_repository import UserRepository


class PermissionService:

    def __init__(self, db):
        self.user_repo = UserRepository(db)

    def can_control_robot(self, user_id):

        user = self.user_repo.get_by_id(user_id)

        if not user:
            return False

        return user.role in [
            "admin",
            "operator"
        ]

    def is_admin(self, user_id):

        user = self.user_repo.get_by_id(user_id)

        if not user:
            return False

        return user.role == "admin"