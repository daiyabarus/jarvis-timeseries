import os

import streamlit as st
from utils.ui import set_page_width


def wiki():
    set_page_width(1200)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    assets_dir = os.path.join(project_root, "assets")

    def safe_image_load(image_name, width=100):
        try:
            image_path = os.path.join(assets_dir, image_name)
            if os.path.exists(image_path):
                return st.image(image_path, width=width)
            else:
                st.warning(f"Image not found: {image_name}")
        except Exception as e:
            st.error(f"Error loading image {image_name}: {e!s}")

    cols = st.columns(4)
    icons = [
        "icon2g.png",
        "icon3g.png",
        "icon4g.png",
        "icon5g.png",
    ]
    for col, icon in zip(cols, icons):
        with col.container(border=False):
            safe_image_load(icon)

    st.divider()
    st.markdown(
        """
    # FLOWCHART JARVIS

     """
    )

    # Load the flowchart image
    safe_image_load("svg/Jarvis.svg", width=600)

    st.divider()
    st.markdown(
        """
    # FLOWCHART DASHBOARD

     """
    )

    # Load the flowchart image
    safe_image_load("svg/Dashboard_flow.svg", width=600)

    st.divider()
