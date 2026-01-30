"""Live Serial Data Plotter
Streams live data from a serial port, computes orientation using a quaternion filter,
and visualizes the orientation on a textured 3D sphere. The orientation data (yaw, pitch, roll)
is also streamed to a Nominal Connect client.
"""
from datetime import datetime, timezone
import time
import sys
import re
import serial

import connect_python
from connect_python import Units
from vispy import app

from my_sphere import SphereOrientation, IMAGE_SIZE
from my_quaternion import Quaternion

# Serial port configuration
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

# Regex pattern to match the expected format
pattern = re.compile(r'Measurement: (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?), (-?\d+(?:\.\d+)?)\r?\n?')

# Set up logger
logger = connect_python.get_logger(__name__)

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
        print(f"Error reading from serial port: {e}")
        return None

class Measurement:
    """Class to hold measurement data."""
    def __init__(self, mag: tuple[float, float, float], acc: tuple[float, float, float]):
        self.mag = mag
        self.acc = acc

    def __repr__(self) -> str:
        return f"Measurement(mag={self.mag}, acc={self.acc})"

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

class Calibration:
    """Class to hold calibration parameters."""
    def __init__(self, is_constant: bool, center: tuple[int, int, int], scale: tuple[int, int, int], radius: int):
        self.is_constant = is_constant
        self.center = center
        self.scale = scale
        self.radius = radius

    def __repr__(self) -> str:
        return (f"Calibration(is_constant={self.is_constant}, "
                f"center={self.center}, scale={self.scale}, radius={self.radius})")
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Calibration):
            return NotImplemented
        return (self.is_constant == other.is_constant and
                self.center == other.center and
                self.scale == other.scale and
                self.radius == other.radius)
    
    def update(self, other):
        """Update calibration parameters."""
        if not isinstance(other, Calibration):
            return
        self.is_constant = other.is_constant
        self.center = other.center
        self.scale = other.scale
        self.radius = other.radius
        logger.info(f"Updated Calibration: {self}")

def update_calibration(calibration: Calibration):
    """Update calibration parameters if they have changed."""
    logger.info(f"Updated Calibration: {calibration}")

@connect_python.main
def stream_data(client: connect_python.Client):
    """Stream live serial data to the client."""
    logger.info("Starting live serial data plotting")

    client.clear_frame_buffer("frame_buffer")
    client.clear_stream("roll")
    client.clear_stream("pitch")
    client.clear_stream("yaw")

    curr_calibration = None

    ser = open_serial_port()
    sphere = SphereOrientation(render=False)
    quat = Quaternion()
    last = time.time()

    def on_timer(event):
        nonlocal last, curr_calibration

        calibrate = client.get_value("calibration_type", "constant")
        center_x = int(client.get_value("center_x", 20962))
        center_y = int(client.get_value("center_y", 34322))
        center_z = int(client.get_value("center_z", -23924))
        scale_x = int(client.get_value("scale_x", 1203))
        scale_y = int(client.get_value("scale_y", 1177))
        scale_z = int(client.get_value("scale_z", 1133))
        radius = int(client.get_value("radius", 48098))

        center = (center_x, center_y, center_z)
        scale = (scale_x, scale_y, scale_z)
        calibration = Calibration(is_constant=(calibrate == "constant"),
                                  center=center,
                                  scale=scale,
                                  radius=radius)
        
        if calibration != curr_calibration:
            curr_calibration = calibration
            curr_calibration.update(calibration)
        
        line = read_serial(ser)
        if not line:
            return

        measurement = parse_line(line)
        if not measurement:
            return

        now = time.time()
        dt = now - last
        last = now

        quat.update(measurement, dt)
        sphere.update(quat)

        yaw, pitch, roll = quat.to_euler_zyx()
        t_datetime = datetime.now(timezone.utc)

        pixels = sphere.to_bytes(n_pixels=IMAGE_SIZE * IMAGE_SIZE)
        client.stream_rgb("frame_buffer", 0, IMAGE_SIZE, pixels)

        client.stream("yaw", t_datetime, yaw, name="yaw", unit=Units.RADIAN)
        client.stream("pitch", t_datetime, pitch, name="pitch", unit=Units.RADIAN)
        client.stream("roll", t_datetime, roll, name="roll", unit=Units.RADIAN)

    timer = app.Timer(interval=0.01, connect=on_timer, start=True)
    try:
        app.run()
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        if ser:
            ser.close()


if __name__ == "__main__":
    stream_data()
