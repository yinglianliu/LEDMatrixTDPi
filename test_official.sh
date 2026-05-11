#!/bin/bash
cd /home/pizero2w/rpi-rgb-led-matrix/bindings/python/samples
sudo python3 runtext.py --led-rows=64 --led-cols=64 --led-slowdown-gpio=4 --led-row-addr-type=0 --led-gpio-mapping=adafruit-hat --led-no-hardware-pulse=1 --led-brightness=80 --text="IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII"
