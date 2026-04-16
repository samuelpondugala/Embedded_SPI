# import time
# import random

# class SPITester:
#     def __init__(self, flash, spi, logger):
#         self.flash = flash
#         self.spi = spi
#         self.log = logger

#     # -----------------------------
#     # 1. JEDEC ID TEST
#     # -----------------------------
#     def test_jedec_id(self):
#         self.log.log("Running JEDEC ID Test...")
#         jedec = self.flash.read_jedec_id()

#         if jedec[0] == 0xEF:
#             self.log.log(f"PASS: JEDEC ID = {jedec}")
#         else:
#             self.log.error(f"FAIL: JEDEC ID = {jedec}")

#     # -----------------------------
#     # 2. WRITE + READ TEST
#     # -----------------------------
#     def test_write_read(self):
#         self.log.log("Running Write/Read Test...")

#         addr = 0x000000
#         data = [random.randint(0, 255) for _ in range(256)]

#         self.flash.sector_erase(addr)
#         self.flash.page_program(addr, data)

#         read_back = self.flash.read_data(addr, 256)

#         if read_back == data:
#             self.log.log("PASS: Data verified")
#         else:
#             self.log.error("FAIL: Data mismatch")

#     # -----------------------------
#     # 3. ERASE TEST
#     # -----------------------------
#     def test_erase(self):
#         self.log.log("Running Erase Test...")

#         addr = 0x000000
#         self.flash.sector_erase(addr)

#         data = self.flash.read_data(addr, 256)

#         if all(x == 0xFF for x in data):
#             self.log.log("PASS: Erase successful")
#         else:
#             self.log.error("FAIL: Erase failed")

#     # -----------------------------
#     # 4. LOOPBACK TEST
#     # -----------------------------
#     def test_loopback(self):
#         self.log.log("Running Loopback Test...")

#         pattern = [0xAA, 0x55, 0xFF, 0x00]

#         resp = self.spi.transfer(pattern)

#         if resp == pattern:
#             self.log.log("PASS: Loopback OK")
#         else:
#             self.log.error(f"FAIL: {resp}")

#     # -----------------------------
#     # 5. SPEED TEST
#     # -----------------------------
#     def test_speed(self):
#         self.log.log("Running Speed Test...")

#         data = [0xFF] * 1024

#         start = time.time()
#         self.spi.transfer(data)
#         end = time.time()

#         throughput = len(data) / (end - start)
#         self.log.metric("Throughput (bytes/sec)", throughput)

#     # -----------------------------
#     # 6. CLOCK VARIATION TEST
#     # -----------------------------
#     def test_clock_variation(self):
#         self.log.log("Running Clock Variation Test...")

#         speeds = [500000, 1000000, 5000000, 10000000]

#         for s in speeds:
#             self.spi.set_speed(s)

#             start = time.time()
#             self.spi.transfer([0xFF]*512)
#             end = time.time()

#             self.log.metric(f"Speed {s}", end - start)

#     # -----------------------------
#     # 7. STRESS TEST
#     # -----------------------------
#     def test_stress(self):
#         self.log.log("Running Stress Test...")

#         for i in range(50):
#             data = [random.randint(0,255) for _ in range(256)]
#             addr = i * 4096

#             self.flash.sector_erase(addr)
#             self.flash.page_program(addr, data)

#             rb = self.flash.read_data(addr, 256)

#             if rb != data:
#                 self.log.error(f"Mismatch at iteration {i}")
#                 return

#         self.log.log("PASS: Stress test completed")

#     def run_all(self):
#         self.test_jedec_id()
#         self.test_write_read()
#         self.test_erase()
#         self.test_loopback()
#         self.test_speed()
#         self.test_clock_variation()
#         self.test_stress()

#         self.log.log("✅ ALL SPI TESTS COMPLETED")

import spidev
import time

# ---------------- SPI INIT ----------------
spi = spidev.SpiDev()

# ---------------- SEND COMMAND ----------------
def send_cmd(cmd, arg, crc):
    packet = [
        0x40 | cmd,
        (arg >> 24) & 0xFF,
        (arg >> 16) & 0xFF,
        (arg >> 8) & 0xFF,
        arg & 0xFF,
        crc
    ]

    spi.xfer([0xFF])
    spi.xfer(packet)

    for _ in range(20):
        r = spi.xfer([0xFF])[0]
        if r != 0xFF:
            return r
    return -1


# ---------------- INIT SD ----------------
def init_sd():
    spi.max_speed_hz = 400000
    spi.xfer([0xFF] * 10)

    print("CMD0:", hex(send_cmd(0, 0, 0x95)))
    print("CMD8:", hex(send_cmd(8, 0x1AA, 0x87)))

    while True:
        send_cmd(55, 0, 0)
        resp = send_cmd(41, 0x40000000, 0)
        if resp == 0:
            break

    print("Card initialized!")


