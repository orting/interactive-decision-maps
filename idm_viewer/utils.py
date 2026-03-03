def strip_prefix(name):
    if name.startswith("param_"):
        return name[6:]
    if name.startswith("metric_"):
        return name[7:]
    return name

def fmt_sci(val):
    try:
        f = float(val)
        return f"{f:.10e}"
    except Exception:
        return str(val)
