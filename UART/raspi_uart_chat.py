import serial
import time
import sys
import RPi.GPIO as GPIO
import signal


# --- Configuration ---
# Update this to match your system's serial port.
# Common examples:
# Linux/Raspberry Pi: '/dev/ttyS0', '/dev/ttyAMA0', or '/dev/ttyUSB0'
# Windows: 'COM3', 'COM4'
SERIAL_PORT = '/dev/serial0'   # Pi UART
BAUD_RATE = 115200

def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print("Raspberry Pi UART Chat Ready...")

        while True:
            if ser.in_waiting > 0:
                msg = ser.readline().decode().strip()

                print(f"Laptop: {msg}")

                # 🔥 Smart reply logic (you can customize)
                if msg.lower() == "hi":
                    reply = "Hello from Pi!"
                elif msg.lower() == "Hello":
                    reply = "Konnichiwa!"
                elif msg.lower() == "how are you?":
                    reply = "I'm Okay, thanks for asking!, How are you??"
                elif msg.lower() == "time":
                    reply = time.strftime("%H:%M:%S")
                elif msg.lower() == "exit":
                    reply = "Goodbye!"
                else:
                    reply = f"Echo: {msg}"

                ser.write((reply + "\n").encode())

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()