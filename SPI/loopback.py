import spidev
import time

# Open SPI bus
spi = spidev.SpiDev()
spi.open(0, 0)  # Bus 0, Device 0 (CE0)

# SPI configuration
spi.max_speed_hz = 500000
spi.mode = 0b00  # SPI Mode 0

def loopback_test():
    print("Starting SPI Loopback Test...\n")

    test_data_list = [
        [0xAA],
        [0x55],
        [0xFF],
        [0x00],
        [0x12, 0x34, 0x56],
        [0xDE, 0xAD, 0xBE, 0xEF]
    ]

    for test_data in test_data_list:
        response = spi.xfer2(test_data)

        print(f"Sent     : {test_data}")
        print(f"Received : {response}")

        if response == test_data:
            print("✅ PASS\n")
        else:
            print("❌ FAIL\n")

        time.sleep(0.5)

try:
    loopback_test()

finally:
    spi.close()
    print("SPI Closed")
