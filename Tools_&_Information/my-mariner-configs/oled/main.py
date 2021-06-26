#!/usr/bin/python3

# -*- coding: utf-8 -*-
# Copyright (c) 2014-2020 Richard Hull and contributors
# See LICENSE.rst for details.
# PYTHON_ARGCOMPLETE_OK


import os, sys, time
import subprocess

from pathlib import Path
from datetime import datetime

if os.name != 'posix':
    sys.exit('{} platform not supported'.format(os.name))

from oled_opts import get_device
from luma.core.render import canvas
from PIL import Image, ImageDraw, ImageFont
from sched_timer import RepeatedTimer

try:
    import psutil
except ImportError:
    print("The psutil library was not found. Run 'sudo -H pip install psutil' to install it.")
    sys.exit()
try:
    import Adafruit_DHT
except ImportError:
    print("The adafruit DHT library was not found.")
    sys.exit()
try:
    from signal import *
except ImportError:
    print("The signal library did not import successfully.")
    sys.exit()


font = ImageFont.load_default()

# TODO: custom font bitmaps for up/down arrows
# TODO: Load histogram

def bytes2human(n):
    """
    >>> bytes2human(10000)
    '9K'
    >>> bytes2human(100001221)
    '95M'
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "%sB" % n



def get_date():
    return time.strftime("%e %b %Y")

def get_time():
    return time.strftime("%H:%M:%S")

def sys_uptime():
    # load average, uptime
    uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    return "Uptime: %s" % (str(uptime).split('.')[0])

def cpu_usage():
    cpu_1m, cpu_5m, cpu_15m = os.getloadavg()
    return "CPU Load: %.2f" % (cpu_5m)

def cpu_temp():
    cmd = "vcgencmd measure_temp | cut -f 2 -d '=' | awk '{printf \"CPU Temp: %s\", $0}'"
    return subprocess.check_output(cmd, shell=True).decode("utf-8")

def mem_usage():
    cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB %.2f%%\", $3,$2,$3*100/$2 }'"
    return subprocess.check_output(cmd, shell=True).decode("utf-8")

def disk_usage(dir):
    cmd = 'df -h | awk \'$NF=="' + dir + '"{printf "Disk: %s/%s %s", $3,$2,$5}\''
    return subprocess.check_output(cmd, shell=True).decode("utf-8")
    # this doesn't reqire a subprocess, but it isn't as accuate
    # usage = shutil.disk_usage(dir)
    # return "Disk: %s/%s" % (bytes2human(usage.used), bytes2human(usage.total))

def network(iface):
    stat = psutil.net_io_counters(pernic=True)[iface]
    return "%s: Tx: %s, Rx: %s" % (iface, bytes2human(stat.bytes_sent), bytes2human(stat.bytes_recv))

def get_ip_address():
    return subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True).decode("utf-8")

str_temp = '--.--*C'
str_hum = '--.--%'

def update_dht():
    humidity, temperature = Adafruit_DHT.read(Adafruit_DHT.DHT22, 18)
    if humidity is not None and temperature is not None:
        global str_temp
        str_temp = '{0:0.2f}*C'.format(temperature)
        global str_hum
        str_hum = '{0:0.2f}%'.format(humidity)
#    print('DHT Sensor Task ran. ', str_temp, ' ', str_hum)

dht_updater = RepeatedTimer(2, update_dht)

def get_atmo():
    global str_temp
    global str_hum
    return "Atmo: " + str_temp + "  " + str_hum

def cleanup(*args):
    print("\nOLED Termintated. Cleaning up\n")
    dht_updater.stop()
    sys.exit(0)

for sig in (SIGABRT, SIGINT, SIGTERM):
    signal(sig, cleanup)


def stats(device):
    # use custom font
    # font_path = str(Path(__file__).resolve().parent.joinpath('fonts', 'C&C Red Alert [INET].ttf'))
    # font2 = ImageFont.truetype(font_path, 12)

    with canvas(device) as draw:
        draw.text((0, 0), get_date(), font=font, fill="white")
        draw.text((80, 0), get_time(), font=font, fill="white")

        try:
            draw.text((0, 16), network('wlan0'), font=font, fill="white")
            draw.text((0, 8), "IP: " + get_ip_address(), font=font, fill="white")
        except KeyError:
            draw.text((0, 8), "Network Unavailable", font=font, fill="white")
            draw.text((0, 16), "Check back later", font=font, fill="white")
            pass
        try:
            draw.text((0, 24), disk_usage('/mnt/usb_share'), font=font, fill="white")
        except KeyError:
            draw.text((0, 24), "USB Storage not accessible", font=font, fill="white")
            pass

        if device.height > 32:
            draw.text((0, 32), cpu_temp(), font=font, fill="white")
            draw.text((0, 40), cpu_usage(), font=font, fill="white")
            draw.text((0, 48), mem_usage(), font=font, fill="white")
            draw.text((0, 56), get_atmo(), font=font, fill="white")

        if device.height > 64:
            draw.text((0, 64), "More lines available", font=font, fill="white")

def main():
    while True:
        stats(device)
        time.sleep(0.1)


if __name__ == "__main__":
    try:
        device = get_device()
        main()
    except KeyboardInterrupt:
        pass

