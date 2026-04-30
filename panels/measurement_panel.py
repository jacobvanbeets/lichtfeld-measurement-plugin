# SPDX-FileCopyrightText: 2025 LichtFeld Studio Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Measurement Panel with 3D visualization."""

import time as _time
import math as _math
import numpy as np

import lichtfeld as lf

from ..core.measurement import get_measurement_store, Measurement
from ..operators.measure_picker import set_pick_callback, clear_pick_callback, was_pick_cancelled
from ..operators.gizmo_drag import (
    attach_gizmo, detach_gizmo, detach_all_gizmos, is_gizmo_active,
    has_active_gizmos
)


# Module-level state for draw handler
_draw_handler_registered = False
_picking_state = {
    'picking_point': 0,  # 0 = not picking, 1 = picking point 1, 2 = picking point 2
    'status_msg': '',
}

# Gizmo state - which point is being adjusted (0=none, 1=P1, 2=P2)
_gizmo_point = 0
_gizmo_measurement_id = ""

# Drag mode state
_drag_mode_active = False
_drag_mode_point = 0  # 1 or 2

# Axis colors for gizmo
_AXIS_COLORS = {
    'x': (1.0, 0.2, 0.2, 1.0),   # Red
    'y': (0.2, 1.0, 0.2, 1.0),   # Green
    'z': (0.2, 0.5, 1.0, 1.0),   # Blue
}

# Flash highlight state
_flash_measurement_id: str = ""
_flash_start_time: float = 0.0
_FLASH_DURATION: float = 1.5

# Module-level state for pending pick from operator
_pending_pick = None


def _on_point_picked_callback(world_pos, point_num: int):
    """Module-level callback for when a point is picked."""
    global _pending_pick
    _pending_pick = (world_pos, point_num)
    lf.ui.request_redraw()


def _measurement_draw_handler(ctx):
    """Draw handler for measurement overlays."""
    store = get_measurement_store()
    
    # Draw picking mode indicator
    picking_point = _picking_state['picking_point']
    if picking_point > 0:
        color = (0.0, 1.0, 0.5, 0.9) if picking_point == 1 else (1.0, 0.8, 0.0, 0.9)
        ctx.draw_text_2d(
            (20, 50),
            f"PICK POINT {picking_point}: Click on model (ESC to cancel)",
            color
        )
    
    # Draw all visible measurements
    for m in store.get_visible():
        _draw_measurement(ctx, m)


def _is_flashing(m: Measurement) -> float:
    """Return flash alpha (0.0-1.0) if this measurement is being flashed, else 0."""
    global _flash_measurement_id, _flash_start_time
    if m.id != _flash_measurement_id:
        return 0.0
    elapsed = _time.time() - _flash_start_time
    if elapsed >= _FLASH_DURATION:
        _flash_measurement_id = ""
        return 0.0
    pulse = _math.sin(elapsed * 10.0) * 0.5 + 0.5
    fade = 1.0 - (elapsed / _FLASH_DURATION)
    lf.ui.request_redraw()
    return pulse * fade


def _start_flash(measurement_id: str):
    """Start flashing a measurement."""
    global _flash_measurement_id, _flash_start_time
    _flash_measurement_id = measurement_id
    _flash_start_time = _time.time()
    lf.ui.request_redraw()


