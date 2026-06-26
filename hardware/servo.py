from hardware.serial_manager import SerialManager


class Servo:

    def __init__(self, serial: SerialManager):
        self.serial = serial

    def angle(self, angle: int):

        angle = max(0, min(180, int(angle)))

        self.serial.send(f"SERVO:{angle}")

    def left(self):
        self.angle(180)

    def right(self):
        self.angle(0)

    def center(self):
        self.angle(90)