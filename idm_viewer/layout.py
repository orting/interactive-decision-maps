from dash import html, dcc

layout = html.Div([
    # Data stores
    dcc.Store(id="store"),
    dcc.Store(id="store-raw"),
    dcc.Store(id="params"),
    dcc.Store(id="metrics"),
    dcc.Store(id="selected-index"),
    dcc.Download(id="download-brushed"),

    html.H2("Interactive Decision Map (IDM-style)"),

    html.Div(style={"display":"flex","gap":"20px"}, children=[

        # LEFT COLUMN
        html.Div(style={"flex":"1","minWidth":"330px"}, children=[
            html.Label("Theme"),
            dcc.Dropdown(
                id="theme",
                options=[
                    {"label":"Light Mode","value":"light"},
                    {"label":"Dark Mode","value":"dark"},
                ],
                value="light",
                clearable=False
            ),

            dcc.Upload(
                id="upload",
                children=html.Div(["Drag CSV or ", html.A("Select")]),
                style={"border":"1px dashed #aaa",
                       "height":"60px","textAlign":"center"}
            ),
            html.Div(id="fileinfo"),

            html.H4("Objective selection"),
            html.Label("X objective"),
            dcc.Dropdown(id="obj-x"),
            html.Label("Y objective"),
            dcc.Dropdown(id="obj-y"),

            html.H4("Brush (sliders across all metrics)"),
            html.Div(id="sliders"),

            html.H4("Color by"),
            dcc.Dropdown(id="color-by"),

            html.Button("Download brushed subset", id="download-btn"),

            html.H4("Point inspection"),
            html.Div(id="inspect",
                     style={"border":"1px solid #aaa","padding":"8px"}),
        ]),

        # RIGHT COLUMN
        html.Div(style={"flex":"2"}, children=[
            dcc.Graph(id="scatter", style={"height":"520px"}),
            dcc.Graph(id="pcp", style={"height":"360px"})
        ])
    ])
])
