import serial
import threading


class SerialManager:

    def __init__(self, port="COM3", baudrate=115200):

        self.serial = serial.Serial(
            port,
            baudrate,
            timeout=1
        )

        self.last_line = ""

        threading.Thread(
            target=self._reader,
            daemon=True
        ).start()

    def _reader(self):

        while True:

            try:
                line = self.serial.readline().decode().strip()

                if line:
                    self.last_line = line
                    #print("[SERIAL]", line)

            except:
                pass

    def send(self, text):

        self.serial.write(
            (text + "\n").encode()
        )