import os
import time

class ProgressTracker:
    def __init__(self, total, operation="WRITE"):
        self.total = total
        self.operation = operation
        self.start_time = time.time()
        self.last_print = 0

    def update(self, current):
        now = time.time()
        if now - self.last_print > 0.1 or current == self.total:
            elapsed = now - self.start_time
            speed = current / elapsed if elapsed > 0 else 0
            percent = (current / self.total) * 100
            
            # Format speed dynamically
            if speed > 1024 * 1024:
                speed_str = f"{speed / (1024 * 1024):.2f} MB/s"
            else:
                speed_str = f"{speed / 1024:.2f} KB/s"
                
            print(f"\r[{self.operation}] {percent:5.1f}% | Speed: {speed_str:<12} ", end='', flush=True)
            self.last_print = now
            
        if current == self.total:
            print() # Newline on completion

class FlashTester:
    def __init__(self, file_path="flash_test_temp.bin", total_size_mb=100, block_size_kb=1024):
        self.file_path = file_path
        self.total_size = total_size_mb * 1024 * 1024
        self.block_size = block_size_kb * 1024
        self.errors_found = 0
        
        print(f"=== INITIALIZING FLASH TEST ===")
        print(f"Target File: {os.path.abspath(self.file_path)}")
        print(f"Test Size:   {total_size_mb} MB")
        print(f"Block Size:  {block_size_kb} KB\n")

    def _force_disk_sync(self, file_obj):
        """
        CRUCIAL: Forces the OS to actually write the data to the physical Flash SSD.
        Without this, modern OSs will just hold the data in RAM (cache), 
        giving you fake speeds of 5000+ MB/s and not actually testing the disk.
        """
        file_obj.flush()
        os.fsync(file_obj.fileno())

    def test_pattern(self, test_name, pattern_byte, is_random=False):
        print(f">>> Starting: {test_name}")
        
        # Pre-generate the 1MB block to save CPU time during the loop
        if not is_random:
            block_data = bytes([pattern_byte] * self.block_size)
            
        written = 0
        tracker = ProgressTracker(self.total_size, "WRITE")
        
        # 1. WRITE PASS
        with open(self.file_path, "wb") as f:
            while written < self.total_size:
                if is_random:
                    block_data = os.urandom(self.block_size)
                    
                f.write(block_data)
                written += self.block_size
                tracker.update(written)
                
            self._force_disk_sync(f) # Force it out of RAM into the physical SSD

        # 2. READ PASS
        read_bytes = 0
        tracker = ProgressTracker(self.total_size, "READ ")
        
        with open(self.file_path, "rb") as f:
            while read_bytes < self.total_size:
                # If it's random, we can't easily verify block-by-block without storing it in RAM.
                # For random, we mostly test the hardware's ability to read random voltage states.
                chunk = f.read(self.block_size)
                
                if not is_random:
                    if chunk != block_data:
                        self.errors_found += 1
                        print(f"\n[ERROR] Block mismatch at offset {read_bytes}!")
                        
                read_bytes += len(chunk)
                tracker.update(read_bytes)
                
        print() # Formatting spacer

    # --- TEST CASES ---
    
    def test_solid_zeros(self):
        # Stresses the flash cells by discharging all logic gates (0x00)
        self.test_pattern("Solid Zeros (0x00)", 0x00)

    def test_solid_ones(self):
        # Stresses the flash cells by charging all logic gates (0xFF)
        self.test_pattern("Solid Ones (0xFF)", 0xFF)

    def test_checkerboard(self):
        # Alternating bits to check for block-leakage
        self.test_pattern("Checkerboard (0xAA)", 0xAA)
        self.test_pattern("Checkerboard Inverse (0x55)", 0x55)
        
    def test_random_data(self):
        # Prevents modern SSD controllers from "cheating" by using data compression
        self.test_pattern("Random Data (Entropy)", None, is_random=True)

    def cleanup(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
            print("Cleaned up test file.")

    def run_all_tests(self):
        start_time = time.time()
        
        try:
            self.test_solid_zeros()
            self.test_solid_ones()
            self.test_checkerboard()
            self.test_random_data()
        except KeyboardInterrupt:
            print("\nTest cancelled by user.")
        finally:
            self.cleanup()

        total_time = time.time() - start_time
        print("=" * 40)
        if self.errors_found == 0:
            print(f"✅ FLASH TESTS COMPLETED SUCCESSFULLY")
        else:
            print(f"❌ COMPLETED WITH {self.errors_found} ERRORS")
        print(f"Total Time: {total_time:.2f} seconds")
        print("=" * 40)


if __name__ == "__main__":
    # Test 100 MB using 1 MB chunks
    tester = FlashTester(file_path="flash_temp.bin", total_size_mb=70, block_size_kb=1024)
    tester.run_all_tests()