#!/usr/bin/env python3
"""
usb_uart_test.py - PySerial USB-to-UART quick test

Works best with a LOOPBACK:
  Connect adapter TX -> RX (and GND -> GND).

Usage examples:
  python3 usb_uart_test.py --list
  python3 usb_uart_test.py -p COM5 -b 115200
  python3 usb_uart_test.py -p /dev/ttyUSB0 -b 115200 --interactive
"""

import argparse
import sys
import time

import serial
from serial.tools import list_ports


def list_serial_ports() -> None:
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return

    print("Available serial ports:")
    for p in ports:
        # p.device: COM5 or /dev/ttyUSB0
        # p.description: USB-SERIAL CH340, FT232R, CP2102, etc.
        # p.hwid: VID:PID=xxxx:yyyy ...
        print(f"  {p.device:15}  {p.description}  [{p.hwid}]")


def open_port(port: str, baud: int, timeout: float) -> serial.Serial:
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,       # read timeout (seconds)
            write_timeout=timeout  # write timeout (seconds)
        )
        # Small settling time for some USB-UART chips after open
        time.sleep(0.1)
        # Flush buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        return ser
    except serial.SerialException as e:
        raise SystemExit(f"Failed to open {port}: {e}") from e


def hexdump(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)


def loopback_test(ser: serial.Serial, payload: bytes, read_timeout: float) -> bool:
    print(f"\nOpened: {ser.port} @ {ser.baudrate} bps")
    print(f"TX ({len(payload)} bytes): {payload!r}")
    print(f"TX hex: {hexdump(payload)}")

    try:
        written = ser.write(payload)
        ser.flush()
        if written != len(payload):
            print(f"WARNING: wrote {written}/{len(payload)} bytes")
    except serial.SerialTimeoutException:
        print("ERROR: write timeout")
        return False

    # Read back up to payload length (loopback) within a deadline
    deadline = time.time() + read_timeout
    rx = b""
    while time.time() < deadline and len(rx) < len(payload):
        chunk = ser.read(len(payload) - len(rx))
        if chunk:
            rx += chunk

    print(f"RX ({len(rx)} bytes): {rx!r}")
    print(f"RX hex: {hexdump(rx)}")

    if rx == payload:
        print("✅ LOOPBACK PASS: RX matches TX")
        return True

    if len(rx) == 0:
        print("❌ No data received. If doing loopback, connect TX->RX and GND->GND.")
    else:
        print("❌ Data mismatch. Check baud/parity/stopbits, wiring, or that device echoes.")
    return False


def interactive_mode(ser: serial.Serial) -> None:
    print("\nInteractive mode:")
    print("  - Type text and press Enter to send")
    print("  - Ctrl+C to exit\n")

    try:
        while True:
            line = input("> ")
            data = (line + "\n").encode("utf-8", errors="replace")
            ser.write(data)
            ser.flush()

            # Non-blocking-ish read of whatever came back shortly after
            time.sleep(0.05)
            waiting = ser.in_waiting
            if waiting:
                rx = ser.read(waiting)
                # Try to show as text but keep bytes safe
                try:
                    txt = rx.decode("utf-8", errors="replace")
                    print(f"< {txt.rstrip()}")
                except Exception:
                    print(f"< {rx!r}")
            else:
                print("< (no response)")
    except KeyboardInterrupt:
        print("\nBye.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="List available serial ports and exit")
    ap.add_argument("-p", "--port", help="Serial port (e.g., COM5 or /dev/ttyUSB0)")
    ap.add_argument("-b", "--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    ap.add_argument("--timeout", type=float, default=0.2, help="Serial read/write timeout (seconds)")
    ap.add_argument("--read-deadline", type=float, default=1.5, help="Max time to wait for echo (seconds)")
    ap.add_argument("--interactive", action="store_true", help="Interactive send/receive mode")
    ap.add_argument("--payload", default="TechDhaba USB-UART test 12345\r\n",
                    help="Payload to send in loopback test (default is a text line)")

    args = ap.parse_args()

    if args.list:
        list_serial_ports()
        return 0

    if not args.port:
        print("ERROR: --port is required unless --list is used.\n")
        list_serial_ports()
        return 2

    ser = open_port(args.port, args.baud, args.timeout)
    try:
        ok = loopback_test(ser, args.payload.encode("utf-8"), args.read_deadline)
        if args.interactive:
            interactive_mode(ser)
        return 0 if ok else 1
    finally:
        ser.close()


if __name__ == "__main__":
    raise SystemExit(main())