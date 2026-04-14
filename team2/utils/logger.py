import time

class Logger:
    def __init__(self):
        self.start_time = time.time()

    def log(self, msg):
        print(f"[{time.time() - self.start_time:.3f}s] {msg}")

    def error(self, msg):
        print(f"[ERROR] {msg}")

    def metric(self, name, value):
        print(f"[METRIC] {name}: {value}")