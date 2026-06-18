# D:\my_projects\robot_ai\hardware\ultrasonic.py

class Ultrasonic:
    def __init__(self, serial):
        self.serial = serial
        self.distance = None

    def update(self):
        line = self.serial.last_line
        if line.startswith("DIST:"):
            try:
                # Меняем int на float, чтобы успешно парсить дробные числа
                raw_dist = float(line.replace("DIST:", ""))
                self.distance = round(raw_dist, 1) # Округляем до 1 знака для красоты
            except ValueError:
                pass

    def get_distance(self):
        self.update()
        return self.distance