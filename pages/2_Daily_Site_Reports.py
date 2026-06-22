import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

if "user" not in st.session_state:
    st.warning("⚠️ Please login via app.py first.")
    st.stop()

st.title("📝 Daily Site Progress & Operations Logs")
st.caption("Field Engineering Tool for Logging Daily Manpower, Materials, Weather, and Site Progress")

conn = sqlite3.connect("database/projects.db", check_same_thread=False)
c = conn.cursor()

# إنشاء جدول التقارير اليومية في قاعدة البيانات
c.execute("""
CREATE TABLE IF NOT EXISTS daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, report_date TEXT,
    weather TEXT, manpower TEXT, materials_received TEXT, equipment_status TEXT,
    progress_notes TEXT, logged_by TEXT, created_at TEXT
)
""")
conn.commit()

current_role = st.session_state.user["role"].replace("(", "").replace(")", "").replace("'", "").replace('"', '').replace(",", "").strip()

c.execute("SELECT id, name FROM projects")
all_projects = c.fetchall()

if not all_projects:
    st.warning("⚠️ Please create at least one project first before logging daily reports.")
else:
    project_dict = {name: pid for pid, name in all_projects}
    
    # 📥 نموذج إدخال التقرير اليومي الميداني (Admins & Engineers)
    if current_role in ["Admin", "Engineer"]:
        with st.expander("📝 Log Today's Site Progress Activity"):
            with st.form("daily_report_form", clear_on_submit=True):
                target_p = st.selectbox("Select Site Location / Project", list(project_dict.keys()))
                rep_date = st.date_input("Report Reporting Date", value=datetime.today())
                weather = st.selectbox("Site Weather Condition", ["Clear / Sunny", "Heavy Rain", "High Winds", "Extreme Heat", "Dust Storm"])
                
                col_r1, col_r2 = st.columns(2)
                manpower = col_r1.text_area("Manpower Attendance (e.g., 5 Civil Engineers, 20 Masons, 10 Labors)")
                materials = col_r2.text_area("Materials Received Logs (e.g., 50 Tons Reinforcement Steel, 100 Bags Cement)")
                
                equipment = st.text_input("Heavy Equipment Status On Site (e.g., Tower Crane Active, Excavator Breakdown)")
                notes = st.text_area("Summary of Accomplished Works / Key Notes")
                
                if st.form_submit_button("Submit & Broadcast Daily Log"):
                    if notes:
                        c.execute("""
                        INSERT INTO daily_reports (project_id, report_date, weather, manpower, materials_received, equipment_status, progress_notes, logged_by, created_at)
                        VALUES (?,?,?,?,?,?,?,?,?)
                        """, (project_dict[target_p], str(rep_date), weather, manpower, materials, equipment, notes, st.session_state.user["name"], datetime.now().strftime("%Y-%m-%d %H:%M")))
                        conn.commit()
                        st.success("🎉 Daily site report cataloged and archived into master project portfolio log successfully!")
                        st.rerun()

    # 🔍 محرك استعراض الأرشيف التاريخي للتقارير اليومية للمشاريع
    st.markdown("---")
    st.subheader("📋 Historical Daily Activity Logs Repository")
    
    df_reports = pd.read_sql("""
        SELECT r.id, p.name as project, r.report_date, r.weather, r.manpower, r.materials_received, r.equipment_status, r.progress_notes, r.logged_by 
        FROM daily_reports r JOIN projects p ON r.project_id = p.id ORDER BY r.id DESC
    """, conn)
    
    if df_reports.empty:
        st.info("No field daily shift logs have been tracked inside repository data tables yet.")
    else:
        for _, row in df_reports.iterrows():
            with st.container():
                st.write(f"### 📄 Report ID #{row['id']}: {row['project']} Log")
                st.markdown(f"📅 **Date:** {row['report_date']} | ☀️ **Weather:** {row['weather']} | 👤 **Logged By:** {row['logged_by']}")
                
                col_det1, col_det2 = st.columns(2)
                with col_det1:
                    st.info(f"👷 **Manpower Attendance:**\n{row['manpower']}")
                with col_det2:
                    st.success(f"🧱 **Materials Tracked:**\n{row['materials_received']}")
                    
                st.warning(f"🚜 **Equipment Operations Telemetry:** {row['equipment_status']}")
                st.markdown(f"📝 **Daily Task Output Summaries:**\n*{row['progress_notes']}*")
                st.divider()

conn.close()

