[![jarvis-timeseries](https://img.shields.io/static/v1?label=&message=Jarvis&color=blue&logo=github)](https://github.com/daiyabarus/jarvis-timeseries "Go to GitHub repo")
[![Made with Python](https://img.shields.io/badge/Python->=3.12-blue?logo=python&logoColor=white)](https://python.org "Go to Python homepage")
[![License](https://img.shields.io/badge/License-MIT-blue)](#license)
[![Made with PostgreSQL](https://img.shields.io/badge/PostgreSQL-13-blue?logo=postgresql&logoColor=white)](https://www.postgresql.org/ "Go to PostgresSQL homepage")
[![OS - Windows](https://img.shields.io/badge/OS-Windows-blue?logo=windows&logoColor=white)](https://www.microsoft.com/ "Go to Microsoft homepage")
![maintained - yes](https://img.shields.io/badge/maintained-yes-blue)

# Jarvis

This is a Streamlit app for programming Python with Streamlit, Pandas, Plotly, Seaborn, and Matplotlib.

## Project Structure

The project has the following files and folders:

## Setup

To set up and run the Streamlit app, follow these steps:

1. Clone the repository.
2. Install the required dependencies by running the following command:
   ```
   pip install -r requirements.txt
   ```
3. Run the Streamlit app by executing the following command:
   ```
   streamlit run .\src\main.py
   ```
## Structure folder
The project's folder structure is as follows:

```
├── .streamlit
│   ├── config.toml
│   └── secrets.toml
├── assets
│   ├── icons
│   │   ├── icon2g.png
│   │   ├── icon3g.png
│   │   ├── icon4g.png
│   │   └── icon5g.png
│   └── signaltower.png
├── database
│   └── database.db
├── docs
│   ├── LICENSE.md
│   └── README.md
├── requirements.txt
└── src
  ├── config
  │   ├── navbar.py
  │   └── page_config.py
  ├── layout
  │   ├── app.py
  │   ├── daily
  │   │   ├── gsmdaily.py
  │   │   ├── ltedaily.py
  │   │   └── nrdaily.py
  │   └── sidebar.py
  └── utils
    ├── db_con.py
    ├── db_process.py
    └── dbutils.py
      ...
```




## Usage

Once the Streamlit app is running, you can access it in your web browser at `http://localhost:8501`. The app provides a user interface for programming Python with Streamlit, Pandas, Plotly, Seaborn, and Matplotlib. You can use it to visualize data, create interactive plots, and explore different Python programming concepts.

## Credit to
- **Puffin:** https://github.com/lpapaspyros/puffin
- **StreamlitAntdComponents:** https://github.com/nicedouble/StreamlitAntdComponents.git
