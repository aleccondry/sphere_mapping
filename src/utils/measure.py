"""
Module for measurement and calibration data structures.
"""
import connect_python

logger = connect_python.get_logger(__name__)

class Measurement:
    """Class to hold measurement data."""
    def __init__(self, mag: tuple[float, float, float], acc: tuple[float, float, float]):
        self.mag = mag
        self.acc = acc

    def __repr__(self) -> str:
        return f"Measurement(mag={self.mag}, acc={self.acc})"

class Calibration:
    """Class to hold calibration parameters."""
    def __init__(self, 
                 is_constant: bool, 
                 center: tuple[int, int, int], 
                 scale: tuple[int, int, int], 
                 radius: int):
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
        logger.info("Updated Calibration: %s", self)

def update_calibration(calibration: Calibration):
    """Update calibration parameters if they have changed."""
    logger.info("Updated Calibration: %s", calibration)