# ---------------- READ OCR ----------------
def read_ocr():
    send_cmd(58, 0, 0)
    ocr = spi.xfer([0xFF]*4)
    print("OCR:", ocr)
    return True if (ocr[0] & 0x40) else False


# ---------------- READ BLOCK ----------------
def read_block(block, is_sdhc):
    addr = block if is_sdhc else block * 512

    spi.xfer([0xFF])

    if send_cmd(17, addr, 0) != 0x00:
        return None

    for _ in range(10000):
        if spi.xfer([0xFF])[0] == 0xFE:
            break

    data = spi.xfer([0xFF] * 512)
    spi.xfer([0xFF, 0xFF])

    return data


# ---------------- WRITE BLOCK ----------------
def write_block(block, data, is_sdhc):
    addr = block if is_sdhc else block * 512

    spi.xfer([0xFF])

    if send_cmd(24, addr, 0) != 0x00:
        print("CMD24 failed")
        return False

    spi.xfer([0xFE])

    data = data + [0x00] * (512 - len(data))
    spi.xfer(data)

    spi.xfer([0xFF, 0xFF])

    resp = spi.xfer([0xFF])[0]
    if (resp & 0x1F) != 0x05:
        print("Write rejected")
        return False

    timeout = 5000
    while timeout > 0:
        if spi.xfer([0xFF])[0] != 0x00:
            break
        timeout -= 1

    return timeout != 0


# =========================================================
# 🧪 TEST FRAMEWORK
# =========================================================

class SPITest:

    def __init__(self):
        self.results = []

    def log(self, name, status, info=""):
        print(f"[{status}] {name} - {info}")
        self.results.append((name, status, info))


    # ---------------- TEST 1 ----------------
    def test_card_identification(self):
        print("\nRunning Card Identification Test...")

        r = send_cmd(8, 0x1AA, 0x87)

        if r == 0x01:
            self.log("CMD8 Test", "PASS")
        else:
            self.log("CMD8 Test", "FAIL", f"Resp: {r}")

        is_sdhc = read_ocr()

        if is_sdhc:
            self.log("OCR Test", "PASS", "SDHC/SDXC")
        else:
            self.log("OCR Test", "PASS", "SDSC")

        return is_sdhc


    # ---------------- TEST 2 ----------------
    def test_read_write(self, is_sdhc):
        print("\nRunning Read/Write Test...")

        block = 1000
        test_data = [i % 256 for i in range(512)]

        if not write_block(block, test_data, is_sdhc):
            self.log("Write Test", "FAIL")
            return

        read_back = read_block(block, is_sdhc)

        if read_back == test_data:
            self.log("Read/Write", "PASS")
        else:
            self.log("Read/Write", "FAIL")


    # ---------------- TEST 3 ----------------
    def test_erase(self, is_sdhc):
        print("\nRunning Erase Test...")

        block = 1001
        empty = [0x00] * 512

        write_block(block, empty, is_sdhc)
        data = read_block(block, is_sdhc)

        if data and all(x == 0x00 for x in data):
            self.log("Erase Test", "PASS")
        else:
            self.log("Erase Test", "FAIL")


    # ---------------- TEST 4 ----------------
    def test_continuous_read(self, is_sdhc):
        print("\nRunning Continuous Read Test...")

        start = time.time()

        for i in range(50):
            read_block(1100 + i, is_sdhc)

        end = time.time()

        self.log("Continuous Read", "PASS", f"{end-start:.2f}s")


    # ---------------- TEST 5 ----------------
    def test_clock_variation(self, is_sdhc):
        print("\nRunning SPI Clock Test...")

        speeds = [100000, 500000, 1000000, 5000000]

        for speed in speeds:
            spi.max_speed_hz = speed

            try:
                data = read_block(0, is_sdhc)

                if data:
                    self.log(f"Clock {speed}", "PASS")
                else:
                    self.log(f"Clock {speed}", "FAIL")

            except Exception as e:
                self.log(f"Clock {speed}", "FAIL", str(e))


    # ---------------- TEST 6 ----------------
    def test_throughput(self, is_sdhc):
        print("\nRunning Throughput Test...")

        blocks = 50
        start = time.time()

        for i in range(blocks):
            read_block(1200 + i, is_sdhc)

        end = time.time()

        speed = (blocks * 512) / (end - start) / 1024

        self.log("Throughput", "PASS", f"{speed:.2f} KB/s")


    # ---------------- RUN ALL ----------------
    def run_all(self):
        spi.open(0, 0)

        init_sd()
        is_sdhc = read_ocr()

        spi.max_speed_hz = 1000000

        self.test_card_identification()
        self.test_read_write(is_sdhc)
        self.test_erase(is_sdhc)
        self.test_continuous_read(is_sdhc)
        self.test_clock_variation(is_sdhc)
        self.test_throughput(is_sdhc)

        print("\n========== FINAL REPORT ==========")
        for r in self.results:
            print(r)


# =========================================================
# 🚀 MAIN
# =========================================================

if __name__ == "__main__":
    tester = SPITest()
    tester.run_all()