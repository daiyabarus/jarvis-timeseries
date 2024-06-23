import streamlit as st
import streamlit_antd_components as sac
from gsmdaily import gsm_daily_page
from ltedaily import lte_daily_page
from nrdaily import nr_daily_page


class DailyTabs:
    def __init__(self):
        self.setup_css()

    def setup_css(self):
        st.markdown("""
        <style>
        [data-testid="collapsedControl"] {
                display: none
            }
        #MainMenu, header, footer {visibility: hidden;}
        .appview-container .main .block-container
        {
            padding-top: 1px;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
            padding-bottom: 1px;
        }
        </style>
        """,unsafe_allow_html=True)

    def create_layout(self):
        col1, col2, col3, col4, col5 = st.columns(5)
        con1 = col1.container()
        con2 = col2.container()
        con3 = col3.container()
        con4 = col4.container()
        con5 = col5.container()
        return con1, con2, con3, con4, con5

    def create_tabs(self):
        opt = sac.buttons([
                sac.ButtonsItem(label="Home", icon="house-door-fill"),
                sac.ButtonsItem(label="5G NR", icon="bar-chart-fill"),
                sac.ButtonsItem(label="4G LTE", icon="bar-chart-fill"),
                sac.ButtonsItem(label="2G GSM", icon="bar-chart-fill"),
              ], align='center', radius='sm', color='#4682b4', use_container_width=True)
        return opt

    def handle_tab_selection(self, opt):
        if opt == "Home":
            # st.switch_page("src/main.py")
            None
        elif opt == "5G NR":
            nr_daily_page()
        elif opt == "4G LTE":
            lte_daily_page()
        elif opt == "2G GSM":
            gsm_daily_page()

    def run(self):
        self.create_layout()
        opt = self.create_tabs()
        self.handle_tab_selection(opt)

def page_tab_daily():
    daily_tabs = DailyTabs()
    daily_tabs.run()
