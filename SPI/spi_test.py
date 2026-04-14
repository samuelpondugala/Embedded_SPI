import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 500000
spi.mode = 0

time.sleep(1)

print("Sending JEDEC...")

resp = spi.xfer2([0x9F, 0x00, 0x00, 0x00])

print("Response:", resp)