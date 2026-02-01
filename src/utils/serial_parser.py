"""
Module for serial communication and data parsing.
"""
import sys
import re

import connect_python
import serial

from .measure import Measurement, Calibration

logger = connect_python.get_logger(__name__)

# Serial port configuration
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

# Regex pattern to match the expected format
meas_pattern = re.compile(r'Measurement: (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?)\r?\n?')
cal_pattern = re.compile(r'Calibration: (-?\d+), (-?\d+), (-?\d+), (-?\d+), (-?\d+), (-?\d+), (\d+)\r?\n?')

def open_serial_port(port: str=SERIAL_PORT, baudrate: int=BAUD_RATE) -> serial.Serial:
    """Open and return a serial port."""
    try:
        uart = serial.Serial(port, baudrate, timeout=1)
        logger.info("Successfully opened %s", port)
        return uart
    except serial.SerialException as e:
        logger.error("Could not open serial port %s: %s", port, e)
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
        logger.error("Error reading from serial port: %s", e)
        return None

def parse_line(line: str) -> Measurement | Calibration | None:
    """
    Parse of a line of serial data.
    Expected format: "Measurement: {mag_x}, {mag_y}, {mag_z}, {acc_x}, {acc_y}, {acc_z}"
    or "Calibration: {center_x}, {center_y}, {center_z}, {scale_x}, {scale_y}, {scale_z}, {radius}"
    """
    match = meas_pattern.search(line)
    if match:
        try:
            mag = (float(match.group(1)), float(match.group(2)), float(match.group(3)))
            acc = (float(match.group(4)), float(match.group(5)), float(match.group(6)))
            return Measurement(mag=mag, acc=acc)
        except ValueError:
            logger.error("Error parsing measurement line: %s", line)
    match = cal_pattern.search(line)
    if match:
        try:
            center = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            scale = (int(match.group(4)), int(match.group(5)), int(match.group(6)))
            radius = int(match.group(7))
            return Calibration(is_constant=True, center=center, scale=scale, radius=radius)
        except ValueError:
            logger.error("Error parsing calibration line: %s", line)
    return None
