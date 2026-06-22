import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import io
from datetime import datetime

if "user" not in st.session_state:
    st.warning("⚠️ Please login via app.py first.")
    st.stop()

st.title("📊 Strategic PMO & Portfolio Dashboard")

conn = sqlite3.connect("database/projects.db", check_same_thread=False)
df = pd.read_sql("SELECT * FROM projects", conn)

col1, col2, col3 = st.columns(3)
col1.metric("Total Portfolio", len(df))
col2.metric("Active Mandates", len(df[df["status"] == "Active"]) if not df.empty else 0)
col3.metric("Completed Workstreams", len(df[df["status"] == "Completed"]) if not df.empty else 0)

st.divider()

if not df.empty:
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        fig = px.pie(df, names="status", title="Project Status Distribution", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    with chart_col2:
        fig2 = px.bar(df, x="name", y="progress", color="status", title="Project Progression Index")
        st.plotly_chart(fig2, use_container_width=True)
        
    st.subheader("📁 Master Dataset view")
    st.dataframe(df, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Portfolio Report')
    st.download_button(label="⬇️ Export Excel Report", data=buffer.getvalue(), file_name=f"PMC_PRO_Report_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("No projects registered in the repository data tables yet.")
conn.close()

