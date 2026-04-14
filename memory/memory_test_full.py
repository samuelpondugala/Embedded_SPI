import os
import mmap
import time
import json
import serial

# --- SETUP UART TRANSMITTER ---
# /dev/serial0 is the default hardware serial port on Pi
try:
    uart = serial.Serial('/dev/serial0', 115200, timeout=1)
except Exception as e:
    print(f"Failed to open UART: {e}")
    exit(1)

def send_data(payload):
    """Encodes JSON and sends it directly out the UART TX pin."""
    try:
        # Add a newline character so the laptop knows when the message ends
        message = json.dumps(payload) + "\n"
        uart.write(message.encode('utf-8'))
        uart.flush() # Force it out the wire immediately
    except Exception as e:
        pass # Ignore write errors to keep tests running

class ProgressTracker:
    def __init__(self, total, operation="WRITE"):
        self.total = total
        self.operation = operation
        self.start_time = time.time()
        self.last_print = 0

    def update(self, current):
        now = time.time()
        if now - self.last_print > 0.99 or current == self.total:
            elapsed = now - self.start_time
            speed = current / elapsed if elapsed > 0 else 0
            
            send_data({
                "event": "progress",
                "operation": self.operation,
                "current": current,
                "total": self.total,
                "speed": speed
            })
            self.last_print = now

class SRAMTester:
    def __init__(self, size=1024 * 1024, use_dev_mem=False, base_addr=0x0):
        self.size = size
        self.errors_found = 0
        send_data({"event": "info", "msg": f"Initializing {size} bytes..."})

        if use_dev_mem:
            self.fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
            self.mem = mmap.mmap(self.fd, size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=base_addr)
        else:
            self.mem = bytearray(size)

    def write_byte(self, addr, value): self.mem[addr] = value
    def read_byte(self, addr): return self.mem[addr]

    def fill_memory(self, pattern, label):
        tracker = ProgressTracker(self.size, label)
        for addr in range(self.size):
            self.write_byte(addr, pattern)
            if addr % 4096 == 0: tracker.update(addr)
        tracker.update(self.size)

    def verify_memory(self, pattern, label):
        tracker = ProgressTracker(self.size, label)
        for addr in range(self.size):
            val = self.read_byte(addr)
            if val != pattern:
                self.errors_found += 1
                send_data({"event": "error", "addr": addr, "expected": pattern, "actual": val})
            if addr % 4096 == 0: tracker.update(addr)
        tracker.update(self.size)

    def test_checkerboard(self):
        send_data({"event": "start_test", "name": "Checkerboard Test"})
        for pattern in [0xAA, 0x55]:
            self.fill_memory(pattern, f"WRITE {pattern:#04x}")
            self.verify_memory(pattern, f"READ {pattern:#04x}")

    def run_all_tests(self):
        start_time = time.time()
        self.test_checkerboard()
        
        total_time = time.time() - start_time
        send_data({"event": "done", "errors": self.errors_found, "time": total_time})

if __name__ == "__main__":
    tester = SRAMTester(size=10 * 1024 * 1024, use_dev_mem=False)
    tester.run_all_tests()