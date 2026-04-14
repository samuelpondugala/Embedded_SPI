import spidev
import time

class SPICore:
    def __init__(self, bus=0, device=0, speed=1000000):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = speed

    def set_speed(self, speed):
        self.spi.max_speed_hz = speed

    def transfer(self, data):
        return self.spi.xfer(data)

    def close(self):
        self.spi.close()