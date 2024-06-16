import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

# Streamlit UI
def main():
    st.title("My Streamlit App")
    st.write("Welcome to my Streamlit app!")

    # Data processing logic
    data = pd.read_csv("data.csv")
    st.write(data.head())

    # Plotting
    fig = px.scatter(data, x="x", y="y")
    st.plotly_chart(fig)

    sns.histplot(data["x"], kde=True)
    st.pyplot()

if __name__ == "__main__":
    main()