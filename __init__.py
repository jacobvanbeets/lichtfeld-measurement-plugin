# SPDX-FileCopyrightText: 2025 LichtFeld Studio Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""3D Measurement Tool Plugin for LichtFeld Studio.

Provides tools to measure distances between points on Gaussian Splats.
"""

import lichtfeld as lf

from .panels.measurement_panel import MeasurementPanel
from .operators.measure_picker import MEASURE_OT_pick_point
from .core.measurement import Measurement, MeasurementStore

_classes = [MeasurementPanel, MEASURE_OT_pick_point]


def on_load():
    """Called when plugin loads."""
    for cls in _classes:
        lf.register_class(cls)
    lf.log.info("Measurement Tool plugin loaded")


def on_unload():
    """Called when plugin unloads."""
    for cls in reversed(_classes):
        lf.unregister_class(cls)
    lf.log.info("Measurement Tool plugin unloaded")


__all__ = [
    "MeasurementPanel",
    "Measurement",
    "MeasurementStore",
]
