import serial

ser = serial.Serial("COM7",115200)

while True:
    print(ser.readline().decode().strip())