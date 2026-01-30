"""
Module for serial communication and data parsing.
"""
import serial
import sys
import re

import connect_python

from utils.measure import Measurement

logger = connect_python.get_logger(__name__)

# Serial port configuration
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

# Regex pattern to match the expected format
pattern = re.compile(r'Measurement: (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?)\r?\n?')

def open_serial_port(port: str=SERIAL_PORT, baudrate: int=BAUD_RATE) -> serial.Serial:
    """Open and return a serial port."""
    try:
        uart = serial.Serial(port, baudrate, timeout=1)
        logger.info(f"Successfully opened {port}")
        return uart
    except serial.SerialException as e:
        logger.error(f"Could not open serial port {port}: {e}")
        sys.exit(1)

def read_serial(uart: serial.Serial | None) -> str | None:
    """Read a line from the serial port."""
    try:
        if uart and uart.in_waiting > 0:
            line_bytes = uart.readline()
            line_str = line_bytes.decode('utf-8', errors='ignore').strip()
            return line_str
        return None
    except Exception as e:
        logger.error(f"Error reading from serial port: {e}")
        return None

def parse_line(line: str) -> Measurement | None:
    """
    Parse of a line of serial data.
    Expected format: "Measurement: {mag_x}, {mag_y}, {mag_z}, {acc_x}, {acc_y}, {acc_z}"
    """
    match = pattern.search(line)
    if match:
        try:
            mag = (float(match.group(1)), float(match.group(2)), float(match.group(3)))
            acc = (float(match.group(4)), float(match.group(5)), float(match.group(6)))
            return Measurement(mag=mag, acc=acc)
        except ValueError:
            print(f"Error parsing line: {line}")
    return None
