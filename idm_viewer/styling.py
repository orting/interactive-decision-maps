# styling.py

import plotly.graph_objects as go

# Simple layout helper — always template=None
def themed_layout(**kwargs):
    return go.Layout(template=None, **kwargs)


def main_colorscale():
    return "Viridis"
