from dash import dcc
import pandas as pd

def export_brushed(store):
    df = pd.DataFrame(store["df"])
    return dcc.send_data_frame(df.to_csv,
        filename="brushed_subset.csv",
        index=False)
