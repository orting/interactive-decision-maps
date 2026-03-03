import numpy as np
import pandas as pd
import base64, io
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
from dash.dependencies import ALL
from dash.exceptions import PreventUpdate

# =========================
# App
# =========================
app = Dash(__name__, suppress_callback_exceptions=True)

# =========================
# Utils
# =========================

def strip_prefix(name: str) -> str:
    if name.startswith('param_'):
        return name[len('param_'):]
    if name.startswith('metric_'):
        return name[len('metric_'):]
    return name


def fmt_sci(val):
    try:
        f = float(val)
        return f"{f:.10e}"  # scientific notation, up to 10 decimals
    except Exception:
        return str(val)

# =========================
# Data helpers
# =========================

def parse_uploaded_csv(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    param_cols = [c for c in df.columns if c.startswith('param_')]
    metric_cols = [c for c in df.columns if c.startswith('metric_')]
    if len(metric_cols) == 0:
        raise ValueError("No metric_ columns found in the CSV file.")
    F = df[metric_cols].to_numpy()
    return df, F, metric_cols, param_cols


def pareto_front(F: np.ndarray) -> np.ndarray:
    n = F.shape[0]
    mask = np.ones(n, dtype=bool)
    for i in range(n):
        if not mask[i]:
            continue
        dominated = np.all(F <= F[i], axis=1) & np.any(F < F[i], axis=1)
        mask[dominated] = False
    return mask


def pareto_front_2d(F2: np.ndarray) -> np.ndarray:
    idx = np.argsort(F2[:, 0])
    best = np.inf
    mask = np.zeros(F2.shape[0], dtype=bool)
    for i in idx:
        if F2[i, 1] < best:
            best = F2[i, 1]
            mask[i] = True
    return mask


def apply_ranges(F: np.ndarray, ranges):
    mask = np.ones(F.shape[0], dtype=bool)
    for k, (low, high) in enumerate(ranges):
        mask &= (F[:, k] >= low) & (F[:, k] <= high)
    return mask

# =========================
# Layout
# =========================
app.layout = html.Div([
    html.H2("Interactive Decision Map (IDM-style)"),
    html.Div(style={"display": "flex", "gap": "20px"}, children=[
        # LEFT COLUMN
        html.Div(style={"flex": "1", "minWidth": "320px"}, children=[
            dcc.Upload(
                id='upload',
                children=html.Div(['Drag CSV or ', html.A('Select')]),
                style={'border': '1px dashed #aaa', 'height': '60px', 'textAlign': 'center'}
            ),
            html.Div(id='fileinfo', style={'margin': '8px 0'}),

            # Stores
            dcc.Store(id='store'),
            dcc.Store(id='params'),
            dcc.Store(id='metrics'),
            dcc.Store(id='selected-index'),

            html.H4("Objective selection"),
            html.Label("X objective"),
            dcc.Dropdown(id='obj-x', options=[], value=None, clearable=False),
            html.Label("Y objective"),
            dcc.Dropdown(id='obj-y', options=[], value=None, clearable=False),

            html.H4("Brush (sliders apply to ALL metrics, including X/Y)"),
            html.Div(id='sliders'),

            html.H4("Point inspection"),
            html.Div(id='inspect', style={'border': '1px solid #aaa', 'padding': '8px', 'minHeight': '120px'})
        ]),

        # RIGHT COLUMN
        html.Div(style={"flex": "2"}, children=[
            dcc.Graph(id='scatter', style={'height': '520px', 'marginBottom': '12px'}),
            dcc.Graph(id='pcp', style={'height': '360px'})
        ])
    ])
])

# =========================
# Callbacks
# =========================

# Load CSV
@app.callback(
    Output('store', 'data'),
    Output('params', 'data'),
    Output('metrics', 'data'),
    Output('fileinfo', 'children'),
    Input('upload', 'contents')
)
def load(contents):
    if contents is None:
        raise PreventUpdate
    df, F, metrics, param_cols = parse_uploaded_csv(contents)
    # Normalize metrics to [0,1]
    Fmin, Fmax = F.min(axis=0), F.max(axis=0)
    Fnorm = (F - Fmin) / (Fmax - Fmin + 1e-12)
    pf = pareto_front(Fnorm).tolist()
    return {
        'F': Fnorm.tolist(),
        'pf': pf,
        'df': df.to_dict('records')
    }, param_cols, metrics, f"Loaded {len(df)} rows, {len(metrics)} metrics, {len(param_cols)} parameters."


# Build objective selectors + metric sliders (display names without prefixes)
@app.callback(
    Output('obj-x', 'options'),
    Output('obj-y', 'options'),
    Output('sliders', 'children'),
    Input('metrics', 'data')
)

def build_controls(metrics):
    if metrics is None:
        raise PreventUpdate
    options = [{'label': strip_prefix(m), 'value': i} for i, m in enumerate(metrics)]
    sliders = []
    for i, m in enumerate(metrics):
        sliders.append(html.Div([
            html.Label(strip_prefix(m)),
            dcc.RangeSlider(id={'type': 'sld', 'index': i}, min=0, max=1, step=0.01, value=[0, 1])
        ], style={'margin': '6px 0'}))
    return options, options, sliders


# Update plots — include selected-index input for instant highlight
@app.callback(
    Output('scatter', 'figure'),
    Output('pcp', 'figure'),
    Input('obj-x', 'value'),
    Input('obj-y', 'value'),
    Input('store', 'data'),
    Input('params', 'data'),
    Input('metrics', 'data'),
    Input({'type': 'sld', 'index': ALL}, 'value'),
    Input('selected-index', 'data')
)

def update_plots(objx, objy, data, param_cols, metrics, slvals, selected):
    if data is None or metrics is None or objx is None or objy is None or objx == objy:
        return go.Figure(), go.Figure()

    F = np.array(data['F'])
    df = pd.DataFrame(data['df'])
    pf = np.array(data['pf'])

    ranges = slvals[:len(metrics)] if slvals else [[0, 1]] * len(metrics)
    mask = apply_ranges(F, ranges)

    Fs = F[mask]
    dfs = df[mask]
    pfs = pf[mask]
    if len(Fs) == 0:
        fig_empty = go.Figure(); fig_empty.update_layout(title='No points within current brush ranges.')
        return fig_empty, go.Figure()

    # ---- Scatter (X/Y metrics) ----
    F2 = Fs[:, [objx, objy]]
    local_pf = pareto_front_2d(F2)

    # Hover text should show **metric values only** (no parameters), formatted with stripped names
    hover = []
    for idx, row in dfs.iterrows():
        lines = []
        for k, m in enumerate(metrics):
            # Only include metrics in hover; display stripped names and current normalized values
            lines.append(f"{strip_prefix(m)}: {fmt_sci(Fs[dfs.index.get_loc(idx), k])}")
        hover.append('<br>'.join(lines))

    figS = go.Figure()
    # Base: all brushed points (grey) — ONLY this trace shows hover text
    figS.add_trace(
        go.Scatter(
            x=F2[:, 0], y=F2[:, 1], mode='markers',
            marker=dict(size=6, color='lightgray'),
            name='Brushed points', text=hover, hoverinfo='text',
            customdata=dfs.index.astype(int).tolist()
        )
    )

    # Global PF: disable hover popups
    if pfs.any():
        G = F2[pfs]
        figS.add_trace(go.Scatter(
            x=G[:, 0], y=G[:, 1], mode='markers', marker=dict(size=8, color='red'),
            name='Global PF', hoverinfo='skip'
        ))

    # Local 2D PF: disable hover popups
    P = F2[local_pf]
    order = np.argsort(P[:, 0])
    P = P[order]
    figS.add_trace(go.Scatter(
        x=P[:, 0], y=P[:, 1], mode='lines+markers', marker=dict(size=7),
        name='Local 2D PF', hoverinfo='skip'
    ))

    # Selected point: disable hover popups
    if selected is not None:
        sel_pos = np.where(dfs.index.values == selected)[0]
        if len(sel_pos) == 1:
            i = sel_pos[0]
            figS.add_trace(go.Scatter(
                x=[F2[i, 0]], y=[F2[i, 1]], mode='markers',
                marker=dict(size=12, color='blue', line=dict(color='white', width=1)),
                name='Selected', hoverinfo='skip'
            ))

    figS.update_layout(
        title=f"{strip_prefix(metrics[objx])} vs {strip_prefix(metrics[objy])}",
        xaxis_title=strip_prefix(metrics[objx]), yaxis_title=strip_prefix(metrics[objy])
    )

    # ---- Parallel Coordinates (brushed subset across all metrics) ----
    dims = []
    for k, m in enumerate(metrics):
        dim = dict(label=strip_prefix(m), range=[0, 1], values=Fs[:, k])
        dim['constraintrange'] = [ranges[k][0], ranges[k][1]]
        dims.append(dim)

    # Color lines: selected line blue, else PF red
    if selected is not None:
        color = [1 if dfs.index.values[i] == selected else 0 for i in range(len(dfs))]
        colorscale = [[0, 'lightgray'], [1, 'blue']]
    else:
        color = (pfs.astype(int)).tolist()
        colorscale = [[0, 'lightgray'], [1, 'red']]

    figP = go.Figure(data=go.Parcoords(
        line=dict(color=color, colorscale=colorscale, cmin=0, cmax=1),
        dimensions=dims
    ))
    figP.update_layout(margin=dict(l=30, r=30, t=20, b=20))

    return figS, figP


# Click in scatter → select point
@app.callback(
    Output('selected-index', 'data'),
    Input('scatter', 'clickData')
)

def set_selected(clickData):
    if clickData is None:
        return None
    pt = clickData['points'][0]
    if pt.get('curveNumber') != 0:  # only grey base trace selectable
        return None
    return int(pt['customdata'])


# Inspection panel with formatted values (scientific notation, <=10 decimals) and stripped names
@app.callback(
    Output('inspect', 'children'),
    Input('selected-index', 'data'),
    State('store', 'data'), State('params', 'data'), State('metrics', 'data')
)

def inspect(idx, data, param_cols, metrics):
    if idx is None:
        return "Click a grey point to inspect values."
    df = pd.DataFrame(data['df'])
    if idx not in df.index:
        return "Selected point is outside current brush."
    row = df.loc[idx]
    param_items = [html.Li(f"{strip_prefix(p)}: {fmt_sci(row[p])}") for p in param_cols]
    metric_items = [html.Li(f"{strip_prefix(m)}: {fmt_sci(row[m])}") for m in metrics]
    return html.Div([
        html.H5('Parameters'), html.Ul(param_items),
        html.H5('Metrics'), html.Ul(metric_items)
    ])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
