# SPDX-FileCopyrightText: 2025 LichtFeld Studio Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Gizmo drag operator - drag measurement points along axes."""

import numpy as np
import lichtfeld as lf
from lfs_plugins.types import Operator, Event

from ..core.measurement import get_measurement_store


# Drag state
_drag_active = False
_drag_axis = None  # 'x', 'y', or 'z'
_drag_point_num = 0  # 1 or 2
_drag_measurement_id = ""
_drag_start_mouse = None
_drag_start_world = None
_drag_axis_screen_dir = None  # Normalized screen direction of the axis
_drag_sensitivity = 0.01

# Axis picker modal state
_picker_active = False
_picker_measurement_id = ""
_picker_point_num = 0
_picker_cancelled = False

# Callbacks
_on_drag_update = None
_on_drag_end = None
_on_picker_end = None


def start_gizmo_drag(measurement_id: str, point_num: int, axis: str, 
                     mouse_x: float, mouse_y: float, on_update=None, on_end=None):
    """Start a gizmo drag operation."""
    global _drag_active, _drag_axis, _drag_point_num, _drag_measurement_id
    global _drag_start_mouse, _drag_start_world, _drag_axis_screen_dir
    global _on_drag_update, _on_drag_end, _drag_sensitivity
    
    store = get_measurement_store()
    m = store.get_by_id(measurement_id)
    if not m:
        return False
    
    # Get the point position
    if point_num == 1 and m.point1:
        world_pos = m.point1
    elif point_num == 2 and m.point2:
        world_pos = m.point2
    else:
        return False
    
    view = lf.get_current_view()
    if not view:
        return False
    
    # Calculate axis screen direction for projecting mouse movement
    axis_dirs = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}
    axis_dir = axis_dirs.get(axis)
    if not axis_dir:
        return False
    
    # Project axis to screen space to get direction
    screen_start = view.world_to_screen(world_pos)
    axis_end_world = (
        world_pos[0] + axis_dir[0],
        world_pos[1] + axis_dir[1],
        world_pos[2] + axis_dir[2]
    )
    screen_end = view.world_to_screen(axis_end_world)
    
    if not screen_start or not screen_end:
        return False
    
    # Compute screen direction
    dx = screen_end[0] - screen_start[0]
    dy = screen_end[1] - screen_start[1]
    length = np.sqrt(dx*dx + dy*dy)
    if length < 0.001:
        return False
    
    _drag_axis_screen_dir = (dx / length, dy / length)
    
    # Calculate sensitivity based on camera distance
    try:
        cam_pos = np.array(view.translation.numpy()).flatten()
        dist = np.linalg.norm(np.array(world_pos) - cam_pos)
        _drag_sensitivity = dist * 0.003
    except:
        _drag_sensitivity = 0.01
    
    _drag_active = True
    _drag_axis = axis
    _drag_point_num = point_num
    _drag_measurement_id = measurement_id
    _drag_start_mouse = (mouse_x, mouse_y)
    _drag_start_world = world_pos
    _on_drag_update = on_update
    _on_drag_end = on_end
    
    return True


def is_dragging():
    """Check if a drag is active."""
    return _drag_active


def get_drag_state():
    """Get current drag state."""
    return {
        'active': _drag_active,
        'axis': _drag_axis,
        'point_num': _drag_point_num,
        'measurement_id': _drag_measurement_id,
    }


def end_drag():
    """End the current drag."""
    global _drag_active, _drag_axis, _on_drag_end
    _drag_active = False
    _drag_axis = None
    if _on_drag_end:
        _on_drag_end()
    _on_drag_end = None


def cancel_drag():
    """Cancel drag and restore original position."""
    global _drag_active, _drag_axis
    
    if _drag_active and _drag_start_world:
        store = get_measurement_store()
        m = store.get_by_id(_drag_measurement_id)
        if m:
            if _drag_point_num == 1:
                m.point1 = _drag_start_world
            else:
                m.point2 = _drag_start_world
    
    _drag_active = False
    _drag_axis = None


def process_drag_move(mouse_x: float, mouse_y: float):
    """Process mouse movement during drag."""
    global _on_drag_update
    
    if not _drag_active:
        return
    
    store = get_measurement_store()
    m = store.get_by_id(_drag_measurement_id)
    if not m:
        end_drag()
        return
    
    # Calculate mouse delta projected onto axis screen direction
    dx = mouse_x - _drag_start_mouse[0]
    dy = mouse_y - _drag_start_mouse[1]
    
    # Project mouse delta onto axis direction
    projected = dx * _drag_axis_screen_dir[0] + dy * _drag_axis_screen_dir[1]
    
    # Convert to world movement
    movement = projected * _drag_sensitivity
    
    # Calculate new position
    axis_dirs = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}
    axis_dir = axis_dirs[_drag_axis]
    
    new_pos = (
        _drag_start_world[0] + axis_dir[0] * movement,
        _drag_start_world[1] + axis_dir[1] * movement,
        _drag_start_world[2] + axis_dir[2] * movement
    )
    
    # Update the point
    if _drag_point_num == 1:
        m.point1 = new_pos
    else:
        m.point2 = new_pos
    
    if _on_drag_update:
        _on_drag_update(new_pos)
    
    lf.ui.request_redraw()


