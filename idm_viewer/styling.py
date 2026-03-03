def is_dark(theme):
    return theme == "dark"

def template(theme):
    return "plotly_dark" if is_dark(theme) else "plotly_white"

def main_colorscale():
    return "Viridis"
