import RPi.GPIO as GPIO
import time
from PIL import Image

class DisplayDriver:
    def __init__(self, spi, dc=24, rst=25):
        self.spi = spi
        self.DC = dc
        self.RST = rst

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.DC, GPIO.OUT)
        GPIO.setup(self.RST, GPIO.OUT)

    def cmd(self, c):
        GPIO.output(self.DC, 0)
        self.spi.write([c])

    def data16(self, d):
        GPIO.output(self.DC, 1)
        self.spi.write([d >> 8, d & 0xFF])

    def reset(self):
        GPIO.output(self.RST, 0)
        time.sleep(0.1)
        GPIO.output(self.RST, 1)
        time.sleep(0.1)

    def init(self):
        self.reset()
        # (keep your init registers here)

    def display_image(self, path):
        img = Image.open(path).convert("RGB")
        img = img.resize((176, 220))

        buffer = []
        for y in range(220):
            for x in range(176):
                r, g, b = img.getpixel((x, y))
                color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                buffer.append(color >> 8)
                buffer.append(color & 0xFF)

        for i in range(0, len(buffer), 4096):
            self.spi.write(buffer[i:i+4096])