import sqlite3
import streamlit as st
import hashlib
import pandas as pd
import plotly.express as px
import io
import os
from datetime import datetime

# ==========================================
# SYSTEM GLOBAL PAGE DESIGN METRICS
# ==========================================
st.set_page_config(page_title="PMC Enterprise PRO", layout="wide")

# Ensure cloud storage directories exist cleanly
os.makedirs("database", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
os.makedirs("blueprints", exist_ok=True)

# Centralized Database Pool Connection
conn = sqlite3.connect("database/projects.db", check_same_thread=False)
c = conn.cursor()

# Database Schemas Architecture Definitions
c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, client TEXT, manager TEXT, status TEXT, priority TEXT, progress INTEGER, start_date TEXT, end_date TEXT, created TEXT)")
c.execute("""
CREATE TABLE IF NOT EXISTS snags (
    id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, description TEXT, 
    location TEXT, severity TEXT, status TEXT, assigned_to TEXT, 
    photo_issue TEXT, photo_fixed TEXT, target_date TEXT, rework_cost REAL, 
    signed_off_by TEXT, inspection_notes TEXT, created TEXT
)
""")
c.execute("CREATE TABLE IF NOT EXISTS drawings (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, drawing_title TEXT, drawing_number TEXT, category TEXT, revision TEXT, file_path TEXT, uploaded_by TEXT, upload_time TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS daily_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, report_date TEXT, weather TEXT, manpower TEXT, materials_received TEXT, equipment_status TEXT, progress_notes TEXT, logged_by TEXT, created_at TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS boq_finance (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, item_code TEXT, description TEXT, budgeted_cost REAL, actual_spent REAL)")
c.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, username TEXT, timestamp TEXT)")
conn.commit()

def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()

# Seeding baseline credentials
c.execute("SELECT * FROM users")
if not c.fetchall():
    users = [
        ("admin", hash_pw("1234"), "Admin"), 
        ("engineer", hash_pw("1234"), "Engineer"), 
        ("viewer", hash_pw("1234"), "Viewer")
    ]
    c.executemany("INSERT INTO users (username, password, role) VALUES (?,?,?)", users)
    conn.commit()

# --- SECURITY SYSTEM AUTHENTICATION BARRIER ---
if "user" not in st.session_state:
    st.title("🔐 PMC ENTERPRISE CONTROL CENTER")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Access System"):
        c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, hash_pw(p)))
        r = c.fetchone()
        if r:
            st.session_state.user = {"name": u, "role": str(r[0]).strip()}
            c.execute("INSERT INTO logs (action, username, timestamp) VALUES (?,?,?)", ("Logged In", u, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            st.success("Authorized successfully!")
            st.rerun()
        else:
            st.error("Invalid credentials entered.")
    st.stop()

# Safe extraction of the authenticated role
current_role = st.session_state.user["role"]

# ==========================================
# VIRTUAL INLINE PAGES DEFINITIONS
# ==========================================

def page_home():
    st.title("Welcome to PMC PRO Control Center")
    st.info("👈 Use the Sidebar Navigation menu to move directly across your operational tracking pages.")
    
    c.execute("SELECT COUNT(*) FROM projects")
    p_res = c.fetchone()
    projects_count = p_res[0] if p_res else 0

    c.execute("SELECT COUNT(*) FROM snags WHERE status != 'Rectified & Closed'")
    s_res = c.fetchone()
    snagging_count = s_res[0] if s_res else 0

    st.markdown("### 🏬 Current Site Operations Summary")
    col1, col2 = st.columns(2)
    col1.metric("Total Corporate Projects", projects_count)
    col2.metric("Active Site Snags", snagging_count)

def page_dashboard():
    st.title("📊 Strategic PMO & Portfolio Dashboard")
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
            
        st.subheader("📁 Master Dataset View")
        st.dataframe(df, use_container_width=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Portfolio Report')
        st.download_button(label="⬇️ Export Excel Report", data=buffer.getvalue(), file_name=f"PMC_PRO_Report_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("No projects registered in the repository data tables yet.")

def page_projects():
    st.title("📂 Central Corporate Projects Registry")
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

    df = pd.read_sql("SELECT * FROM projects", conn)
    if df.empty:
        st.info("No projects registered in the database yet.")
    else:
        status_options = ["Active", "Completed", "On Hold"]
        for index, row in df.iterrows():
            pid = row["id"]
            with st.container():
                col1, col2, col3 = st.columns()
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

def page_snagging():
    st.title("🔎 Advanced Site Snagging & Quality Control")
    c.execute("SELECT id, name FROM projects")
    all_projects = c.fetchall()

    if not all_projects:
        st.warning("⚠️ Please create at least one project first in the Projects page.")
    else:
        project_dict = {name: pid for pid, name in all_projects}
        if current_role in ["Admin", "Engineer"]:
            with st.expander("⚠️ Log New Site Defect / Snag Item"):
                with st.form("snag_form", clear_on_submit=True):
                    target_p = st.selectbox("Associated Project Link", list(project_dict.keys()))
                    desc = st.text_area("Defect Description")
                    loc = st.text_input("Exact Site Location")
