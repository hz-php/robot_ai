"""
Система ролей
"""


class Roles:
    ADMIN = "ADMIN"

    OPERATOR = "OPERATOR"

    GUEST = "GUEST"


class PermissionService:

    @staticmethod
    def can_add_user(role):

        return role == Roles.ADMIN

    @staticmethod
    def can_drive_robot(role):

        return role in [
            Roles.ADMIN,
            Roles.OPERATOR
        ]