import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

if "user" not in st.session_state:
    st.warning("⚠️ Please login via app.py first.")
    st.stop()

st.title("📂 Central Corporate Projects Registry")
conn = sqlite3.connect("database/projects.db", check_same_thread=False)
c = conn.cursor()

current_role = st.session_state.user["role"]

if current_role in ["Admin", "Engineer"]:
    with st.expander("➕ Authorize New Enterprise Project Profile"):
        with st.form("add_project_form"):
            project_name = st.text_input("Project Name")
            client_name = st.text_input("Client Name")
            manager_name = st.text_input("Project Manager")
            status = st.selectbox("Status", ["Active", "Completed", "On Hold"])
            priority = st.selectbox("Priority Allocation", ["Low", "Medium", "High"])
            progress = st.slider("Progress %", 0, 100, 0)
            start_d = st.date_input("Start Date")
            end_d = st.date_input("Delivery Date")

            if st.form_submit_button("Add Project Record"):
                if project_name and client_name:
                    c.execute("""
                        INSERT INTO projects (name, client, manager, status, priority, progress, start_date, end_date, created)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (project_name, client_name, manager_name, status, priority, progress, str(start_d), str(end_d), datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success("Project Added Successfully!")
                    st.rerun()
                else:
                    st.error("Project Name and Client cannot be blank.")

df = pd.read_sql("SELECT * FROM projects", conn)
if df.empty:
    st.info("No projects registered in the database yet.")
else:
    status_options = ["Active", "Completed", "On Hold"]
    for index, row in df.iterrows():
        pid = row["id"]
        with st.container():
            col1, col2, col3 = st.columns([2,2,1])
            with col1:
                st.markdown(f"### 🏗️ {row['name']}")
                st.write(f"**Client:** {row['client']} | **Manager:** {row['manager']} | **Priority:** {row['priority']}")
                st.caption(f"Timeline: {row['start_date']} to {row['end_date']}")
            with col2:
                st.progress(int(row["progress"]) / 100)
                if current_role in ["Admin", "Engineer"]:
                    new_progress = st.slider(f"Update Progress %", 0, 100, int(row["progress"]), key=f"p_{pid}")
                    current_idx = status_options.index(row["status"]) if row["status"] in status_options else 0
                    new_status = st.selectbox(f"Update Status", status_options, index=current_idx, key=f"s_{pid}")
            with col3:
                st.write(f"Yield: {row['progress']}%")
                if current_role in ["Admin", "Engineer"]:
                    if st.button("💾 Save", key=f"u_{pid}"):
                        c.execute("UPDATE projects SET progress=?, status=? WHERE id=?", (new_progress, new_status, pid))
                        conn.commit()
                        st.rerun()
                    if current_role == "Admin":
                        if st.button("🗑️ Delete", key=f"del_{pid}"):
                            c.execute("DELETE FROM snags WHERE project_id=?", (pid,))
                            c.execute("DELETE FROM projects WHERE id=?", (pid,))
                            conn.commit()
                            st.rerun()
            st.divider()
conn.close()

