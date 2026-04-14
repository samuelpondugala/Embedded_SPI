import serial
import time
import sys
import RPi.GPIO as GPIO
import signal

# Set up GPIO
LED_A = 17
LED_B = 26
LED_C = 23



GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_A, GPIO.OUT)
GPIO.setup(LED_B, GPIO.OUT)
GPIO.setup(LED_C, GPIO.OUT)

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
                if msg.lower() == "a on":
                    GPIO.output(LED_A, GPIO.HIGH)
                    reply = "led A is on!"
                elif msg.lower() == "a off":
                    GPIO.output(LED_A, GPIO.LOW)
                    reply = "led A is off!"
                elif msg.lower() == "b on":
                    GPIO.output(LED_B, GPIO.HIGH)
                    reply = "led B is on!"
                elif msg.lower() == "b off":
                    GPIO.output(LED_B, GPIO.LOW)
                    reply = "led B is off!"
                elif msg.lower() == "c on":
                    GPIO.output(LED_C, GPIO.HIGH)
                    reply = "led C is on!"
                elif msg.lower() == "c off":
                    GPIO.output(LED_C, GPIO.LOW)
                    reply = "led C is off!"

                elif msg.lower() == 'blink':
                    print("Blinking all LEDs...")
                    while True:
                        GPIO.output(LED_A, GPIO.HIGH)
                        GPIO.output(LED_B, GPIO.HIGH)
                        GPIO.output(LED_C, GPIO.HIGH)
                        time.sleep(1)
                        GPIO.output(LED_A, GPIO.LOW)
                        GPIO.output(LED_B, GPIO.LOW)
                        GPIO.output(LED_C, GPIO.LOW)
                        time.sleep(1)
                elif msg.lower() == 'stop':
                    print("Stopping blink...")
                    GPIO.output(LED_A, GPIO.LOW)
                    GPIO.output(LED_B, GPIO.LOW)
                    GPIO.output(LED_C, GPIO.LOW)

                elif msg.lower() == "hi":
                    reply = "Hello from Pi!"
                elif msg.lower() == "Hello":
                    reply = "Konnichiwa!"
                elif msg.lower() == "how are you?":
                    reply = "I'm Okay, thanks for asking!, How are you??"
                elif msg.lower() == "exit":
                    reply = "Goodbye!"
                else:
                    reply = f"Echo: {msg}"

                ser.write((reply + "\n").encode())


    except KeyboardInterrupt:
        GPIO.cleanup()   # 🔥 VERY IMPORTANT
        print("GPIO Cleaned up")
        print("\nExiting...")


    except Exception as e:
        print(f"Error: {e}")
    

    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()