def _draw_gizmo_at_point(ctx, point):
    """Draw XYZ gizmo arrows at a point."""
    if point is None:
        return
    
    screen_start = ctx.world_to_screen(point)
    if not screen_start:
        return
    
    # Get camera distance to scale arrow length
    arrow_length = 0.5
    view = lf.get_current_view()
    if view:
        try:
            cam_pos = np.array(view.translation.numpy()).flatten()
            dist = np.linalg.norm(np.array(point) - cam_pos)
            arrow_length = dist * 0.12
        except:
            pass
    
    line_thickness = 4.0
    
    # Draw X axis (Red)
    x_end = (point[0] + arrow_length, point[1], point[2])
    screen_x = ctx.world_to_screen(x_end)
    if screen_x:
        ctx.draw_line_2d(screen_start, screen_x, _AXIS_COLORS['x'], line_thickness)
        ctx.draw_circle_2d(screen_x, 8.0, _AXIS_COLORS['x'], 3.0)
        ctx.draw_text_2d((screen_x[0] + 12, screen_x[1] - 5), "X", _AXIS_COLORS['x'])
    
    # Draw Y axis (Green)
    y_end = (point[0], point[1] + arrow_length, point[2])
    screen_y = ctx.world_to_screen(y_end)
    if screen_y:
        ctx.draw_line_2d(screen_start, screen_y, _AXIS_COLORS['y'], line_thickness)
        ctx.draw_circle_2d(screen_y, 8.0, _AXIS_COLORS['y'], 3.0)
        ctx.draw_text_2d((screen_y[0] + 12, screen_y[1] - 5), "Y", _AXIS_COLORS['y'])
    
    # Draw Z axis (Blue)
    z_end = (point[0], point[1], point[2] + arrow_length)
    screen_z = ctx.world_to_screen(z_end)
    if screen_z:
        ctx.draw_line_2d(screen_start, screen_z, _AXIS_COLORS['z'], line_thickness)
        ctx.draw_circle_2d(screen_z, 8.0, _AXIS_COLORS['z'], 3.0)
        ctx.draw_text_2d((screen_z[0] + 12, screen_z[1] - 5), "Z", _AXIS_COLORS['z'])
    
    # Draw white center
    ctx.draw_circle_2d(screen_start, 10.0, (1.0, 1.0, 1.0, 1.0), 3.0)


def _draw_measurement(ctx, m: Measurement):
    """Draw a single measurement."""
    global _gizmo_point, _gizmo_measurement_id
    
    flash = _is_flashing(m)
    color = m.color
    
    # Flash: override color to bright yellow pulsing
    if flash > 0:
        color = (1.0, 1.0, 0.0, 0.5 + flash * 0.5)
        point_size = 20.0 + flash * 12.0
        line_width = 3.0 + flash * 4.0
    else:
        point_size = 16.0
        line_width = 2.0
    
    # Check if this measurement has gizmo active
    show_gizmo_p1 = (m.id == _gizmo_measurement_id and _gizmo_point == 1)
    show_gizmo_p2 = (m.id == _gizmo_measurement_id and _gizmo_point == 2)
    
    # Draw Point 1
    if m.point1 is not None:
        ctx.draw_point_3d(m.point1, color, point_size)
        screen1 = ctx.world_to_screen(m.point1)
        if screen1:
            ctx.draw_circle_2d(screen1, 12.0, color, 2.0)
            ctx.draw_text_2d((screen1[0] + 15, screen1[1] - 8), "P1", color)
        
        # Draw gizmo at P1 if active
        if show_gizmo_p1:
            _draw_gizmo_at_point(ctx, m.point1)
    
    # Draw Point 2
    if m.point2 is not None:
        ctx.draw_point_3d(m.point2, color, point_size)
        screen2 = ctx.world_to_screen(m.point2)
        if screen2:
            ctx.draw_circle_2d(screen2, 12.0, color, 2.0)
            ctx.draw_text_2d((screen2[0] + 15, screen2[1] - 8), "P2", color)
        
        # Draw gizmo at P2 if active
        if show_gizmo_p2:
            _draw_gizmo_at_point(ctx, m.point2)
    
    # Draw line and distance if complete
    if m.is_complete:
        # Draw line in 3D
        ctx.draw_line_3d(m.point1, m.point2, color, line_width)
        
        # Draw distance at midpoint
        midpoint = m.midpoint
        if midpoint:
            screen_mid = ctx.world_to_screen(midpoint)
            if screen_mid:
                dist_text = f"{m.distance:.3f}"
                # Draw background for readability
                ctx.draw_text_2d(
                    (screen_mid[0] + 2, screen_mid[1] + 2),
                    dist_text,
                    (0.0, 0.0, 0.0, 0.8)
                )
                ctx.draw_text_2d(
                    (screen_mid[0], screen_mid[1]),
                    dist_text,
                    color
                )


