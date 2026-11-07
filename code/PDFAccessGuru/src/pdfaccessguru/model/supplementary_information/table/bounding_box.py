from dataclasses import dataclass

@dataclass
class BoundingBox:
    """
    Bounding box in pdfplumber coordinate space: top-left origin, y increases downward.
    """
    x0: float
    top: float
    x1: float
    bottom: float
