# SPDX-FileCopyrightText: 2025 LichtFeld Studio Authors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Measurement Panel with 3D visualization."""

import time as _time
import math as _math

import lichtfeld as lf

from ..core.measurement import get_measurement_store, Measurement
from ..operators.measure_picker import set_pick_callback, clear_pick_callback, was_pick_cancelled


# Module-level state for draw handler
_draw_handler_registered = False
_picking_state = {
    'picking_point': 0,  # 0 = not picking, 1 = picking point 1, 2 = picking point 2
    'status_msg': '',
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


def _draw_measurement(ctx, m: Measurement):
    """Draw a single measurement."""
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
    
    # Draw Point 1
    if m.point1 is not None:
        ctx.draw_point_3d(m.point1, color, point_size)
        screen1 = ctx.world_to_screen(m.point1)
        if screen1:
            ctx.draw_circle_2d(screen1, 12.0, color, 2.0)
            ctx.draw_text_2d((screen1[0] + 15, screen1[1] - 8), "P1", color)
    
    # Draw Point 2
    if m.point2 is not None:
        ctx.draw_point_3d(m.point2, color, point_size)
        screen2 = ctx.world_to_screen(m.point2)
        if screen2:
            ctx.draw_circle_2d(screen2, 12.0, color, 2.0)
            ctx.draw_text_2d((screen2[0] + 15, screen2[1] - 8), "P2", color)
    
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
    
    def draw(self, layout):
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
        
        # Ensure draw handler
        _ensure_draw_handler()
        
        # Update module-level state
        global _picking_state
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
