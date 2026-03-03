import numpy as np
import pandas as pd
import base64, io
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
from dash.dependencies import ALL
from dash.exceptions import PreventUpdate

# =========================
# CSV Parsing
# =========================

def parse_uploaded_csv(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    param_cols = [c for c in df.columns if c.startswith('param_')]
    metric_cols = [c for c in df.columns if c.startswith('metric_')]

    if len(metric_cols) == 0:
        raise ValueError('No metric_ columns found in the CSV file.')

    F = df[metric_cols].to_numpy()
    labels = metric_cols

    return df, F, labels, param_cols

# =========================
# Pareto Utilities
# =========================

def pareto_front(F):
    n = F.shape[0]
    mask = np.ones(n, dtype=bool)
    for i in range(n):
        if not mask[i]:
            continue
        dominated = np.all(F <= F[i], axis=1) & np.any(F < F[i], axis=1)
        mask[dominated] = False
    return mask

def pareto_front_2d(F2):
    idx = np.argsort(F2[:, 0])
    best = np.inf
    mask = np.zeros(F2.shape[0], dtype=bool)
    for i in idx:
        if F2[i, 1] < best:
            best = F2[i, 1]
            mask[i] = True
    return mask

# =========================
# Slice Logic
# =========================

def slice_points(F, obj_i, obj_j, ranges):
    n_obj = F.shape[1]
    mask = np.ones(F.shape[0], dtype=bool)
    for k in range(n_obj):
        if k == obj_i or k == obj_j:
            continue
        low, high = ranges[k]
        mask &= (F[:, k] >= low) & (F[:, k] <= high)
    return mask

# =========================
# Dash App
# =========================

app = Dash(__name__, suppress_callback_exceptions=True)

app.layout = html.Div([
    html.H2("Interactive Decision Map (IDM-style)"),

    html.Div(style={"display": "flex", "flex-direction": "row", "gap": "20px"}, children=[

        # LEFT COLUMN
        html.Div(style={"flex": "1", "min-width": "320px"}, children=[

            dcc.Upload(
                id='upload-data',
                children=html.Div(['Drag and drop or ', html.A('Select CSV File')]),
                style={
                    'width': '100%', 'height': '60px', 'lineHeight': '60px',
                    'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                    'textAlign': 'center', 'margin-bottom': '20px'
                },
                multiple=False
            ),
            html.Div(id='file-info'),

            dcc.Store(id='data-store'),
            dcc.Store(id='params-store'),
            dcc.Store(id='labels-store'),

            html.H4("Objective selection"),
            html.Label("X-axis objective"),
            dcc.Dropdown(id='obj-x', options=[], value=None, clearable=False),
            html.Label("Y-axis objective"),
            dcc.Dropdown(id='obj-y', options=[], value=None, clearable=False),

            html.H4("Slice ranges"),
            html.Div(id='slider-container'),

            html.H4("Point inspection"),
            html.Div(id='inspection-window', style={
                "border": "1px solid #aaa",
                "padding": "10px",
                "margin-top": "10px",
                "background": "#fafafa",
                "min-height": "120px"
            }),
        ]),

        # RIGHT COLUMN
        html.Div(style={"flex": "2"}, children=[
            dcc.Graph(id='slice-plot', style={'height': '900px'})
        ])
    ])
])

# =========================
# Callbacks
# =========================

@app.callback(
    Output('data-store', 'data'),
    Output('params-store', 'data'),
    Output('labels-store', 'data'),
    Output('file-info', 'children'),
    Input('upload-data', 'contents')
)
def load_csv(contents):
    if contents is None:
        raise PreventUpdate

    df, F, labels, param_cols = parse_uploaded_csv(contents)
    Fmin, Fmax = F.min(axis=0), F.max(axis=0)
    F_norm = (F - Fmin) / (Fmax - Fmin + 1e-12)
    global_pf = pareto_front(F_norm).tolist()

    return (
        {
            'F_norm': F_norm.tolist(),
            'global_pf': global_pf,
            'df': df.to_dict('records')
        },
        param_cols,
        labels,
        f"Loaded file with {len(df)} rows, {len(labels)} metric columns, {len(param_cols)} parameter columns."
    )

@app.callback(
    Output('obj-x', 'options'),
    Output('obj-y', 'options'),
    Output('slider-container', 'children'),
    Input('labels-store', 'data')
)
def update_selectors(labels):
    if labels is None:
        raise PreventUpdate
    options = [{'label': l, 'value': i} for i, l in enumerate(labels)]
    sliders = []
    for i, label in enumerate(labels):
        sliders.append(html.Div([
            html.Label(f"{label} range"),
            dcc.RangeSlider(id={'type': 'metric-slider', 'index': i}, min=0, max=1, step=0.01, value=[0, 1])
        ], style={'margin': '10px 0'}))
    return options, options, sliders

@app.callback(
    Output('slice-plot', 'figure'),
    Input('obj-x', 'value'),
    Input('obj-y', 'value'),
    Input('data-store', 'data'),
    Input('params-store', 'data'),
    Input('labels-store', 'data'),
    Input({'type': 'metric-slider', 'index': ALL}, 'value')
)
def update_plot(obj_x, obj_y, data, param_cols, labels, slider_values):
    if data is None or labels is None:
        raise PreventUpdate
    if obj_x is None or obj_y is None or obj_x == obj_y:
        fig = go.Figure()
        fig.update_layout(title='Select two different objectives.')
        return fig

    F_norm = np.array(data['F_norm'])
    df = pd.DataFrame(data['df'])
    global_pf = np.array(data['global_pf'])

    ranges = slider_values[: len(labels)]
    ranges = [(low, high) for (low, high) in ranges]

    mask = slice_points(F_norm, obj_x, obj_j=obj_y, ranges=ranges)
    F_slice = F_norm[mask]
    df_slice = df[mask]

    if len(F_slice) == 0:
        fig = go.Figure()
        fig.update_layout(title='No points in slice.')
        return fig

    F2 = F_slice[:, [obj_x, obj_y]]
    local_pf = pareto_front_2d(F2)
    global_pf_slice = global_pf[mask]

    # Hover text: parameters only
    hovertext = [
        '<br>'.join([f"{c}: {row[c]}" for c in param_cols])
        for _, row in df_slice[param_cols].iterrows()
    ]

    # Slice scatter with robust customdata
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=F2[:,0], y=F2[:,1], mode='markers',
        marker=dict(size=6, color='lightgray'),
        name='Slice points', text=hovertext, hoverinfo='text',
        customdata=df_slice.index.astype(int).tolist()
    ))

    # Global PF
    if any(global_pf_slice):
        G = F2[global_pf_slice]
        fig.add_trace(go.Scatter(
            x=G[:,0], y=G[:,1],
            mode='markers', marker=dict(size=8, color='red'), name='Global PF'
        ))

    # Local PF
    PF = F2[local_pf]
    order = np.argsort(PF[:,0])
    PF = PF[order]
    fig.add_trace(go.Scatter(
        x=PF[:,0], y=PF[:,1], mode='lines+markers', marker=dict(size=7), name='Local PF'
    ))

    fig.update_layout(title=f"{labels[obj_x]} vs {labels[obj_y]}", xaxis_title=labels[obj_x], yaxis_title=labels[obj_y])
    return fig

# =========================
# Point Inspection Window
# =========================

@app.callback(
    Output('inspection-window', 'children'),
    Input('slice-plot', 'clickData'),
    Input('data-store', 'data'),
    Input('params-store', 'data'),
    Input('labels-store', 'data')
)
def show_details(clickData, data, param_cols, metric_cols):
    if clickData is None or data is None:
        return "Click a grey slice point to inspect its values."

    point = clickData['points'][0]

    # Accept only clicks on trace 0 (slice points)
    if point.get('curveNumber', None) != 0:
        return "Click a grey slice point to inspect its values."

    if 'customdata' not in point:
        return "Click a grey slice point to inspect its values."

    row_index = int(point['customdata'])

    df = pd.DataFrame(data['df'])
    row = df.loc[row_index]

    return html.Div([
        html.H5("Parameters"),
        html.Ul([html.Li(f"{p}: {row[p]}") for p in param_cols]),

        html.H5("Metrics"),
        html.Ul([html.Li(f"{m}: {row[m]}") for m in metric_cols])
    ])

# =========================
# Main
# =========================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
