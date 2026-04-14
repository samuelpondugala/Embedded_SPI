from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont
import time

# Initialize I2C (address 0x3C, port 1)
serial = i2c(port=1, address=0x3C)

# Initialize OLED (128x32)
device = ssd1306(serial)

# Create blank image
image = Image.new("1", (device.width, device.height))
draw = ImageDraw.Draw(image)

# Draw text
draw.text((10, 10), "HELLO SAMUEL", fill=255)

# Display on OLED
device.display(image)

# Keep it visible
time.sleep(10)

# Clear display
device.clear()