import serial
import time
import sys
import RPi.GPIO as GPIO

# ---------------- CONFIG ----------------
SERIAL_PORT = '/dev/ttyUSB1'
BAUD_RATE = 115200

# ---------------- GPIO SETUP (ONLY ONCE) ----------------
GPIO.setwarnings(False)  # Optional: disable warnings
GPIO.setmode(GPIO.BCM)

LED_A = 17
LED_B = 26
LED_C = 14

GPIO.setup(LED_A, GPIO.OUT)
GPIO.setup(LED_B, GPIO.OUT)
GPIO.setup(LED_C, GPIO.OUT)

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

    print(f"Successfully opened {SERIAL_PORT}")
    print("UART Chat + GPIO Control Started\n")

    ser.flushInput()
    ser.flushOutput()

    while True:
        user_input = input("You: ")

        if not user_input:
            continue

        ser.write((user_input + '\n').encode())

        time.sleep(0.1)

        if ser.in_waiting > 0:
            received = ser.readline().decode().strip()

            # ---------------- LED CONTROL ----------------
            if received == "A on":
                GPIO.output(LED_A, GPIO.HIGH)
                print("LED1 ON")

            elif received == "A off":
                GPIO.output(LED_A, GPIO.LOW)
                print("LED1 OFF")

            elif received == "B on":
                GPIO.output(LED_B, GPIO.HIGH)
                print("LED2 ON")

            elif received == "B off":
                GPIO.output(LED_B, GPIO.LOW)
                print("LED2 OFF")

            elif received == "C on":
                GPIO.output(LED_C, GPIO.HIGH)
                print("LED3 ON")

            elif received == "C off":
                GPIO.output(LED_C, GPIO.LOW)
                print("LED3 OFF")
            
            elif received == 'all on':
                GPIO.output(LED_A, GPIO.HIGH)
                GPIO.output(LED_B, GPIO.HIGH)
                GPIO.output(LED_C, GPIO.HIGH)
                print("ALL LEDs ON")

            elif received == 'all off':
                GPIO.output(LED_A, GPIO.LOW)
                GPIO.output(LED_B, GPIO.LOW)
                GPIO.output(LED_C, GPIO.LOW)
                print("ALL LEDs OFF")
            
            elif received == 'blink':
                print("Blinking all LEDs...")
                while True:
                    GPIO.output(LED_A, GPIO.HIGH)
                    GPIO.output(LED_B, GPIO.HIGH)
                    GPIO.output(LED_C, GPIO.HIGH)
                    time.sleep(0.5)
                    GPIO.output(LED_A, GPIO.LOW)
                    GPIO.output(LED_B, GPIO.LOW)
                    GPIO.output(LED_C, GPIO.LOW)
                    time.sleep(0.5)
            elif received == 'stop':
                print("Stopping blink...")
                GPIO.output(LED_A, GPIO.LOW)
                GPIO.output(LED_B, GPIO.LOW)
                GPIO.output(LED_C, GPIO.LOW)


            else:
                print(f"Echo: {received}")

        else:
            print("No data received")

# ---------------- CLEAN EXIT ----------------
except serial.SerialException as e:
    print(f"Serial Error: {e}")

except KeyboardInterrupt:
    GPIO.cleanup()   # 🔥 VERY IMPORTANT
    print("GPIO Cleaned up")
    print("\nExiting...")

finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()

    GPIO.cleanup()   # 🔥 VERY IMPORTANT
    print("GPIO Cleaned up")