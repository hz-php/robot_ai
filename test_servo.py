import time

from hardware.hardware import Hardware

hw = Hardware(port="COM7")

time.sleep(2)

while True:

    hw.servo.left()
    print("LEFT")
    time.sleep(2)

    hw.servo.center()
    print("CENTER")
    time.sleep(2)

    hw.servo.right()
    print("RIGHT")
    time.sleep(2)