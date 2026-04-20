import spidev
import RPi.GPIO as GPIO
import time

DC = 24
RST = 25

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC, GPIO.OUT)
GPIO.setup(RST, GPIO.OUT)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 20000000

# -------- LOW LEVEL --------
def cmd(c):
    GPIO.output(DC, 0)
    spi.writebytes([c])

def data(d):
    GPIO.output(DC, 1)
    spi.writebytes([d >> 8, d & 0xFF])

def write_reg(reg, val):
    cmd(reg)
    data(val)

def reset():
    GPIO.output(RST, 0)
    time.sleep(0.1)
    GPIO.output(RST, 1)
    time.sleep(0.1)

# -------- REAL INIT --------
def init_display():
    reset()

    write_reg(0x01, 0x011C)
    write_reg(0x02, 0x0100)
    write_reg(0x03, 0x1030)
    write_reg(0x08, 0x0808)
    write_reg(0x0C, 0x0000)
    write_reg(0x0F, 0x0A01)

    write_reg(0x20, 0x0000)
    write_reg(0x21, 0x0000)

    write_reg(0x10, 0x0A00)
    write_reg(0x11, 0x1038)
    write_reg(0x12, 0x1121)
    write_reg(0x13, 0x0066)
    write_reg(0x14, 0x5F60)

    time.sleep(0.1)

    write_reg(0x30, 0x0000)
    write_reg(0x31, 0x00DB)
    write_reg(0x32, 0x0000)
    write_reg(0x33, 0x0000)

    write_reg(0x34, 0x00DB)
    write_reg(0x35, 0x0000)

    write_reg(0x50, 0x0000)
    write_reg(0x51, 0x0808)
    write_reg(0x52, 0x080A)
    write_reg(0x53, 0x000A)
    write_reg(0x54, 0x0A08)
    write_reg(0x55, 0x0808)
    write_reg(0x56, 0x0000)
    write_reg(0x57, 0x0A00)
    write_reg(0x58, 0x0710)
    write_reg(0x59, 0x0710)

    write_reg(0x07, 0x1017)  # Display ON

# -------- DRAW --------
def set_window(x1, y1, x2, y2):
    write_reg(0x36, x2)
    write_reg(0x37, x1)
    write_reg(0x38, y2)
    write_reg(0x39, y1)
    write_reg(0x20, x1)
    write_reg(0x21, y1)
    cmd(0x22)

def fill_screen(color):
    set_window(0, 0, 175, 219)
    GPIO.output(DC, 1)
    for _ in range(176 * 220):
        spi.writebytes([color >> 8, color & 0xFF])

# -------- RUN --------
init_display()

fill_screen(0xF800)  # RED
time.sleep(2)
fill_screen(0x07E0)  # GREEN
time.sleep(2)
fill_screen(0x001F)  # BLUE