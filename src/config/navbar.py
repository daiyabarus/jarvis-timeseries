# navbar.py
from streamlit_navigation_bar import st_navbar

# TAG: navbar is configuration for the navigation bar


def navbar():
    pages = ["Dashboard", "Database", "Jarvis", "Wiki", "GitHub"]
    urls = {"GitHub": "https://github.com/daiyabarus/jarvis-timeseries"}

    styles = {
        "nav": {
            "background-color": "#E60000",
            "justify-content": "center",
        },
        "img": {
            "padding-right": "12px",
        },
        "span": {
            "color": "white",
            "padding": "12px",
            "font-family": "Ericsson Hilda Light",
        },
        "active": {
            "background-color": "white",
            "color": "black",
            "font-weight": "normal",
            "padding": "14px",
            "border": "1px",
            "border-radius": "10px",
        },
    }
    options = {
        "show_menu": True,
        "show_sidebar": True,
    }

    page = st_navbar(
        pages,
        urls=urls,
        styles=styles,
        options=options,
    )

    return page
