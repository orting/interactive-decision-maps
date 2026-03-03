import numpy as np
import pandas as pd
import base64, io

def parse_csv(contents):
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
    params = [c for c in df.columns if c.startswith("param_")]
    metrics = [c for c in df.columns if c.startswith("metric_")]
    F_raw = df[metrics].to_numpy()
    return df, F_raw, metrics, params

def normalize(F_raw):
    Fmin = F_raw.min(axis=0)
    Fmax = F_raw.max(axis=0)
    return (F_raw - Fmin) / (Fmax - Fmin + 1e-12)

def pareto_front(F):
    n = F.shape[0]
    mask = np.ones(n, dtype=bool)
    for i in range(n):
        if not mask[i]: continue
        dominated = np.all(F <= F[i], axis=1) & np.any(F < F[i], axis=1)
        mask[dominated] = False
    return mask

def pareto_front_2d(F2):
    idx = np.argsort(F2[:,0])
    best = np.inf
    mask = np.zeros(F2.shape[0], bool)
    for i in idx:
        if F2[i,1] < best:
            best = F2[i,1]
            mask[i] = True
    return mask

def apply_ranges(F, ranges):
    mask = np.ones(len(F), dtype=bool)
    for i,(lo,hi) in enumerate(ranges):
        mask &= (F[:,i] >= lo) & (F[:,i] <= hi)
    return mask
