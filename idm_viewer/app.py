from dash import Dash
from idm_viewer.layout import layout

def create_app():
    """
    Factory function that creates and configures the Dash app.
    Callbacks are registered AFTER the app is created to avoid circular imports.
    """
    app = Dash(
        __name__,
        suppress_callback_exceptions=True
    )
    app.layout = layout
    return app


def main():
    """
    Entry point for the idm-viewer CLI command.
    """
    app = create_app()

    # ---- IMPORTANT ----
    # Import AFTER app is created (prevents circular imports)
    from idm_viewer import callbacks
    callbacks.register_callbacks(app)

    # Run server
    app.run(host="0.0.0.0", port=8050, debug=False)


# Allow running directly with: python app.py
if __name__ == "__main__":
    main()
