# hardware/hardware.py

from hardware.serial_manager import SerialManager
from hardware.ultrasonic import Ultrasonic
from hardware.servo import Servo


class Hardware:

    def __init__(self, port="COM3", baudrate=115200):

        self.serial = SerialManager(
            port=port,
            baudrate=baudrate
        )

        self.ultrasonic = Ultrasonic(
            self.serial
        )

        self.servo = Servo(
            self.serial
        )

    def distance(self):
        return self.ultrasonic.get_distance()