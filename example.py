#!/usr/bin/env python3

import os.path
import time

from PIL import Image
import serial

from turing_smart_screen import TuringDisplayAutoSelect


DEVICE = '/dev/cu.usbmodem2017_2_251'
if not os.path.exists(DEVICE):
    DEVICE = '/dev/cu.usbmodemUSB35INCHIPSV21'

bitmap_path = 'gerph.png'

ser = serial.Serial(DEVICE, 115200, timeout=1, rtscts=1)
display = TuringDisplayAutoSelect(ser)

# Hide everything
display.enable(False)

# If the display is rotated around 180 degrees, it image may need inverting
#display.invert(display.INVERT_XY)

# If your image is oriented for landscape
#display.orientation(display.ORIENTATION_LANDSCAPE)

# Draw a picture in the display
image = Image.open(bitmap_path)
display.update_region_pillow(0, 0, image)

# Set the brightness to half
display.brightness(128)

# And show it in one go
display.enable(True)

time.sleep(2)
