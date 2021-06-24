#!/usr/bin/python3

# SPDX-FileCopyrightText: 2017 Tony DiCola for Adafruit Industries
# SPDX-FileCopyrightText: 2017 James DeVito for Adafruit Industries
# SPDX-License-Identifier: MIT

# This example is for use on (Linux) computers that are using CPython with
# Adafruit Blinka to support CircuitPython libraries. CircuitPython does
# not support PIL/pillow (python imaging library)!

import time
import threading
import sys
import os
import subprocess
from signal import *

import board
import busio
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import Adafruit_DHT

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

# Create the SSD1306 OLED class.
# The first two parameters are the pixel width and pixel height.  Change these
# to the right size for your display!
disp = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
disp.rotation = 2

# Clear display.
disp.fill(0)
disp.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new("1", (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = 0
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0


# Load default font.
font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the
# same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('/home/pi/Apple ][.ttf', 6)
#font = ImageFont.truetype("/usr/share/fonts/truetype/ubuntumono/ubuntu_mono.ttf", 8)

# dht_device = adafruit_dht.DHT22(board.D18, use_pulseio=False)
str_temp = '----*C'
str_hum = '----%'

class RepeatedTimer(object):
  def __init__(self, interval, function, *args, **kwargs):
    self._timer = None
    self.interval = interval
    self.function = function
    self.args = args
    self.kwargs = kwargs
    self.is_running = False
    self.next_call = time.time()
    self.start()

  def _run(self):
    self.is_running = False
    self.start()
    self.function(*self.args, **self.kwargs)

  def start(self):
    if not self.is_running:
      self.next_call += self.interval
      self._timer = threading.Timer(self.next_call - time.time(), self._run)
      self._timer.start()
      self.is_running = True

  def stop(self):
    self._timer.cancel()
    self.is_running = False

def update_dht():
    humidity, temperature = Adafruit_DHT.read(Adafruit_DHT.DHT22, 18)
    if humidity is not None and temperature is not None:
        str_temp = '{0:0.2f}*C'.format(temperature)
        str_hum = '{0:0.2f}%'.format(humidity)

dht_updater = RepeatedTimer(2, update_dht)

def cleanup(*args):
    print("\nOLED Termintated. Cleaning up\n")
    disp.fill(0)
    disp.show()
    dht_updater.stop()
    sys.exit(0)

for sig in (SIGABRT, SIGINT, SIGTERM):
    dht_updater.stop()
    signal(sig, cleanup)


while True:

    try:

        # Draw a black filled box to clear the image.
        draw.rectangle((0, 0, width, height), outline=0, fill=0)

        # Shell scripts for system monitoring from here:
        # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
        cmd = "vcgencmd measure_temp | cut -f 2 -d '=' | awk '{printf \"CPU Temp: %s\", $0}'"
        temp = subprocess.check_output(cmd, shell=True).decode("utf-8")
        cmd = "hostname -I | cut -d' ' -f1"
        IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
        cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
        CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
        cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB %.2f%%\", $3,$2,$3*100/$2 }'"
        MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")
        cmd = 'df -h | awk \'$NF=="/mnt/usb_share"{printf "Disk: %s/%s %s", $3,$2,$5}\''
        Disk = subprocess.check_output(cmd, shell=True).decode("utf-8")

        time_f = time.strftime("%H:%M:%S")
        date = time.strftime("%e %b %Y")

        draw.text((x+80, top + 0), time_f, font=font, fill=255)
        draw.text((x, top +  0), date, font=font, fill=255)
        draw.text((x, top +  8), "IP: " + IP, font=font, fill=255)
        draw.text((x, top + 16), temp, font=font, fill=255)
        draw.text((x, top + 24), CPU, font=font, fill=255)
        draw.text((x, top + 32), MemUsage, font=font, fill=255)
        draw.text((x, top + 40), Disk, font=font, fill=255)
        draw.text((x, top + 48), "Atmo: " + str_temp + "  " + str_hum, font=font, fill=255)

        # Display image.
        disp.image(image)
        disp.show()


    except RuntimeError as error:
        continue
    except Exception as error:
        disp.fill(0)
        disp.show()
        raise error
    finally:
        dht_updater.stop()
