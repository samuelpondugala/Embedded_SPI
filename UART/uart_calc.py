import serial
import time
import subprocess
import sys

# ---------------- CONFIG ----------------
SERIAL_PORT = '/dev/serial0'   # change if needed
BAUD_RATE = 115200

# ---------------- CALCULATOR LOGIC ----------------
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b

def calculate(a, b, operation):
    operations = {
        "1": add,
        "2": subtract,
        "3": multiply,
        "4": divide,
    }

    if operation not in operations:
        raise ValueError("Invalid operation")

    return operations[operation](a, b)

# ---------------- UART HELPERS ----------------
def uart_send(ser, message):
    ser.write((message + "\n").encode('utf-8'))

def uart_receive(ser):
    if ser.in_waiting > 0:
        return ser.readline().decode('utf-8').strip()
    return None

# ---------------- MENU ----------------
def show_menu(ser):
    menu = """
===== UART MENU =====
1. Calculator
2. Run Pytest
3. Chat Mode (Loopback)
4. Exit
=====================
Choose option:
"""
    uart_send(ser, menu)

# ---------------- CALCULATOR MODE ----------------
def calculator_mode(ser):
    uart_send(ser, "Enter first number:")
    while not ser.in_waiting:
        pass
    a = float(ser.readline().decode().strip())

    uart_send(ser, "Enter second number:")
    while not ser.in_waiting:
        pass
    b = float(ser.readline().decode().strip())

    uart_send(ser, """
Choose Operation:
1. Add
2. Subtract
3. Multiply
4. Divide
""")

    while not ser.in_waiting:
        pass
    op = ser.readline().decode().strip()

    try:
        result = calculate(a, b, op)
        uart_send(ser, f"Result: {result}")
    except Exception as e:
        uart_send(ser, f"Error: {str(e)}")

# ---------------- PYTEST MODE ----------------
def run_pytest_mode(ser):
    uart_send(ser, "Running pytest...\n")

    try:
        process = subprocess.Popen(
            ["pytest", "-v"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Stream output line-by-line to UART
        for line in process.stdout:
            uart_send(ser, line.strip())

        process.wait()

        uart_send(ser, f"\nPytest Finished with code {process.returncode}")

    except Exception as e:
        uart_send(ser, f"Error running pytest: {str(e)}")

# ---------------- CHAT MODE ----------------
def chat_mode(ser):
    uart_send(ser, "Entering Chat Mode (type 'exit' to return)\n")

    while True:
        if ser.in_waiting:
            msg = ser.readline().decode().strip()

            if msg.lower() == "exit":
                uart_send(ser, "Exiting Chat Mode...")
                break

            uart_send(ser, f"Echo: {msg}")

# ---------------- MAIN LOOP ----------------
def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print("UART App Started...")

        ser.flushInput()
        ser.flushOutput()

        while True:
            show_menu(ser)

            # Wait for user input
            while not ser.in_waiting:
                pass

            choice = ser.readline().decode().strip()

            if choice == "1":
                calculator_mode(ser)

            elif choice == "2":
                run_pytest_mode(ser)

            elif choice == "3":
                chat_mode(ser)

            elif choice == "4":
                uart_send(ser, "Exiting Program...")
                break

            else:
                uart_send(ser, "Invalid option. Try again.")

            time.sleep(0.5)

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("UART Closed.")

# ---------------- RUN ----------------
if __name__ == "__main__":
    main()