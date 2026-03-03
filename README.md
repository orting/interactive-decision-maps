# Interactive Decision Map (IDM‑style)

This viewer lets you explore multi‑objective datasets with **slider‑based brushing** across *all* metrics, a 2D scatter for any metric pair, and a **Parallel Coordinates** view. Click a point in the scatter to inspect its parameter + metric values; the corresponding line in PCP is highlighted immediately.

## How to interpret each plot

### Scatter Plot (right, top)
- X and Y axes: your selected `metric_*` columns (normalized to [0,1], lower is better).
- **Grey** points: all **brushed** points (i.e., those within the slider ranges across all metrics).
- **Red** points: brushed points that are also on the **global Pareto front** in the full metric space.
- **Blue line**: **local 2D Pareto front** within the brushed subset for the selected (X,Y) metrics.
- **Blue dot**: the **clicked/selected** point.

### Parallel Coordinates (right, bottom)
- One vertical axis per `metric_*`; values are normalized to [0,1] (lower is better).
- **Grey lines**: all brushed points.
- **Red lines** (when no point is selected): lines that are globally Pareto‑optimal.
- **Blue line**: the currently **selected** point (if any).
- Axis shading (constraint range) reflects your **slider brush** per metric.

### Inspection Window (left)
- Shows **param_*** (parameters) and **metric_*** (metrics) for the selected point.

## Slider‑based brushing (recommended)
Use the sliders (left column) to **constrain every metric’s range**. The constraints are applied to *all* points before plotting, so both the scatter and PCP show only the brushed subset. This gives you reliable, responsive brushing without relying on PCP’s internal (non‑exposed) events.

## Run
```bash
python idm_viewer.py
```
App runs at: http://0.0.0.0:8050
