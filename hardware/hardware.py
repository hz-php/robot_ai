# D:\my_projects\robot_ai\hardware\hardware.py

from hardware.serial_manager import SerialManager
from hardware.ultrasonic import Ultrasonic


class Hardware:
    # [ИЗМЕНЕНО] Теперь класс умеет принимать порт и скорость при создании
    def __init__(self, port="COM3", baudrate=115200):
        
        # Передаем полученные порт и скорость внутрь SerialManager
        self.serial = SerialManager(port=port, baudrate=baudrate)

        self.ultrasonic = Ultrasonic(
            self.serial
        )

    def distance(self):

        return self.ultrasonic.get_distance()