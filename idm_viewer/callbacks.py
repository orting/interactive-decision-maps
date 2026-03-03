import numpy as np
import pandas as pd
from dash import Input, Output, State, dcc, html
from dash.dependencies import ALL
from dash.exceptions import PreventUpdate

from idm_viewer.data import (
    parse_csv,
    normalize,
    pareto_front,
    pareto_front_2d,
    apply_ranges,
)
from idm_viewer.utils import strip_prefix, fmt_sci
from idm_viewer.styling import template, main_colorscale
from idm_viewer.exporters import export_brushed


def register_callbacks(app):

    # ---------------------- LOAD CSV ----------------------
    @app.callback(
        Output("store", "data"),
        Output("store-raw", "data"),
        Output("params", "data"),
        Output("metrics", "data"),
        Output("fileinfo", "children"),
        Input("upload", "contents")
    )
    def load(contents):
        # SAFETY: first app load -> contents is None
        if contents is None:
            raise PreventUpdate

        df, F_raw, metrics, params = parse_csv(contents)
        F_norm = normalize(F_raw)
        pf = pareto_front(F_norm).tolist()

        return (
            {"F": F_norm.tolist(), "pf": pf, "df": df.to_dict("records")},
            {"F_raw": F_raw.tolist(), "metrics": metrics, "params": params},
            params,
            metrics,
            f"Loaded {len(df)} rows"
        )

    # ---------------------- BUILD CONTROLS ----------------------
    @app.callback(
        Output("obj-x", "options"),
        Output("obj-y", "options"),
        Output("sliders", "children"),
        Output("color-by", "options"),
        Input("metrics", "data"),
        Input("params", "data")
    )
    def build_controls(metrics, params):
        # SAFETY: both inputs may be None on first render
        if metrics is None or params is None:
            raise PreventUpdate

        metric_opts = [{"label": strip_prefix(m), "value": m} for m in metrics]
        param_opts  = [{"label": strip_prefix(p), "value": p} for p in params]
        color_opts = metric_opts + param_opts

        obj_opts = [{"label": strip_prefix(m), "value": i} for i, m in enumerate(metrics)]

        sliders = []
        for i, m in enumerate(metrics):
            sliders.append(
                html.Div([
                    html.Label(strip_prefix(m)),
                    dcc.RangeSlider(
                        id={"type": "sld", "index": i},
                        min=0, max=1, step=0.01, value=[0, 1]
                    )
                ], style={"margin": "6px 0"})
            )

        return obj_opts, obj_opts, sliders, color_opts

    # ---------------------- DOWNLOAD BRUSHED SUBSET ----------------------
    @app.callback(
        Output("download-brushed", "data"),
        Input("download-btn", "n_clicks"),
        State("store", "data"),
        prevent_initial_call=True
    )
    def download(n, store):
        # SAFETY: if user clicks instantly before data is present
        if store is None or "df" not in store:
            raise PreventUpdate
        return export_brushed(store)

    # ---------------------- UPDATE PLOTS ----------------------
    @app.callback(
        Output("scatter", "figure"),
        Output("pcp", "figure"),
        Input("obj-x", "value"),
        Input("obj-y", "value"),
        Input("store", "data"),
        Input("store-raw", "data"),
        Input("params", "data"),
        Input("metrics", "data"),
        Input({"type": "sld", "index": ALL}, "value"),
        Input("selected-index", "data"),
        Input("color-by", "value"),
        Input("theme", "value")
    )
    def update_plots(objx, objy, store, raw, params, metrics,
                     slider_vals, selected, colorby, theme):

        # SAFETY: early renders before upload/selection
        if store is None or metrics is None or objx is None or objy is None:
            raise PreventUpdate

        F = np.array(store["F"])
        df = pd.DataFrame(store["df"])
        pf = np.array(store["pf"])

        # Brushed subset (sliders can be None on very first run)
        ranges = slider_vals[:len(metrics)] if slider_vals else [[0, 1]] * len(metrics)
        mask = apply_ranges(F, ranges)
        Fs = F[mask]
        df_s = df[mask]
        pf_s = pf[mask]

        if len(Fs) == 0:
            # Nothing to show; avoid clearing existing figures
            raise PreventUpdate

        # ---- Color-by (normalized)
        if colorby in metrics:
            col_values = Fs[:, metrics.index(colorby)]
        elif colorby in params:
            vals = df_s[colorby].astype(float).values
            mn, mx = vals.min(), vals.max()
            col_values = (vals - mn) / (mx - mn + 1e-12)
        else:
            col_values = np.zeros(len(Fs))
        colorscale = main_colorscale()

        # ---- Scatter
        F2 = Fs[:, [objx, objy]]
        local_pf = pareto_front_2d(F2)

        hover = []
        for rid, row in df_s.iterrows():
            lines = []
            for k, m in enumerate(metrics):
                val = fmt_sci(Fs[df_s.index.get_loc(rid), k])
                lines.append(f"{strip_prefix(m)}: {val}")
            hover.append("<br>".join(lines))

        scatter = {
            "data": [
                {
                    "x": F2[:, 0], "y": F2[:, 1],
                    "mode": "markers",
                    "marker": {"size": 7, "color": col_values, "colorscale": colorscale},
                    "name": "Brushed",
                    "text": hover, "hoverinfo": "text",
                    "customdata": df_s.index.astype(int).tolist(),
                }
            ],
            "layout": {
                "template": template(theme),
                "title": f"{strip_prefix(metrics[objx])} vs {strip_prefix(metrics[objy])}",
                "xaxis": {"title": strip_prefix(metrics[objx])},
                "yaxis": {"title": strip_prefix(metrics[objy])},
            }
        }

        # Global PF
        if pf_s.any():
            G = F2[pf_s]
            scatter["data"].append({
                "x": G[:, 0], "y": G[:, 1],
                "mode": "markers",
                "marker": {"size": 10, "color": "red"},
                "name": "Global PF",
                "hoverinfo": "skip"
            })

        # Local 2D PF
        LP = F2[pareto_front_2d(F2)]
        order = np.argsort(LP[:, 0])
        LP = LP[order]
        scatter["data"].append({
            "x": LP[:, 0], "y": LP[:, 1],
            "mode": "lines+markers",
            "marker": {"size": 7, "color": "blue"},
            "name": "Local PF",
            "hoverinfo": "skip"
        })

        # Selected point
        if selected is not None:
            pos = np.where(df_s.index.values == selected)[0]
            if len(pos) == 1:
                i = pos[0]
                scatter["data"].append({
                    "x": [F2[i, 0]], "y": [F2[i, 1]],
                    "mode": "markers",
                    "marker": {"size": 16, "color": "blue",
                               "line": {"color": "white", "width": 2}},
                    "name": "Selected",
                    "hoverinfo": "skip"
                })

        # ---- PCP
        dims = []
        for k, m in enumerate(metrics):
            dims.append(dict(
                label=strip_prefix(m),
                range=[0, 1],
                values=Fs[:, k],
                constraintrange=ranges[k]
            ))

        pcp = {
            "data": [
                {
                    "type": "parcoords",
                    "line": {
                        "color": col_values,
                        "colorscale": colorscale,
                        "cmin": 0, "cmax": 1
                    },
                    "dimensions": dims
                }
            ],
            "layout": {"template": template(theme)}
        }

        # Selected line overlay
        if selected is not None:
            pos = np.where(df_s.index.values == selected)[0]
            if len(pos) == 1:
                pcp["data"].append({
                    "type": "parcoords",
                    "line": {"color": [1],
                             "colorscale": [[0, "blue"], [1, "blue"]]},
                    "dimensions": dims
                })

        return scatter, pcp

    # ---------------------- CLICK ON SCATTER ----------------------
    @app.callback(
        Output("selected-index", "data"),
        Input("scatter", "clickData")
    )
    def select_point(click):
        # SAFETY: no click yet
        if click is None:
            raise PreventUpdate
        pt = click["points"][0]
        if pt.get("curveNumber") != 0:
            # Only base (brushed) layer is selectable
            raise PreventUpdate
        return int(pt["customdata"])

    # ---------------------- INSPECTION PANEL ----------------------
    @app.callback(
        Output("inspect", "children"),
        Input("selected-index", "data"),
        State("store", "data"),
        State("params", "data"),
        State("metrics", "data")
    )
    def inspect_panel(idx, store, params, metrics):
        # Keep prior panel if no selection yet
        if idx is None or store is None:
            raise PreventUpdate

        df = pd.DataFrame(store["df"])
        if idx not in df.index:
            # selection no longer in brush -> keep existing panel
            raise PreventUpdate

        row = df.loc[idx]
        return html.Div([
            html.H5("Parameters"),
            html.Ul([html.Li(f"{strip_prefix(p)}: {fmt_sci(row[p])}") for p in params]),
            html.H5("Metrics"),
            html.Ul([html.Li(f"{strip_prefix(m)}: {fmt_sci(row[m])}") for m in metrics]),
        ])
