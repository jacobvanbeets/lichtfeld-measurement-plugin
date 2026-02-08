# SPDX-FileCopyrightText: 2025 LichtFeld Studio Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Measurement point picker operator - modal operator for picking measurement points."""

import lichtfeld as lf
import lichtfeld.selection as sel
from lfs_plugins.types import Operator, Event


# Module-level callback for when a point is picked
_pick_callback = None
_pick_point_num = 0
_pick_cancelled = False


def set_pick_callback(callback, point_num: int):
    """Set the callback to invoke when a point is picked."""
    global _pick_callback, _pick_point_num, _pick_cancelled
    _pick_callback = callback
    _pick_point_num = point_num
    _pick_cancelled = False


def clear_pick_callback():
    """Clear the pick callback."""
    global _pick_callback, _pick_point_num, _pick_cancelled
    _pick_callback = None
    _pick_point_num = 0
    _pick_cancelled = True


def was_pick_cancelled() -> bool:
    """Check if pick was cancelled and clear the flag."""
    global _pick_cancelled
    if _pick_cancelled:
        _pick_cancelled = False
        return True
    return False


class MEASURE_OT_pick_point(Operator):
    """Modal operator for picking a measurement point on the gaussian splat model."""
    
    label = "Pick Measurement Point"
    description = "Click on the model to pick a point for measurement"
    options = {'BLOCKING'}
    
    def invoke(self, context, event: Event) -> set:
        """Start modal mode."""
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event: Event) -> set:
        """Handle mouse events - pick points until ESC/right-click."""
        global _pick_callback, _pick_point_num
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Try to pick at mouse position
            result = sel.pick_at_screen(event.mouse_region_x, event.mouse_region_y)
            
            if result is not None and _pick_callback is not None:
                # Call callback with world position
                _pick_callback(result.world_position, _pick_point_num)
                return {'RUNNING_MODAL'}
            # No hit, continue picking
            return {'RUNNING_MODAL'}
        
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            clear_pick_callback()
            return {'CANCELLED'}
        
        # Pass through other events
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        """Clean up on cancel."""
        clear_pick_callback()
