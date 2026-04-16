import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 400000  # Start slow
spi.mode = 0

def send_cmd(cmd, arg, crc):
    packet = [
        cmd | 0x40,
        (arg >> 24) & 0xFF,
        (arg >> 16) & 0xFF,
        (arg >> 8) & 0xFF,
        arg & 0xFF,
        crc
    ]
    spi.xfer2(packet)

    # Wait for response
    for _ in range(10):
        resp = spi.xfer2([0xFF])[0]
        if resp != 0xFF:
            return resp
    return -1

def init_sd():
    print("Initializing SD Card...")

    # Send 80 clock cycles
    spi.xfer2([0xFF]*10)

    # CMD0 → reset
    resp = send_cmd(0, 0, 0x95)
    print("CMD0 Response:", resp)

    # CMD8 → check voltage
    resp = send_cmd(8, 0x1AA, 0x87)
    print("CMD8 Response:", resp)

init_sd()
spi.close()
