import streamlit as st
import sqlite3
import pandas as pd

st.title("Historia wejść")
conn = sqlite3.connect('access_system.db')
df = pd.read_sql_query("SELECT * FROM logs ORDER BY timestamp DESC", conn)
st.table(df)