import os
import time
from utils import generate_data, checksum

class SDTester:

    def __init__(self, mount_point, file_size_mb=10, block_size=4096):
        self.mount = mount_point
        self.file_path = os.path.join(mount_point, "sd_test.bin")
        self.size_mb = file_size_mb
        self.block_size = block_size

    def write_test(self):
        print("\n[WRITE TEST]")
        total_bytes = self.size_mb * 1024 * 1024
        written = 0

        start = time.time()

        with open(self.file_path, "wb") as f:
            while written < total_bytes:
                chunk = generate_data(min(self.block_size, total_bytes - written))
                f.write(chunk)
                written += len(chunk)

        os.sync()
        speed = self.size_mb / (time.time() - start)
        print(f"Write Speed: {speed:.2f} MB/s")

        return speed

    def read_test(self):
        print("\n[READ TEST]")
        start = time.time()

        with open(self.file_path, "rb") as f:
            while f.read(self.block_size):
                pass

        size_mb = os.path.getsize(self.file_path) / (1024 * 1024)
        speed = size_mb / (time.time() - start)

        print(f"Read Speed: {speed:.2f} MB/s")
        return speed

    def integrity_test(self):
        print("\n[INTEGRITY TEST]")

        with open(self.file_path, "rb") as f:
            data1 = f.read()

        hash1 = checksum(data1)

        with open(self.file_path, "rb") as f:
            data2 = f.read()

        hash2 = checksum(data2)

        if hash1 == hash2:
            print("Integrity: PASS")
            return True
        else:
            print("Integrity: FAIL")
            return False

    def cleanup(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
            print("\n[Cleanup Done]")
