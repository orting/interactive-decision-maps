import numpy as np
import pandas as pd
import base64, io
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
from dash.dependencies import ALL
from dash.exceptions import PreventUpdate

app = Dash(__name__, suppress_callback_exceptions=True)

# CSV parsing

def parse_uploaded_csv(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    param_cols = [c for c in df.columns if c.startswith('param_')]
    metric_cols = [c for c in df.columns if c.startswith('metric_')]
    F = df[metric_cols].to_numpy()
    return df, F, metric_cols, param_cols

# Pareto utils

def pareto_front(F):
    n = F.shape[0]
    mask = np.ones(n, dtype=bool)
    for i in range(n):
        if not mask[i]: continue
        dominated = np.all(F <= F[i], 1) & np.any(F < F[i], 1)
        mask[dominated] = False
    return mask


def pareto_front_2d(F2):
    idx = np.argsort(F2[:,0]); best = np.inf
    mask = np.zeros(F2.shape[0], bool)
    for i in idx:
        if F2[i,1] < best:
            best = F2[i,1]; mask[i] = True
    return mask

# Slice

def slice_points(F, obj_x, obj_y, ranges):
    mask = np.ones(F.shape[0], bool)
    for k,(lo,hi) in enumerate(ranges):
        if k in (obj_x,obj_y): continue
        mask &= (F[:,k] >= lo) & (F[:,k] <= hi)
    return mask

# Layout
app.layout = html.Div([
 html.H2("Interactive Decision Map"),
 html.Div(style={'display':'flex','gap':'20px'},children=[
  html.Div(style={'flex':'1'},children=[
    dcc.Upload(id='upload',children=html.Div(['Drag CSV or ',html.A('Select')]),
               style={'border':'1px dashed #aaa','height':'60px','textAlign':'center'}),
    html.Div(id='fileinfo'),
    dcc.Store(id='store'),dcc.Store(id='params'),dcc.Store(id='metrics'),dcc.Store(id='selected-index'),
    html.Label("X objective"), dcc.Dropdown(id='obj-x'),
    html.Label("Y objective"), dcc.Dropdown(id='obj-y'),
    html.Div(id='sliders'),
    html.H4("Point inspection"),html.Div(id='inspect',style={'border':'1px solid #aaa','padding':'8px'})
  ]),
  html.Div(style={'flex':'2'},children=[
    dcc.Graph(id='scatter',style={'height':'520px'}),
    dcc.Graph(id='pcp',style={'height':'360px'})
  ])
 ])
])

# Load CSV
@app.callback(
 Output('store','data'),Output('params','data'),Output('metrics','data'),Output('fileinfo','children'),
 Input('upload','contents') )
def load(contents):
 if contents is None:
  raise PreventUpdate
 df,F,metrics,param_cols = parse_uploaded_csv(contents)
 Fmin,Fmax = F.min(0),F.max(0)
 Fnorm = (F-Fmin)/(Fmax-Fmin+1e-12)
 pf = pareto_front(Fnorm).tolist()
 return {'F':Fnorm.tolist(),'pf':pf,'df':df.to_dict('records')},param_cols,metrics,f"Loaded {len(df)} rows"

# Build selectors
@app.callback(
 Output('obj-x','options'),Output('obj-y','options'),Output('sliders','children'),
 Input('metrics','data') )
def sels(metrics):
 if metrics is None: raise PreventUpdate
 opts=[{'label':m,'value':i} for i,m in enumerate(metrics)]
 sliders=[ html.Div([html.Label(m), dcc.RangeSlider(id={'type':'sld','index':i},min=0,max=1,step=0.01,value=[0,1])]) for i,m in enumerate(metrics) ]
 return opts,opts,sliders

# Update both plots
@app.callback(
 Output('scatter','figure'),Output('pcp','figure'),
 Input('obj-x','value'),Input('obj-y','value'),Input('store','data'),Input('params','data'),Input('metrics','data'),
 Input({'type':'sld','index':ALL},'value'),State('selected-index','data') )
def update(objx,objy,data,param_cols,metrics,slvals,selected):
 if data is None or objx is None or objy is None or objx==objy:
  return go.Figure(),go.Figure()
 F=np.array(data['F']);df=pd.DataFrame(data['df']);pf=np.array(data['pf'])
 ranges=slvals[:len(metrics)]
 mask=slice_points(F,objx,objy,ranges)
 Fs=F[mask]; dfs=df[mask]; pfs=pf[mask]
 if len(Fs)==0: return go.Figure(),go.Figure()

 # Scatter
 F2=Fs[:,[objx,objy]]
 locpf=pareto_front_2d(F2)
 hover=[ '<br>'.join(f"{p}:{row[p]}" for p in param_cols) for _,row in dfs[param_cols].iterrows() ]
 figS=go.Figure()
 figS.add_trace(go.Scatter(x=F2[:,0],y=F2[:,1],mode='markers',marker=dict(size=6,color='lightgray'),
   text=hover,hoverinfo='text',customdata=dfs.index.astype(int).tolist(),name='Slice'))
 if pfs.any():
  G=F2[pfs]
  figS.add_trace(go.Scatter(x=G[:,0],y=G[:,1],mode='markers',marker=dict(size=8,color='red'),name='Global PF'))
 P=F2[locpf]
 ord=np.argsort(P[:,0]);P=P[ord]
 figS.add_trace(go.Scatter(x=P[:,0],y=P[:,1],mode='lines+markers',name='Local PF'))
 figS.update_layout(title=f"{metrics[objx]} vs {metrics[objy]}")

 # PCP
 dims=[ dict(label=m,range=[0,1],values=Fs[:,i]) for i,m in enumerate(metrics) ]

 # Color: highlight selected
 if selected is not None:
  col=[1 if dfs.index[i]==selected else 0 for i in range(len(dfs))]
 else:
  col=(pfs.astype(int)).tolist()

 figP=go.Figure(data=go.Parcoords(line=dict(color=col,colorscale=[[0,'lightgray'],[1,'blue']],cmin=0,cmax=1),dimensions=dims))
 return figS,figP

# Click highlight
@app.callback(Output('selected-index','data'),Input('scatter','clickData'))
def click(clickData):
 if clickData is None: return None
 pt=clickData['points'][0]
 if pt.get('curveNumber')!=0: return None
 return int(pt['customdata'])

# Inspect
@app.callback(Output('inspect','children'),Input('selected-index','data'),State('store','data'),State('params','data'),State('metrics','data'))
def inspect(idx,data,param_cols,metrics):
 if idx is None: return "Click slice point"
 df=pd.DataFrame(data['df']); row=df.loc[idx]
 return html.Div([
  html.H5('Parameters'),html.Ul([html.Li(f"{p}:{row[p]}") for p in param_cols]),
  html.H5('Metrics'),html.Ul([html.Li(f"{m}:{row[m]}") for m in metrics]) ])

if __name__=='__main__': app.run(host='0.0.0.0',port=8050,debug=True)