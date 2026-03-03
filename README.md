# Interactive Decision Map (IDM-style)

## How to interpret the plots
### Scatter Plot
Shows a **2D slice** of the objective space defined by your chosen X/Y objectives. Grey = slice points, Red = global PF, Blue = local 2D PF.

### Parallel Coordinates Plot
Each vertical axis is a **metric**. Each polyline is **one solution** in the slice. Lines near the bottom (0) are better; crossings show **trade-offs**.
- Grey line = slice point
- Blue line = currently selected point
- Red (in earlier view) = global PF membership

### Inspection Window
Click a grey slice point to see full parameter + metric values.

### Brushing
Drag on the PCP axes to define ranges. The scatter plot will update to show only points whose metric values fall within brushed intervals.

## Run
```
python idm_viewer.py
```
App at http://0.0.0.0:8050
