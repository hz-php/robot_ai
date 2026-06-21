import time
import serial

# Открываем порт COM7 напрямую на скорости 115200 (как в ESP32)
ser = serial.Serial("COM7", 115200, timeout=1)
time.sleep(2) # Ждем перезагрузку ESP32

print("Отправляем команды напрямую в порт...")

try:
    while True:
        print("Отправляю: SERVO:45")
        ser.write(b"SERVO:45\n") # \n в конце ОБЯЗАТЕЛЕН, так как ESP32 ждет строки
        time.sleep(2)

        print("Отправляю: SERVO:90")
        ser.write(b"SERVO:90\n")
        time.sleep(2)

        print("Отправляю: SERVO:135")
        ser.write(b"SERVO:135\n")
        time.sleep(2)

except KeyboardInterrupt:
    ser.close()
    print("Тест завершен.")