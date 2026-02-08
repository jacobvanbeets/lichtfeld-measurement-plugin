# SPDX-FileCopyrightText: 2025 LichtFeld Studio Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Measurement data structures and calculations."""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List
import numpy as np
from uuid import uuid4


@dataclass
class Measurement:
    """A single measurement between two points."""
    
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    point1: Optional[Tuple[float, float, float]] = None
    point2: Optional[Tuple[float, float, float]] = None
    color: Tuple[float, float, float, float] = (0.0, 1.0, 0.5, 1.0)  # Cyan-green
    visible: bool = True
    
    def __post_init__(self):
        if not self.name:
            self.name = f"Measurement {self.id}"
    
    @property
    def is_complete(self) -> bool:
        """Check if both points are set."""
        return self.point1 is not None and self.point2 is not None
    
    @property
    def distance(self) -> Optional[float]:
        """Calculate the 3D distance between the two points."""
        if not self.is_complete:
            return None
        p1 = np.array(self.point1)
        p2 = np.array(self.point2)
        return float(np.linalg.norm(p2 - p1))
    
    @property
    def midpoint(self) -> Optional[Tuple[float, float, float]]:
        """Get the midpoint between the two points."""
        if not self.is_complete:
            return None
        p1 = np.array(self.point1)
        p2 = np.array(self.point2)
        mid = (p1 + p2) / 2.0
        return tuple(mid)
    
    @property
    def delta(self) -> Optional[Tuple[float, float, float]]:
        """Get the delta (difference) between point2 and point1."""
        if not self.is_complete:
            return None
        p1 = np.array(self.point1)
        p2 = np.array(self.point2)
        d = p2 - p1
        return (float(d[0]), float(d[1]), float(d[2]))
    
    def format_distance(self, decimals: int = 3) -> str:
        """Format the distance as a string with units."""
        dist = self.distance
        if dist is None:
            return "N/A"
        return f"{dist:.{decimals}f}"
    
    def format_delta(self, decimals: int = 3) -> str:
        """Format the delta as a string."""
        d = self.delta
        if d is None:
            return "N/A"
        return f"Δ({d[0]:.{decimals}f}, {d[1]:.{decimals}f}, {d[2]:.{decimals}f})"
    
    def clear(self):
        """Clear both points."""
        self.point1 = None
        self.point2 = None


class MeasurementStore:
    """Store for managing multiple measurements."""
    
    # Color palette for measurements
    COLORS = [
        (0.0, 1.0, 0.5, 1.0),   # Cyan-green
        (1.0, 0.5, 0.0, 1.0),   # Orange
        (0.5, 0.5, 1.0, 1.0),   # Light blue
        (1.0, 0.0, 0.5, 1.0),   # Pink
        (0.5, 1.0, 0.0, 1.0),   # Lime
        (1.0, 1.0, 0.0, 1.0),   # Yellow
        (0.0, 1.0, 1.0, 1.0),   # Cyan
        (1.0, 0.0, 1.0, 1.0),   # Magenta
    ]
    
    def __init__(self):
        self._measurements: List[Measurement] = []
        self._active_index: int = -1
        self._color_index: int = 0
    
    @property
    def measurements(self) -> List[Measurement]:
        """Get all measurements."""
        return self._measurements
    
    @property
    def active(self) -> Optional[Measurement]:
        """Get the currently active measurement."""
        if 0 <= self._active_index < len(self._measurements):
            return self._measurements[self._active_index]
        return None
    
    @property
    def active_index(self) -> int:
        """Get the active measurement index."""
        return self._active_index
    
    @active_index.setter
    def active_index(self, value: int):
        """Set the active measurement index."""
        if -1 <= value < len(self._measurements):
            self._active_index = value
    
    def _next_color(self) -> Tuple[float, float, float, float]:
        """Get the next color from the palette."""
        color = self.COLORS[self._color_index % len(self.COLORS)]
        self._color_index += 1
        return color
    
    def create(self, name: str = "") -> Measurement:
        """Create a new measurement and make it active."""
        m = Measurement(name=name, color=self._next_color())
        self._measurements.append(m)
        self._active_index = len(self._measurements) - 1
        return m
    
    def delete(self, index: int) -> bool:
        """Delete a measurement by index."""
        if 0 <= index < len(self._measurements):
            self._measurements.pop(index)
            # Adjust active index
            if self._active_index >= len(self._measurements):
                self._active_index = len(self._measurements) - 1
            return True
        return False
    
    def delete_active(self) -> bool:
        """Delete the currently active measurement."""
        return self.delete(self._active_index)
    
    def clear_all(self):
        """Clear all measurements."""
        self._measurements.clear()
        self._active_index = -1
    
    def get_by_id(self, measurement_id: str) -> Optional[Measurement]:
        """Get a measurement by its ID."""
        for m in self._measurements:
            if m.id == measurement_id:
                return m
        return None
    
    def get_visible(self) -> List[Measurement]:
        """Get all visible measurements."""
        return [m for m in self._measurements if m.visible]


# Global singleton store
_store = MeasurementStore()


def get_measurement_store() -> MeasurementStore:
    """Get the global measurement store."""
    return _store
