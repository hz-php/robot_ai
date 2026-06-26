import serial
import keyboard
import time

arduino = serial.Serial('COM6', 115200)
time.sleep(2)

print("Управление:")
print("A - влево")
print("D - вправо")
print("S - центр")
print("ESC - выход")

while True:

    if keyboard.is_pressed('a'):
        arduino.write(b'D')
        time.sleep(0.05)

    elif keyboard.is_pressed('d'):
        arduino.write(b'A')
        time.sleep(0.05)

    elif keyboard.is_pressed('s'):
        arduino.write(b'S')
        time.sleep(0.05)

    elif keyboard.is_pressed('esc'):
        break

arduino.close()