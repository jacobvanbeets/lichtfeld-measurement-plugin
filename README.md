# Measurement Tool Plugin for LichtFeld Studio

A 3D measurement tool plugin for measuring distances between points on Gaussian Splats.

## Features

- **Point Picking**: Click on the model to place measurement points
- **Point Adjustment**: Use native transform gizmos to drag and fine-tune point positions
- **3D Visualization**: See measurements overlaid on the 3D view with lines and distance labels
- **Multiple Measurements**: Create and manage multiple measurements simultaneously
- **Detailed Coordinates**: View exact X, Y, Z coordinates and deltas
- **Visibility Control**: Toggle visibility of individual measurements
- **Step Adjustment**: Fine-tune points with +/- buttons at configurable step sizes

## Usage

1. Open the **Measurement** panel in the sidebar
2. Click **+ New Measurement** to create a new measurement
3. Click **Pick Point 1** and click on the model to place the first point
4. Click **Pick Point 2** and click on the model to place the second point
5. The distance will be displayed in the panel and as an overlay in the 3D view

## Controls

- **Left Click**: Place a point when in picking mode
- **ESC / Right Click**: Cancel picking mode
- **Enable P1/P2 Gizmo**: Activate a 3D transform gizmo to drag and adjust the point position
- **+/- buttons**: Nudge points along X, Y, or Z axes by the selected step size
- **Flash**: Briefly highlight a measurement in the viewport
- **Hide/Show**: Toggle measurement visibility
- **Delete**: Remove a measurement

## Installation

Copy this plugin folder to your LichtFeld Studio plugins directory.

## License

GPL-3.0-or-later
