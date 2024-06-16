import altair as alt
import pandas as pd


class BaseChart:
    def __init__(self, data):
        self.data = data

    def prepare_data(self):
        pass

    def create_chart(self):
        pass

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            self.prepare_data()
            chart = self.create_chart()
            func(chart, *args, **kwargs)

        return wrapper


class LineChart(BaseChart):
    def __init__(self, data, x, y, color=None):
        super().__init__(data)
        self.x = x
        self.y = y
        self.color = color

    def prepare_data(self):
        self.data[self.x] = pd.to_datetime(self.data[self.x])

    def create_chart(self):
        chart = (
            alt.Chart(self.data)
            .mark_line()
            .encode(x=self.x, y=self.y, color=self.color)
            .properties(width=600, height=400)
        )
        return chart


class BarChart(BaseChart):
    def __init__(self, data, x, y, color=None):
        super().__init__(data)
        self.x = x
        self.y = y
        self.color = color

    def create_chart(self):
        chart = alt.Chart(self.data).mark_bar().encode(x=self.x, y=self.y)

        if self.color:
            chart = chart.encode(color=self.color)

        chart = chart.properties(width=600, height=400)

        return chart


class ScatterChart(BaseChart):
    def __init__(self, data, x, y, color=None, size=None, tooltip=None):
        super().__init__(data)
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.tooltip = tooltip

    def create_chart(self):
        chart = (
            alt.Chart(self.data)
            .mark_point()
            .encode(
                x=self.x,
                y=self.y,
                color=self.color,
                size=self.size,
                tooltip=self.tooltip,
            )
            .properties(width=600, height=400)
        )
        return chart


# # Contoh penggunaan
# data = pd.DataFrame(
#     {
#         "date": [
#             "5/1/2024",
#             "5/1/2024",
#             "5/1/2024",
#             "5/1/2024",
#             "5/1/2024",
#             "5/1/2024",
#             "5/1/2024",
#             "5/1/2024",
#             "5/1/2024",
#         ],
#         "category": ["A", "B", "C", "A", "B", "C", "A", "B", "C"],
#         "value1": [10, 20, 30, 40, 50, 60, 70, 80, 90],
#         "value2": [5, 15, 25, 35, 45, 55, 65, 75, 85],
#     }
# )


# @LineChart(data, "date", "value1", color="category", column="category")
# def show_line_chart(chart):
#     st.altair_chart(chart)


# @BarChart(data, "category", "value1", color="category")
# def show_bar_chart(chart):
#     st.altair_chart(chart)


# @ScatterChart(
#     data,
#     "value1",
#     "value2",
#     color="category",
#     size="value1",
#     tooltip=["category", "value1", "value2"],
# )
# def show_scatter_chart(chart):
#     st.altair_chart(chart)


# # Menampilkan chart menggunakan Streamlit
# show_line_chart()
# show_bar_chart()
# show_scatter_chart()
