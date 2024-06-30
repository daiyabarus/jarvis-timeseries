import streamlit as st

# TAG: Page configuration
# TAG: add margin page


# This function sets the page configuration.
def page_config():
    st.set_page_config(
        page_title="JARVIS",
        layout="wide",
        page_icon="assets/signaltower.png",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
                <style>
                [data-testid="collapsedControl"] {
                        display: none;
                    }
                .appview-container .main .block-container {
                    padding-top: 1px;
                    padding-left: 1rem;
                    padding-right: 1rem;
                    padding-bottom: 1rem;
                }
                </style>
                """,
        unsafe_allow_html=True,
    )
