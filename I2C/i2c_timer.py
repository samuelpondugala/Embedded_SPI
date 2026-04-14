import sys
import time
import signal
import tm1637

# Setup Display
tm = tm1637.TM1637(clk=5, dio=4)
tm.brightness(3)

def cleanup(signum, frame):
    tm.write([0, 0, 0, 0]) # Clear display
    print("Timer Stopped.")
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)

try:
    time_str = sys.argv[1] # Expected "05:00"
    minutes, seconds = map(int, time_str.split(':'))
    total_seconds = minutes * 60 + seconds
    
    print(f"Countdown Started: {time_str}")
    
    while total_seconds >= 0:
        m, s = divmod(total_seconds, 60)
        # Show digits and colon in one command to prevent flicker
        tm.numbers(m, s, colon=True)
        time.sleep(1)
        total_seconds -= 1
        
    # Finished Animation
    print("Timer Finished!")
    for _ in range(3):
        tm.numbers(0, 0, colon=False)
        time.sleep(0.3)
        tm.write([0,0,0,0]) # Blank
        time.sleep(0.3)

except ValueError:
    print("Error: Invalid time format. Use MM:SS")
except Exception as e:
    print(f"Error: {e}")
