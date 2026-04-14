import os
import mmap
import random
import struct
import time

class SRAMTester:
    def __init__(self, size=1024, use_dev_mem=False, base_addr=0x0):
        self.size = size
        self.use_dev_mem = use_dev_mem
        self.base_addr = base_addr

        if use_dev_mem:
            self.fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
            self.mem = mmap.mmap(self.fd, size, mmap.MAP_SHARED,
                                 mmap.PROT_READ | mmap.PROT_WRITE,
                                 offset=base_addr)
        else:
            self.mem = bytearray(size)

    def write_byte(self, addr, value):
        if isinstance(self.mem, mmap.mmap):
            self.mem[addr] = value
        else:
            self.mem[addr] = value

    def read_byte(self, addr):
        return self.mem[addr]

    def log_error(self, addr, expected, actual):
        print(f"[ERROR] Addr: {addr:#06x} Expected: {expected:#04x} Got: {actual:#04x}")

    # -----------------------------
    # 1. Walking 1s Test
    # -----------------------------
    def test_walking_ones(self):
        print("Running Walking 1s Test...")
        for bit in range(8):
            pattern = 1 << bit
            for addr in range(self.size):
                self.write_byte(addr, pattern)

            for addr in range(self.size):
                val = self.read_byte(addr)
                if val != pattern:
                    self.log_error(addr, pattern, val)

        print("Walking 1s Test Completed\n")

    # -----------------------------
    # 2. Walking 0s Test
    # -----------------------------
    def test_walking_zeros(self):
        print("Running Walking 0s Test...")
        for bit in range(8):
            pattern = ~(1 << bit) & 0xFF
            for addr in range(self.size):
                self.write_byte(addr, pattern)

            for addr in range(self.size):
                val = self.read_byte(addr)
                if val != pattern:
                    self.log_error(addr, pattern, val)

        print("Walking 0s Test Completed\n")

    # -----------------------------
    # 3. Checkerboard Test
    # -----------------------------
    def test_checkerboard(self):
        print("Running Checkerboard Test...")
        patterns = [0xAA, 0x55]

        for pattern in patterns:
            for addr in range(self.size):
                self.write_byte(addr, pattern)

            for addr in range(self.size):
                val = self.read_byte(addr)
                if val != pattern:
                    self.log_error(addr, pattern, val)

        print("Checkerboard Test Completed\n")

    # -----------------------------
    # 4. Address Test
    # -----------------------------
    def test_address(self):
        print("Running Address Test...")

        for addr in range(self.size):
            self.write_byte(addr, addr & 0xFF)

        for addr in range(self.size):
            expected = addr & 0xFF
            val = self.read_byte(addr)
            if val != expected:
                self.log_error(addr, expected, val)

        print("Address Test Completed\n")

    # -----------------------------
    # 5. Random Pattern Test
    # -----------------------------
    def test_random(self):
        print("Running Random Pattern Test...")

        pattern = [random.randint(0, 255) for _ in range(self.size)]

        for addr in range(self.size):
            self.write_byte(addr, pattern[addr])

        for addr in range(self.size):
            val = self.read_byte(addr)
            if val != pattern[addr]:
                self.log_error(addr, pattern[addr], val)

        print("Random Pattern Test Completed\n")

    # -----------------------------
    # 6. March Test (Basic)
    # -----------------------------
    def test_march(self):
        print("Running March Test...")

        # Write 0
        for addr in range(self.size):
            self.write_byte(addr, 0x00)

        # Read 0, Write 1
        for addr in range(self.size):
            if self.read_byte(addr) != 0x00:
                self.log_error(addr, 0x00, self.read_byte(addr))
            self.write_byte(addr, 0xFF)

        # Read 1
        for addr in reversed(range(self.size)):
            if self.read_byte(addr) != 0xFF:
                self.log_error(addr, 0xFF, self.read_byte(addr))

        print("March Test Completed\n")

    def run_all_tests(self):
        self.test_walking_ones()
        self.test_walking_zeros()
        self.test_checkerboard()
        self.test_address()
        self.test_random()
        self.test_march()

        print("✅ ALL TESTS COMPLETED")


if __name__ == "__main__":
    tester = SRAMTester(size=1024, use_dev_mem=False)
    tester.run_all_tests()