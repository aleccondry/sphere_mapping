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