class MEASURE_OT_gizmo_drag(Operator):
    """Modal operator for dragging gizmo axes."""
    
    label = "Drag Gizmo Axis"
    description = "Drag to move point along axis"
    options = {'BLOCKING'}
    
    def invoke(self, context, event: Event) -> set:
        """Start drag mode."""
        if not is_dragging():
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event: Event) -> set:
        """Handle drag events."""
        if event.type == 'MOUSEMOVE':
            process_drag_move(event.mouse_region_x, event.mouse_region_y)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            end_drag()
            return {'FINISHED'}
        
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            cancel_drag()
            lf.ui.request_redraw()
            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        """Clean up on cancel."""
        cancel_drag()


def hit_test_gizmo_axis(mouse_x: float, mouse_y: float, point: tuple, 
                        hit_radius: float = 20.0) -> str:
    """Test if mouse position hits a gizmo axis.
    
    Returns: 'x', 'y', 'z', or None
    """
    if point is None:
        return None
    
    view = lf.get_current_view()
    if not view:
        return None
    
    screen_start = view.world_to_screen(point)
    if not screen_start:
        return None
    
    # Calculate arrow length based on camera distance
    arrow_length = 0.5
    try:
        cam_pos = np.array(view.translation.numpy()).flatten()
        dist = np.linalg.norm(np.array(point) - cam_pos)
        arrow_length = dist * 0.12
    except:
        pass
    
    # Test each axis
    axes = {
        'x': (point[0] + arrow_length, point[1], point[2]),
        'y': (point[0], point[1] + arrow_length, point[2]),
        'z': (point[0], point[1], point[2] + arrow_length),
    }
    
    for axis_name, axis_end in axes.items():
        screen_end = view.world_to_screen(axis_end)
        if not screen_end:
            continue
        
        # Distance from mouse to line segment
        dist = _point_to_segment_distance(
            (mouse_x, mouse_y),
            screen_start,
            screen_end
        )
        
        if dist < hit_radius:
            return axis_name
    
    return None


def _point_to_segment_distance(point, seg_start, seg_end):
    """Compute distance from point to line segment."""
    px, py = point
    x1, y1 = seg_start
    x2, y2 = seg_end
    
    dx = x2 - x1
    dy = y2 - y1
    
    if dx == 0 and dy == 0:
        return np.sqrt((px - x1)**2 + (py - y1)**2)
    
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)))
    
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    return np.sqrt((px - closest_x)**2 + (py - closest_y)**2)


# ==========================================================================
# Axis Picker Modal - Click gizmo axis to start drag
# ==========================================================================

def start_axis_picker(measurement_id: str, point_num: int, on_end=None):
    """Start the axis picker modal.
    
    User can click on any gizmo axis to start dragging.
    """
    global _picker_active, _picker_measurement_id, _picker_point_num
    global _picker_cancelled, _on_picker_end
    
    _picker_active = True
    _picker_measurement_id = measurement_id
    _picker_point_num = point_num
    _picker_cancelled = False
    _on_picker_end = on_end
    return True


def is_picker_active():
    """Check if axis picker is active."""
    return _picker_active


def was_picker_cancelled():
    """Check if picker was cancelled."""
    return _picker_cancelled


def end_axis_picker():
    """End the axis picker."""
    global _picker_active, _on_picker_end
    _picker_active = False
    if _on_picker_end:
        _on_picker_end()
    _on_picker_end = None


def cancel_axis_picker():
    """Cancel the axis picker."""
    global _picker_active, _picker_cancelled
    _picker_active = False
    _picker_cancelled = True


def get_picker_point():
    """Get the current picker target point position."""
    if not _picker_active:
        return None
    store = get_measurement_store()
    m = store.get_by_id(_picker_measurement_id)
    if not m:
        return None
    if _picker_point_num == 1:
        return m.point1
    else:
        return m.point2


class MEASURE_OT_axis_picker(Operator):
    """Modal operator for picking a gizmo axis to drag."""
    
    label = "Pick Gizmo Axis"
    description = "Click on a gizmo axis arrow to drag the point"
    options = {'BLOCKING'}
    
    def invoke(self, context, event: Event) -> set:
        """Start picker mode."""
        if not is_picker_active():
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event: Event) -> set:
        """Handle picker events - click on axis to start drag."""
        global _picker_active, _drag_active
        
        # If we transitioned to dragging, hand off to drag handling
        if _drag_active:
            if event.type == 'MOUSEMOVE':
                process_drag_move(event.mouse_region_x, event.mouse_region_y)
                return {'RUNNING_MODAL'}
            
            elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                end_drag()
                end_axis_picker()
                lf.ui.request_redraw()
                return {'FINISHED'}
            
            elif event.type in {'RIGHTMOUSE', 'ESC'}:
                cancel_drag()
                end_axis_picker()
                lf.ui.request_redraw()
                return {'CANCELLED'}
            
            return {'RUNNING_MODAL'}
        
        # Not yet dragging - wait for click on axis
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            point = get_picker_point()
            if point:
                axis = hit_test_gizmo_axis(
                    event.mouse_region_x, 
                    event.mouse_region_y,
                    point,
                    hit_radius=25.0  # Generous hit area
                )
                if axis:
                    # Start drag on this axis
                    success = start_gizmo_drag(
                        _picker_measurement_id,
                        _picker_point_num,
                        axis,
                        event.mouse_region_x,
                        event.mouse_region_y
                    )
                    if success:
                        return {'RUNNING_MODAL'}
            # Clicked but didn't hit axis - ignore or finish?
            # Let's keep running so user can try again
            return {'RUNNING_MODAL'}
        
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            cancel_axis_picker()
            lf.ui.request_redraw()
            return {'CANCELLED'}
        
        # Allow view navigation (passthrough for middle mouse)
        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}
        
        return {'RUNNING_MODAL'}
