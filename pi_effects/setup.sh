#!/bin/bash
# Run once on the Pi to install all dependencies
# Usage: bash setup.sh

set -e
echo "=== Installing LED Matrix Effects dependencies ==="

# System packages
sudo apt-get update
sudo apt-get install -y \
    python3-pillow \
    python3-numpy \
    fonts-dejavu

# Audio library (optional — only needed for Audio Reactive effect)
echo ""
echo "Installing sounddevice for audio reactive effect..."
pip3 install sounddevice

echo ""
echo "=== Done! ==="
echo ""
echo "Run with:  sudo python3 main.py"
echo "           sudo python3 main.py --effect 2   (start on audio)"
