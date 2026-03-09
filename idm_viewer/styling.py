# styling.py

import plotly.graph_objects as go

# Get the appropriate Plotly template based on theme
# The actual template will be set dynamically by the frontend
def themed_layout(**kwargs):
    # Start with None; plotly-theme.js will override in browser
    return go.Layout(template=None, **kwargs)


def main_colorscale():
    return "Viridis"
