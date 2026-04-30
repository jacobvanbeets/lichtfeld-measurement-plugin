# SPDX-FileCopyrightText: 2025 LichtFeld Studio Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native gizmo drag for measurement points using LichtFeld TransformGizmo API."""

import lichtfeld as lf

from ..core.measurement import get_measurement_store


# Active gizmos - keyed by "measurement_id:point_num"
_active_gizmos = {}

# Debug status
_debug_status = ""


def get_debug_status():
    """Get debug status for display."""
    return _debug_status


def _make_gizmo_key(measurement_id: str, point_num: int) -> str:
    """Create a unique key for a gizmo."""
    return f"{measurement_id}:{point_num}"


def _point_to_matrix(point) -> list:
    """Convert a 3D point to a 4x4 translation matrix (column-major, 16 floats)."""
    if point is None:
        return [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]
    x, y, z = point[0], point[1], point[2]
    # Column-major 4x4 identity with translation in last column
    return [
        1.0, 0.0, 0.0, 0.0,  # column 0
        0.0, 1.0, 0.0, 0.0,  # column 1
        0.0, 0.0, 1.0, 0.0,  # column 2
        x,   y,   z,   1.0   # column 3 (translation)
    ]


def _matrix_to_point(matrix: list) -> tuple:
    """Extract translation from a 4x4 column-major matrix."""
    # Translation is in indices 12, 13, 14 (column 3, rows 0-2)
    return (matrix[12], matrix[13], matrix[14])


def attach_gizmo(measurement_id: str, point_num: int, on_change=None, on_end=None):
    """Attach a native TranslationGizmo to a measurement point.
    
    Args:
        measurement_id: The measurement ID
        point_num: 1 or 2 for P1 or P2
        on_change: Optional callback when point changes
        on_end: Optional callback when drag ends
    
    Returns:
        True if gizmo was attached, False otherwise
    """
    global _debug_status, _active_gizmos
    
    store = get_measurement_store()
    m = store.get_by_id(measurement_id)
    if not m:
        _debug_status = "No measurement found"
        return False
    
    # Get current point
    if point_num == 1:
        point = m.point1
    else:
        point = m.point2
    
    if point is None:
        _debug_status = f"Point {point_num} is None"
        return False
    
    key = _make_gizmo_key(measurement_id, point_num)
    
    # Remove existing gizmo if any
    if key in _active_gizmos:
        try:
            _active_gizmos[key].detach()
        except:
            pass
        del _active_gizmos[key]
    
    try:
        # Create translation gizmo
        initial_matrix = _point_to_matrix(point)
        gizmo = lf.TranslationGizmo(matrix=initial_matrix, id=f"measure.{key}")
        gizmo.space = "world"
        gizmo.snap = False
        
        # Create getter/setter callbacks
        def get_transform():
            store = get_measurement_store()
            m = store.get_by_id(measurement_id)
            if not m:
                return _point_to_matrix(None)
            pt = m.point1 if point_num == 1 else m.point2
            return _point_to_matrix(pt)
        
        def set_transform(matrix):
            store = get_measurement_store()
            m = store.get_by_id(measurement_id)
            if not m:
                return
            new_point = _matrix_to_point(list(matrix))
            if point_num == 1:
                m.point1 = new_point
            else:
                m.point2 = new_point
            if on_change:
                on_change(new_point)
            lf.ui.request_redraw()
        
        # Attach with callbacks
        gizmo.attach_to_callbacks(get_transform, set_transform)
        
        # Set end callback if provided
        if on_end:
            gizmo.set_on_end(on_end)
        
        _active_gizmos[key] = gizmo
        _debug_status = f"Gizmo attached for P{point_num}"
        lf.ui.request_redraw()
        return True
        
    except Exception as e:
        _debug_status = f"Error: {type(e).__name__}: {str(e)[:40]}"
        return False


def detach_gizmo(measurement_id: str, point_num: int):
    """Detach a gizmo from a measurement point."""
    global _active_gizmos, _debug_status
    
    key = _make_gizmo_key(measurement_id, point_num)
    if key in _active_gizmos:
        try:
            _active_gizmos[key].detach()
        except:
            pass
        del _active_gizmos[key]
        _debug_status = f"Gizmo detached for P{point_num}"
        lf.ui.request_redraw()
        return True
    return False


def detach_all_gizmos():
    """Detach all active gizmos."""
    global _active_gizmos, _debug_status
    
    for key, gizmo in list(_active_gizmos.items()):
        try:
            gizmo.detach()
        except:
            pass
    _active_gizmos.clear()
    _debug_status = "All gizmos detached"
    lf.ui.request_redraw()


def is_gizmo_active(measurement_id: str, point_num: int) -> bool:
    """Check if a gizmo is active for a measurement point."""
    key = _make_gizmo_key(measurement_id, point_num)
    return key in _active_gizmos


def has_active_gizmos() -> bool:
    """Check if any gizmos are active."""
    return len(_active_gizmos) > 0


# Legacy API compatibility - these are no longer needed with native gizmos
# but kept for compatibility with panel code

def start_axis_picker(measurement_id: str, point_num: int, on_end=None):
    """Legacy: Start axis picker - now just attaches native gizmo."""
    return attach_gizmo(measurement_id, point_num, on_end=on_end)


def is_picker_active():
    """Legacy: Check if picker is active."""
    return has_active_gizmos()


def was_picker_cancelled():
    """Legacy: Check if picker was cancelled."""
    return False


def cancel_axis_picker():
    """Legacy: Cancel axis picker."""
    detach_all_gizmos()


def end_axis_picker():
    """Legacy: End axis picker."""
    pass  # Gizmos stay attached until explicitly detached


# Additional legacy exports
def start_gizmo_drag(*args, **kwargs):
    return False

def is_dragging():
    return False

def get_drag_state():
    return {'active': False}

def end_drag():
    pass

def hit_test_gizmo_axis(*args, **kwargs):
    return None

def get_debug_info():
    return "", {}

def get_last_event():
    return ""

def get_drag_status():
    return _debug_status

def get_drag_fail_reason():
    return ""
