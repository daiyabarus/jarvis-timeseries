import streamlit as st
import streamlit_antd_components as sac
from daily import gsm_daily_page, lte_daily_page, nr_daily_page


class DailyTabs:
    def __init__(self):
        self.setup_css()

    def setup_css(self):
        st.markdown(
            """
        <style>
        .stPlotlyChart {
            background-color: #f0f2f6;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            padding: 10px;
        }
        .st-bd {
            padding: 5px;
        }
        .st-eb {
            font-weight: 600;
        }
        .st-ca {
            color: #4682b4;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

    def create_layout(self):
        col1, col2, col3, col4 = st.columns(4)
        con1 = col1.container()
        con2 = col2.container()
        con3 = col3.container()
        con4 = col4.container()
        return con1, con2, con3, con4

    def create_tabs(self):
        opt = sac.tabs(
            [
                sac.TabsItem(label="Home", icon="house-door-fill"),
                sac.TabsItem(label="5G NR", icon="bar-chart-fill"),
                sac.TabsItem(label="4G LTE", icon="bar-chart-fill"),
                sac.TabsItem(label="2G GSM", icon="bar-chart-fill"),
            ],
            align="center",
            variant="outline",
            color="#4682b4",
            use_container_width=True,
            return_index=True,
        )
        sac.divider(label="", align="center")
        return opt

    def handle_tab_selection(self, opt):
        if opt == 1:
            st.switch_page("src/main.py")
        elif opt == 2:
            nr_daily_page()
        elif opt == 3:
            lte_daily_page()
        elif opt == 4:
            gsm_daily_page()

    def run(self):
        self.create_layout()
        opt = self.create_tabs()
        self.handle_tab_selection(opt)
