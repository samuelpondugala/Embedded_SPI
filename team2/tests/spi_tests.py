import time
import random

class SPITester:
    def __init__(self, flash, spi, logger):
        self.flash = flash
        self.spi = spi
        self.log = logger

    # -----------------------------
    # 1. JEDEC ID TEST
    # -----------------------------
    def test_jedec_id(self):
        self.log.log("Running JEDEC ID Test...")
        jedec = self.flash.read_jedec_id()

        if jedec[0] == 0xEF:
            self.log.log(f"PASS: JEDEC ID = {jedec}")
        else:
            self.log.error(f"FAIL: JEDEC ID = {jedec}")

    # -----------------------------
    # 2. WRITE + READ TEST
    # -----------------------------
    def test_write_read(self):
        self.log.log("Running Write/Read Test...")

        addr = 0x000000
        data = [random.randint(0, 255) for _ in range(256)]

        self.flash.sector_erase(addr)
        self.flash.page_program(addr, data)

        read_back = self.flash.read_data(addr, 256)

        if read_back == data:
            self.log.log("PASS: Data verified")
        else:
            self.log.error("FAIL: Data mismatch")

    # -----------------------------
    # 3. ERASE TEST
    # -----------------------------
    def test_erase(self):
        self.log.log("Running Erase Test...")

        addr = 0x000000
        self.flash.sector_erase(addr)

        data = self.flash.read_data(addr, 256)

        if all(x == 0xFF for x in data):
            self.log.log("PASS: Erase successful")
        else:
            self.log.error("FAIL: Erase failed")

    # -----------------------------
    # 4. LOOPBACK TEST
    # -----------------------------
    def test_loopback(self):
        self.log.log("Running Loopback Test...")

        pattern = [0xAA, 0x55, 0xFF, 0x00]

        resp = self.spi.transfer(pattern)

        if resp == pattern:
            self.log.log("PASS: Loopback OK")
        else:
            self.log.error(f"FAIL: {resp}")

    # -----------------------------
    # 5. SPEED TEST
    # -----------------------------
    def test_speed(self):
        self.log.log("Running Speed Test...")

        data = [0xFF] * 1024

        start = time.time()
        self.spi.transfer(data)
        end = time.time()

        throughput = len(data) / (end - start)
        self.log.metric("Throughput (bytes/sec)", throughput)

    # -----------------------------
    # 6. CLOCK VARIATION TEST
    # -----------------------------
    def test_clock_variation(self):
        self.log.log("Running Clock Variation Test...")

        speeds = [500000, 1000000, 5000000, 10000000]

        for s in speeds:
            self.spi.set_speed(s)

            start = time.time()
            self.spi.transfer([0xFF]*512)
            end = time.time()

            self.log.metric(f"Speed {s}", end - start)

    # -----------------------------
    # 7. STRESS TEST
    # -----------------------------
    def test_stress(self):
        self.log.log("Running Stress Test...")

        for i in range(50):
            data = [random.randint(0,255) for _ in range(256)]
            addr = i * 4096

            self.flash.sector_erase(addr)
            self.flash.page_program(addr, data)

            rb = self.flash.read_data(addr, 256)

            if rb != data:
                self.log.error(f"Mismatch at iteration {i}")
                return

        self.log.log("PASS: Stress test completed")

    def run_all(self):
        self.test_jedec_id()
        self.test_write_read()
        self.test_erase()
        self.test_loopback()
        self.test_speed()
        self.test_clock_variation()
        self.test_stress()

        self.log.log("✅ ALL SPI TESTS COMPLETED")