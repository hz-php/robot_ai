"""
Будущее управление Arduino / ESP32
"""

from ai.permissions import PermissionService


class RobotController:

    def execute_command(
        self,
        user,
        command
    ):
        """
        Проверяем права
        """

        if not PermissionService.can_drive_robot(
            user.role
        ):
            return False

        print(
            f"[Robot]: {user.name} -> {command}"
        )

        return True