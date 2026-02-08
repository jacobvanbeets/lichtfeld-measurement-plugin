# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

A LichtFeld Studio plugin that provides 3D measurement tools for Gaussian Splat models. Users can pick points on the model and measure distances between them with visual overlays.

## Development

This plugin is loaded directly by LichtFeld Studio. There is no separate build step.

- **Install**: Copy the plugin folder to LichtFeld Studio's plugins directory
- **Hot reload**: Enabled via `pyproject.toml` - changes reload automatically during development
- **Minimum LichtFeld version**: 0.5.0
- **Dependencies**: numpy (handled by LichtFeld)

No linting or test infrastructure is currently configured.

## Architecture

### Plugin Registration Pattern

Plugins use `on_load()` / `on_unload()` entry points in `__init__.py`. Classes (Panels, Operators) must be registered via `lf.register_class()` at load time and unregistered in reverse order on unload.

### Module Structure

- **`core/`** - Data structures and business logic
  - `measurement.py` - `Measurement` dataclass and `MeasurementStore` singleton that manages all measurement state
  
- **`operators/`** - Modal operators for user interactions
  - `measure_picker.py` - `MEASURE_OT_pick_point` operator handles point picking via modal input events; uses module-level callbacks to communicate with the panel
  
- **`panels/`** - UI panels
  - `measurement_panel.py` - `MeasurementPanel` renders the sidebar UI; also owns the 3D draw handler (`_measurement_draw_handler`) for rendering measurement overlays

- **`tools/`** - Reserved for future tool implementations

### Key Patterns

**Global singleton store**: `MeasurementStore` instance accessed via `get_measurement_store()`. All measurement state lives here.

**Operator-Panel communication**: The modal picker operator uses module-level callbacks (`set_pick_callback`, `_pending_pick`) rather than direct function calls since the operator and panel have different lifecycles.

**Draw handler registration**: The panel lazily registers a single named draw handler (`"measurement_overlay"`) via `lf.add_draw_handler()`. The handler is called each frame and receives a drawing context for 2D/3D primitives.

### LichtFeld API Usage

```python
import lichtfeld as lf
import lichtfeld.selection as sel
from lfs_plugins.types import Panel, Operator, Event
```

- `lf.register_class()` / `lf.unregister_class()` - Class registration
- `lf.add_draw_handler()` / `lf.remove_draw_handler()` - Overlay rendering
- `lf.has_scene()` - Check if a scene is loaded (used in panel polling)
- `lf.ui.request_redraw()` - Request UI refresh
- `lf.ui.ops.invoke()` - Invoke operators
- `sel.pick_at_screen()` - Raycast to model at screen coordinates
- `lf.log.info()` - Logging

### Operator Conventions

Operators inherit from `lfs_plugins.types.Operator` and follow Blender-style conventions:
- `label`, `description`, `options` class attributes
- `invoke()` to start, `modal()` for event handling, `cancel()` for cleanup
- Return sets: `{'RUNNING_MODAL'}`, `{'CANCELLED'}`, `{'FINISHED'}`
