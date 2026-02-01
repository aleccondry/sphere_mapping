"""Live Serial Data Plotter
Streams live data from a serial port, computes orientation using a quaternion filter,
and visualizes the orientation on a textured 3D sphere. The orientation data (yaw, pitch, roll)
is also streamed to a Nominal Connect client.
"""
from datetime import datetime, timezone
import time

import connect_python
from connect_python import Units
from vispy import app

from utils.sphere import SphereOrientation, IMAGE_SIZE
from utils.quaternion import Quaternion
from utils.measure import Calibration
from utils.serial_parser import open_serial_port, read_serial, parse_line

# Set up logger
logger = connect_python.get_logger(__name__)

def handle_calibration_data(client: connect_python.Client, cal: Calibration):
    """Update client calibration values based on received calibration data."""
    client.set_value("center_x", cal.center[0])
    client.set_value("center_y", cal.center[1])
    client.set_value("center_z", cal.center[2])
    client.set_value("scale_x", cal.scale[0])
    client.set_value("scale_y", cal.scale[1])
    client.set_value("scale_z", cal.scale[2])
    client.set_value("radius", cal.radius)
    client.set_value("calibration_type", "constant")


@connect_python.main
def stream_data(client: connect_python.Client):
    """Stream live serial data to the client."""
    logger.info("Starting live serial data plotting")

    client.clear_all_values()
    client.clear_all_streams()
    client.clear_frame_buffer("frame_buffer")

    ser = open_serial_port()
    sphere = SphereOrientation(render=False)
    quat = Quaternion()
    last = time.time()

    def on_timer(event):
        nonlocal last

        # Handle calibration updates from the client.
        cal_type = client.get_value("calibration_type") == "constant"
        if not cal_type:
            logger.info("Requesting manual calibration from device")
            ser.write("SCAL\r".encode("utf-8"))
            client.set_value("calibration_type", "constant")

        # Read serial data.
        line = read_serial(ser)
        if not line:
            return

        # Parse measurement data or calibration data from serial.
        result = parse_line(line)
        if not result:
            return
        elif isinstance(result, Calibration):
            logger.info("Received calibration data from device: %s", result)
            handle_calibration_data(client, result)
            return

        now = time.time()
        dt = now - last
        last = now

        # Update quaternion and sphere orientation.
        quat.update(result, dt)
        sphere.update(quat)

        # Extract Euler angles from quaternion.
        yaw, pitch, roll = quat.to_euler_zyx()
        t_datetime = datetime.now(timezone.utc)

        # Stream frame buffer and orientation data.
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
