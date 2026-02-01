"""
Module for quaternion representation and conversion to rotation matrix.
"""
import numpy as np
from ahrs.filters import FQA

class Quaternion:
    """Quaternion representation and conversion to rotation matrix."""
    def __init__(self):
        self.q = np.array([1.0, 0.0, 0.0, 0.0])

    def __repr__(self) -> str:
        return f"Quaternion(q={self.q})"

    def update(self, measurement):
        """Update quaternion from magnetometer and accelerometer data."""
        acc = np.array(measurement.acc, dtype=float)
        acc_norm = np.linalg.norm(acc)
        if acc_norm > 0:
            acc /= acc_norm
        else:
            print("Warning: Zero accelerometer reading")
            return

        mag = np.array(measurement.mag, dtype=float)
        mag_norm = np.linalg.norm(mag)
        if mag_norm > 0:
            mag /= mag_norm
        else:
            print("Warning: Zero magnetometer reading")
            return

        # use FQA (acc+mag) to estimate orientation
        fqa = FQA()
        self.q = fqa.estimate(acc=acc, mag=mag)

    def to_matrix4(self):
        """4x4 homogeneous rotation matrix"""
        w, x, y, z = self.q

        R = np.array([
            [1 - 2*(y*y + z*z),     2*(x*y - z*w),     2*(x*z + y*w), 0],
            [2*(x*y + z*w),     1 - 2*(x*x + z*z),     2*(y*z - x*w), 0],
            [2*(x*z - y*w),         2*(y*z + x*w), 1 - 2*(x*x + y*y), 0],
            [0, 0, 0, 1]
        ])
        return R

    def to_euler_zyx(self, degrees: bool = False):
        """
        Return yaw-pitch-roll (Z-Y-X) Euler angles from the quaternion.

        - yaw: rotation about Z (psi)
        - pitch: rotation about Y (theta)
        - roll: rotation about X (phi)

        Parameters
        ----------
        degrees : bool
            If True, return angles in degrees; otherwise radians.

        Notes
        -----
        Uses the aerospace Z-Y-X convention. Angle extraction clamps the
        pitch term to handle numerical drift near +/-90°.
        """
        w, x, y, z = self.q
        yaw = np.arctan2(2.0*(w*z + x*y), 1.0 - 2.0*(y*y + z*z))
        pitch = np.arcsin(np.clip(2.0*(w*y - z*x), -1.0, 1.0))
        roll = np.arctan2(2.0*(w*x + y*z), 1.0 - 2.0*(x*x + y*y))
        if degrees:
            return tuple(np.degrees([yaw, pitch, roll]))
        return yaw, pitch, roll