def _ensure_draw_handler():
    """Ensure the draw handler is registered."""
    global _draw_handler_registered
    if not _draw_handler_registered:
        try:
            lf.remove_draw_handler("measurement_overlay")
        except:
            pass
        lf.add_draw_handler("measurement_overlay", _measurement_draw_handler, "POST_VIEW")
        _draw_handler_registered = True


class MeasurementPanel(lf.ui.Panel):
    """Panel for 3D measurement tool."""
    
    id = "measurement_tool.measurement_panel"
    label = "Measurement"
    space = lf.ui.PanelSpace.MAIN_PANEL_TAB
    order = 26
    
    def __init__(self):
        self._picking_point = 0  # 0 = not picking, 1 or 2 = picking that point
        self._adjust_point = 0   # 0 = not adjusting, 1 or 2 = adjusting that point
        self._step_size = 0.01   # Step size for adjustment
        self._status_msg = ""
        self._status_is_error = False
        self._show_details = True
        self._decimals = 3
    
    @classmethod
    def poll(cls, context) -> bool:
        return lf.has_scene()
    
    def _process_pending_pick(self):
        """Process any pending pick from the modal operator."""
        global _pending_pick
        if _pending_pick is None:
            return False
        
        world_pos, point_num = _pending_pick
        _pending_pick = None
        
        store = get_measurement_store()
        m = store.active
        
        if m is None:
            # Auto-create a measurement if none exists
            m = store.create()
        
        if point_num == 1:
            m.point1 = world_pos
            self._status_msg = f"Point 1 set (click again or press ESC)"
        else:
            m.point2 = world_pos
            self._status_msg = f"Point 2 set (click again or press ESC)"
        
        self._status_is_error = False
        lf.ui.request_redraw()
        return True
    
    def _start_picking(self, point_num: int):
        """Start picking mode using modal operator."""
        global _pending_pick
        _pending_pick = None
        
        self._picking_point = point_num
        self._status_msg = f"Click on model to set Point {point_num}..."
        self._status_is_error = False
        
        set_pick_callback(_on_point_picked_callback, point_num)
        op_id = "lfs_plugins.measurement_tool.operators.measure_picker.MEASURE_OT_pick_point"
        lf.ui.ops.invoke(op_id)
        lf.ui.request_redraw()
    
    def _cancel_picking(self):
        """Cancel picking mode."""
        self._picking_point = 0
        clear_pick_callback()
        lf.ui.ops.cancel_modal()
        self._status_msg = "Picking cancelled"
        self._status_is_error = False
        lf.ui.request_redraw()
    
    def _toggle_gizmo(self, measurement_id: str, point_num: int):
        """Toggle the native transform gizmo for a measurement point."""
        global _gizmo_point, _gizmo_measurement_id
        
        if is_gizmo_active(measurement_id, point_num):
            # Detach gizmo
            detach_gizmo(measurement_id, point_num)
            _gizmo_point = 0
            _gizmo_measurement_id = ""
            self._status_msg = f"Gizmo disabled for P{point_num}"
        else:
            # Attach gizmo
            success = attach_gizmo(measurement_id, point_num)
            if success:
                _gizmo_point = point_num
                _gizmo_measurement_id = measurement_id
                self._status_msg = f"Gizmo enabled for P{point_num} - drag to move"
            else:
                self._status_msg = f"Failed to attach gizmo"
                self._status_is_error = True
        
        self._status_is_error = False
        lf.ui.request_redraw()
    
    def draw(self, layout):
        # Global declarations at top of method
        global _drag_mode_active, _drag_mode_point, _gizmo_point, _gizmo_measurement_id
        global _picking_state
        
        theme = lf.ui.theme()
        scale = layout.get_dpi_scale()
        store = get_measurement_store()
        
        # Process any pending pick
        self._process_pending_pick()
        
        # Check if picking was cancelled
        if was_pick_cancelled() and self._picking_point > 0:
            self._picking_point = 0
            self._status_msg = "Picking stopped"
            self._status_is_error = False
        
        # No longer need to check for cancelled picker with native gizmos
        
        # Ensure draw handler
        _ensure_draw_handler()
        
        # Update module-level state
        _picking_state['picking_point'] = self._picking_point
        _picking_state['status_msg'] = self._status_msg
        
        # === New Measurement Button ===
        if layout.button("+ New Measurement", (-1, 32 * scale)):
            if self._picking_point > 0:
                self._cancel_picking()
            store.create()
            self._status_msg = "Created new measurement"
            self._status_is_error = False
        
        # === Pick Point Controls (always at top) ===
        m = store.active
        if m is not None:
            # Pick Point 1
            if self._picking_point == 1:
                if layout.button_styled("[x] Stop Picking Point 1##pick1", "error", (-1, 32 * scale)):
                    self._cancel_picking()
            else:
                btn_label = "Pick Point 1" if m.point1 is None else "Re-pick Point 1"
                if layout.button(f"{btn_label}##pick1", (-1, 32 * scale)):
                    self._start_picking(1)
            
            # Pick Point 2
            if self._picking_point == 2:
                if layout.button_styled("[x] Stop Picking Point 2##pick2", "error", (-1, 32 * scale)):
                    self._cancel_picking()
            else:
                btn_label = "Pick Point 2" if m.point2 is None else "Re-pick Point 2"
                if layout.button(f"{btn_label}##pick2", (-1, 32 * scale)):
                    self._start_picking(2)
            
            # Clear points
            if m.point1 or m.point2:
                if layout.button("Clear Points##clear", (-1, 0)):
                    m.clear()
                    self._status_msg = "Points cleared"
                    self._status_is_error = False
                    lf.ui.request_redraw()
        
        layout.separator()
        
        # === Measurement List ===
        if not store.measurements:
            layout.text_colored("No measurements yet", theme.palette.text_dim)
            layout.text_colored("Click '+ New Measurement' to start", theme.palette.text_dim)
        else:
            for i, m in enumerate(store.measurements):
                is_active = (i == store.active_index)
                
                # Measurement header row
                layout.push_id(f"meas_{m.id}")
                
                # Build display label with distance
                if m.is_complete:
                    display_name = f"{m.name} — {m.format_distance(self._decimals)}"
                else:
                    display_name = f"{m.name}: (incomplete)"
                
                # Measurement name row
                if is_active:
                    layout.text_colored(f"▶ {display_name}", m.color if m.is_complete else theme.palette.text_dim)
                else:
                    if layout.button(f"{display_name}##sel", (-1, 0)):
                        store.active_index = i
                
                # Control buttons row for every measurement
                if layout.button(f"Flash##flash", (50 * scale, 0)):
                    _start_flash(m.id)
                layout.same_line()
                if layout.button(f"Remeasure##remeasure", (80 * scale, 0)):
                    m.clear()
                    store.active_index = i
                    self._start_picking(1)
                layout.same_line()
                vis_text = "Hide" if m.visible else "Show"
                if layout.button(f"{vis_text}##vis", (50 * scale, 0)):
                    m.visible = not m.visible
                    lf.ui.request_redraw()
                layout.same_line()
                if layout.button_styled("Delete##del", "error", (55 * scale, 0)):
                    store.delete(i)
                    lf.ui.request_redraw()
                
                layout.pop_id()
                
                # Show details for active measurement
                if is_active and self._show_details:
                    layout.indent(20 * scale)
                    
                    # Point 1 info
                    if m.point1:
                        p1_str = f"P1: ({m.point1[0]:.{self._decimals}f}, {m.point1[1]:.{self._decimals}f}, {m.point1[2]:.{self._decimals}f})"
                        layout.text_colored(p1_str, (0.7, 0.7, 0.7, 1.0))
                    
                    # Point 2 info
                    if m.point2:
                        p2_str = f"P2: ({m.point2[0]:.{self._decimals}f}, {m.point2[1]:.{self._decimals}f}, {m.point2[2]:.{self._decimals}f})"
                        layout.text_colored(p2_str, (0.7, 0.7, 0.7, 1.0))
                    
                    # Delta info
                    if m.is_complete:
                        layout.text_colored(m.format_delta(self._decimals), (0.6, 0.6, 0.6, 1.0))
                        layout.spacing()
                        layout.label("Distance")
                        layout.button_styled(
                            f"Distance measured {m.format_distance(self._decimals)} units##dist_{m.id}",
                            "primary",
                            (-1, 32 * scale),
                        )
                        
                        # === Adjust Points Section ===
                        layout.spacing()
                        layout.separator()
                        layout.text_colored("─── Adjust Points ───", (1.0, 0.8, 0.2, 1.0))
                        
                        # Step size control
                        layout.label("Step:")
                        layout.same_line()
                        step_options = [(0.001, ".001"), (0.01, ".01"), (0.1, ".1"), (1.0, "1.0")]
                        for idx, (step_val, step_lbl) in enumerate(step_options):
                            is_sel = abs(self._step_size - step_val) < 0.0001
                            if is_sel:
                                if layout.button_styled(f"{step_lbl}##st", "primary", (40 * scale, 0)):
                                    self._step_size = step_val
                            else:
                                if layout.button(f"{step_lbl}##st{step_lbl}", (40 * scale, 0)):
                                    self._step_size = step_val
                            if idx < len(step_options) - 1:
                                layout.same_line()
                        
                        layout.spacing()
                        
                        # Point 1 gizmo toggle
                        gizmo_p1_on = is_gizmo_active(m.id, 1)
                        if gizmo_p1_on:
                            if layout.button_styled("[P1 Gizmo ON] Click to disable##giz1", "primary", (-1, 28 * scale)):
                                self._toggle_gizmo(m.id, 1)
                        else:
                            if layout.button("Enable P1 Gizmo##giz1", (-1, 24 * scale)):
                                self._toggle_gizmo(m.id, 1)
                        
                        layout.text_colored("P1:", (0.4, 1.0, 0.4, 1.0))
                        layout.same_line()
                        layout.text_colored("X", (1.0, 0.3, 0.3, 1.0))
                        layout.same_line()
                        if layout.button("-##p1x-", (25 * scale, 0)):
                            m.point1 = (m.point1[0] - self._step_size, m.point1[1], m.point1[2])
                            lf.ui.request_redraw()
                        layout.same_line()
                        if layout.button("+##p1x+", (25 * scale, 0)):
                            m.point1 = (m.point1[0] + self._step_size, m.point1[1], m.point1[2])
                            lf.ui.request_redraw()
                        layout.same_line()
                        layout.text_colored("Y", (0.3, 1.0, 0.3, 1.0))
                        layout.same_line()
                        if layout.button("-##p1y-", (25 * scale, 0)):
                            m.point1 = (m.point1[0], m.point1[1] - self._step_size, m.point1[2])
                            lf.ui.request_redraw()
                        layout.same_line()
                        if layout.button("+##p1y+", (25 * scale, 0)):
                            m.point1 = (m.point1[0], m.point1[1] + self._step_size, m.point1[2])
                            lf.ui.request_redraw()
                        layout.same_line()
                        layout.text_colored("Z", (0.3, 0.3, 1.0, 1.0))
                        layout.same_line()
                        if layout.button("-##p1z-", (25 * scale, 0)):
                            m.point1 = (m.point1[0], m.point1[1], m.point1[2] - self._step_size)
                            lf.ui.request_redraw()
                        layout.same_line()
                        if layout.button("+##p1z+", (25 * scale, 0)):
                            m.point1 = (m.point1[0], m.point1[1], m.point1[2] + self._step_size)
                            lf.ui.request_redraw()
                        
                        # Point 2 gizmo toggle
                        gizmo_p2_on = is_gizmo_active(m.id, 2)
                        if gizmo_p2_on:
                            if layout.button_styled("[P2 Gizmo ON] Click to disable##giz2", "primary", (-1, 28 * scale)):
                                self._toggle_gizmo(m.id, 2)
                        else:
                            if layout.button("Enable P2 Gizmo##giz2", (-1, 24 * scale)):
                                self._toggle_gizmo(m.id, 2)
                        
                        # Point 2 adjustment
                        layout.text_colored("P2:", (1.0, 0.6, 0.2, 1.0))
                        layout.same_line()
                        layout.text_colored("X", (1.0, 0.3, 0.3, 1.0))
                        layout.same_line()
                        if layout.button("-##p2x-", (25 * scale, 0)):
                            m.point2 = (m.point2[0] - self._step_size, m.point2[1], m.point2[2])
                            lf.ui.request_redraw()
                        layout.same_line()
                        if layout.button("+##p2x+", (25 * scale, 0)):
                            m.point2 = (m.point2[0] + self._step_size, m.point2[1], m.point2[2])
                            lf.ui.request_redraw()
                        layout.same_line()
                        layout.text_colored("Y", (0.3, 1.0, 0.3, 1.0))
                        layout.same_line()
                        if layout.button("-##p2y-", (25 * scale, 0)):
                            m.point2 = (m.point2[0], m.point2[1] - self._step_size, m.point2[2])
                            lf.ui.request_redraw()
                        layout.same_line()
                        if layout.button("+##p2y+", (25 * scale, 0)):
                            m.point2 = (m.point2[0], m.point2[1] + self._step_size, m.point2[2])
                            lf.ui.request_redraw()
                        layout.same_line()
                        layout.text_colored("Z", (0.3, 0.3, 1.0, 1.0))
                        layout.same_line()
                        if layout.button("-##p2z-", (25 * scale, 0)):
                            m.point2 = (m.point2[0], m.point2[1], m.point2[2] - self._step_size)
                            lf.ui.request_redraw()
                        layout.same_line()
                        if layout.button("+##p2z+", (25 * scale, 0)):
                            m.point2 = (m.point2[0], m.point2[1], m.point2[2] + self._step_size)
                            lf.ui.request_redraw()
                    
                    layout.unindent(20 * scale)
        
        # === Settings ===
        layout.separator()
        if layout.collapsing_header("Settings", default_open=False):
            _, self._show_details = layout.checkbox("Show Details", self._show_details)
            
            layout.label("Decimal Places:")
            layout.same_line()
            if layout.button("-##dec", (24 * scale, 0)):
                self._decimals = max(1, self._decimals - 1)
            layout.same_line()
            layout.label(str(self._decimals))
            layout.same_line()
            if layout.button("+##dec", (24 * scale, 0)):
                self._decimals = min(6, self._decimals + 1)
            
            layout.spacing()
            if layout.button("Clear All Measurements", (-1, 0)):
                store.clear_all()
                self._status_msg = "All measurements cleared"
                self._status_is_error = False
        
        # === Status ===
        if self._status_msg:
            layout.spacing()
            color = (1.0, 0.4, 0.4, 1.0) if self._status_is_error else (0.4, 1.0, 0.4, 1.0)
            layout.text_colored(self._status_msg, color)
