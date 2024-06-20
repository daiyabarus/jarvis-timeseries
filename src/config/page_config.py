import streamlit as st

# TAG: Page configuration


# This function sets the page configuration.
def page_config():
    st.set_page_config(
        page_title="JARVIS",
        layout="wide",
        page_icon="assets/signaltower.png",
        initial_sidebar_state="expanded",
    )
