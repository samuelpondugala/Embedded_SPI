import serial
import time
import subprocess

# ---------------- CONFIG ----------------
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200

# ---------------- CALCULATOR ----------------
def add(a, b): return a + b
def subtract(a, b): return a - b
def multiply(a, b): return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b

def calculate(a, b, op):
    ops = {
        "1": add,
        "2": subtract,
        "3": multiply,
        "4": divide
    }
    if op not in ops:
        raise ValueError("Invalid operation")
    return ops[op](a, b)

# ---------------- UART SEND ----------------
def uart_send(ser, msg):
    ser.write((msg + "\n").encode('utf-8'))

# ---------------- MENU ----------------
def show_menu():
    print("""
===== MAIN MENU =====
1. Calculator
2. Run Pytest
3. Chat Mode
4. Exit
=====================
""")
def clear_uart_buffer(ser):
    """Clear all pending UART data"""
    while ser.in_waiting > 0:
        ser.readline()

# ---------------- CALCULATOR MODE ----------------
def calculator_mode(ser):
    clear_uart_buffer(ser)
    try:
        a = float(input("Enter first number: "))
        b = float(input("Enter second number: "))

        print("""
Select Operation:
1. Add
2. Subtract
3. Multiply
4. Divide
""")

        op = input("Enter choice: ")

        result = calculate(a, b, op)

        print(f"Result: {result}")
        uart_send(ser, f"CALC RESULT: {result}")

    except Exception as e:
        print(f"Error: {e}")
        uart_send(ser, f"CALC ERROR: {str(e)}")

# ---------------- PYTEST MODE ----------------
def pytest_mode(ser):
    clear_uart_buffer(ser)
    print("Running pytest...\n")
    uart_send(ser, "Running pytest...")

    try:
        process = subprocess.Popen(
            ["pytest", "-v", "test_calculator.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            line = line.strip()
            print(line)
            uart_send(ser, line)

        process.wait()

        uart_send(ser, f"Pytest completed (code {process.returncode})")

    except Exception as e:
        print(f"Error: {e}")
        uart_send(ser, f"PYTEST ERROR: {str(e)}")

# ---------------- CHAT MODE ----------------
def chat_mode(ser):
    print("\nEntering Chat Mode (type 'exit' to return)\n")

    clear_uart_buffer(ser)   # 🔥 VERY IMPORTANT

    while True:
        msg = input("You: ")

        if msg.lower() == "exit":
            print("Exiting chat mode...\n")
            uart_send(ser, "EXIT CHAT MODE")
            clear_uart_buffer(ser)
            break

        # Send message
        uart_send(ser, msg)

        time.sleep(0.1)

        # 🔥 Read ONLY latest response (drain old ones)
        latest = None

        while ser.in_waiting > 0:
            latest = ser.readline().decode().strip()

        if latest:
            print(f"Device Echoed: {latest}")
        else:
            print("No response (check loopback)")


# ---------------- MAIN ----------------
def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE}")
        print("USB UART App Started\n")

        ser.flushInput()
        ser.flushOutput()

        while True:
            show_menu()
            choice = input("Enter choice: ")

            if choice == "1":
                calculator_mode(ser)

            elif choice == "2":
                pytest_mode(ser)

            elif choice == "3":
                chat_mode(ser)

            elif choice == "4":
                print("Exiting program...")
                uart_send(ser, "PROGRAM EXIT")
                break

            else:
                print("Invalid option\n")

    except serial.SerialException as e:
        print(f"Serial Error: {e}")
        print(f"Try: sudo chmod 666 {SERIAL_PORT}")

    except KeyboardInterrupt:
        print("\nInterrupted by user")

    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed.")

# ---------------- RUN ----------------
if __name__ == "__main__":
    
    main()