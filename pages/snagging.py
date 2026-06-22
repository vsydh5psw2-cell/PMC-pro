import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

# Security Gate
if "user" not in st.session_state:
    st.warning("⚠️ Please login via app.py first.")
    st.stop()

st.title("🔎 Advanced Site Snagging & Quality Control")
st.caption("Enterprise Defect Management, SLA Tracking, Digital Sign-off, and Financial Penalties Matrix")

# Core Shared Database Link
conn = sqlite3.connect("database/projects.db", check_same_thread=False)
c = conn.cursor()

# 1. Base Structural Seeding
c.execute("""
CREATE TABLE IF NOT EXISTS snags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    description TEXT,
    location TEXT,
    severity TEXT,
    status TEXT,
    assigned_to TEXT,
    photo_issue TEXT,
    photo_fixed TEXT,
    created TEXT
)
""")
conn.commit()

# 2. Automated Schema Matrix Upgrades
columns_to_add = [
    ("target_date", "TEXT"),
    ("rework_cost", "REAL"),
    ("signed_off_by", "TEXT"),
    ("inspection_notes", "TEXT")
]

for col_name, col_type in columns_to_add:
    try:
        c.execute(f"ALTER TABLE snags ADD COLUMN {col_name} {col_type}")
        conn.commit()
    except sqlite3.OperationalError:
        pass

# Extract Active User Context Clean
current_user_data = st.session_state.user
current_role = current_user_data["role"].replace("(", "").replace(")", "").replace("'", "").replace('"', '').replace(",", "").strip()

# Fetch active project nodes lookup list
c.execute("SELECT id, name FROM projects")
all_projects = c.fetchall()

if not all_projects:
    st.warning("⚠️ Please create at least one project first in the Projects page.")
else:
    project_dict = {name: pid for pid, name in all_projects}
    
    # -------------------------------------------------------------
    # CREATE DISCOVERY WORKSPACE DATA ENTRY FORM
    # -------------------------------------------------------------
    if current_role in ["Admin", "Engineer"]:
        with st.expander("⚠️ Log New Site Defect / Snag Item"):
            with st.form("snag_form", clear_on_submit=True):
                target_p = st.selectbox("Associated Project Link", list(project_dict.keys()))
                desc = st.text_area("Defect Description / Unresolved Item")
                loc = st.text_input("Exact Site Location (e.g., Zone B - Flat 4)")
                
                col_f1, col_f2 = st.columns(2)
                severity = col_f1.selectbox("Risk Severity", ["Minor", "Major", "Critical"])
                assigned = col_f2.text_input("Responsible Contractor Name")
                
                col_f3, col_f4 = st.columns(2)
                target_date = col_f3.date_input("Target Resolution Deadline (SLA)")
                rework_cost = col_f4.number_input("Rework Penalty Cost ($)", min_value=0.0, step=100.0)
                
                uploaded_issue_img = st.file_uploader("📸 Upload Defect Photo", type=["png", "jpg", "jpeg"])
                
                if st.form_submit_button("Publish Snag Record"):
                    if desc:
                        photo_issue_path = "N/A"
                        if uploaded_issue_img is not None:
                            filename = f"issue_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uploaded_issue_img.name}"
                            photo_issue_path = os.path.join("uploads", filename)
                            with open(photo_issue_path, "wb") as f:
                                f.write(uploaded_issue_img.getbuffer())
                        
                        c.execute("""
                        INSERT INTO snags (project_id, description, location, severity, status, assigned_to, photo_issue, photo_fixed, target_date, rework_cost, signed_off_by, inspection_notes, created) 
                        VALUES (?,?,?,?,?,?,?,?,?)
                        """, (project_dict[target_p], desc, loc, severity, "Logged", assigned, photo_issue_path, "N/A", str(target_date), rework_cost, "N/A", "N/A", datetime.now().strftime("%Y-%m-%d %H:%M")))
                        conn.commit()
                        st.success("Defect registered and SLA tracking activated successfully!")
                        st.rerun()

    # -------------------------------------------------------------
    # INTERACTIVE FILTERS BLOCK
    # -------------------------------------------------------------
    st.markdown("---")
    st.subheader("🔍 Smart Filter & Risk Matrix")
    
    col_m1, col_m2 = st.columns(2)
    filter_severity = col_m1.selectbox("Filter by Severity Risk", ["All Severities", "Minor", "Major", "Critical"])
    filter_status = col_m2.selectbox("Filter by Operational Lifecycle", ["All Active Snags", "Logged", "Received", "Under Review", "Rectified & Closed"])
    
    # Clean Single Line Query string representation to avoid AST compilation failure
    query_base = "SELECT s.id, p.name as project, s.description, s.location, s.severity, s.status, s.assigned_to, s.photo_issue, s.photo_fixed, s.target_date, s.rework_cost, s.signed_off_by, s.inspection_notes, s.created FROM snags s JOIN projects p ON s.project_id = p.id WHERE 1=1"
    params = []
    
    if filter_severity != "All Severities":
        query_base += " AND s.severity = ?"
        params.append(filter_severity)
        
    if filter_status == "All Active Snags":
        query_base += " AND s.status != 'Rectified & Closed'"
    else:
        query_base += " AND s.status = ?"
        params.append(filter_status)
        
    query_base += " ORDER BY s.id DESC"
    
    df_snags = pd.read_sql(query_base, conn, params=params)
    
    if df_snags.empty:
        st.info("No site snag list items found matching the selected risk filters.")
    else:
        # -------------------------------------------------------------
        # METRICS DISPLAY AND ACTION INTERFACE
        # -------------------------------------------------------------
        for _, row in df_snags.iterrows():
            sid = row["id"]
            
            with st.container():
                status_labels = {
                    "Logged": "🔵 **[Status: Logged - Awaiting Action]**",
                    "Received": "🟡 **[Status: Received - Work in Progress]**",
                    "Under Review": "🟠 **[Status: Under Review - Pending Sign-Off]**",
                    "Rectified & Closed": "🟢 **[Status: Rectified & Closed - Archived]**"
                }
                
                st.write(f"### Defect Item #{sid}: {row['description']}")
                st.markdown(status_labels.get(row["status"], row["status"]))
                
                if row["status"] != "Rectified & Closed" and row["target_date"] and row["target_date"] != "N/A":
                    try:
                        due_date = datetime.strptime(row["target_date"], "%Y-%m-%d").date()
                        today = datetime.today().date()
                        if today > due_date:
                            days_overdue = (today - due_date).days
                            st.error(f"⚠️ **SLA BREACHED:** Overdue by {days_overdue} Days! Target was {row['target_date']}.")
                        else:
                            st.success(f"⏱️ **SLA Deadline Active:** Target date is {row['target_date']}.")
                    except Exception:
                        pass
                
                col_det1, col_det2 = st.columns(2)
                with col_det1:
                    st.write(f"**Project:** {row['project']} | **Location:** {row['location']}")
                    st.write(f"**Contractor:** `{row['assigned_to']}` | **Severity:** {row['severity']}")
                with col_det2:
                    st.write(f"**Rework Penalty:** `${row['rework_cost']:,.2f}`")
                    if row["status"] == "Rectified & Closed":
                        st.write(f"✍️ **Signed Off By:** `{row['signed_off_by']}`")
                        st.write(f"📝 **Inspection Notes:** *{row['inspection_notes']}*")

                col_img1, col_img2 = st.columns(2)
                with col_img1:
                    if row["photo_issue"] and row["photo_issue"] != "N/A" and os.path.exists(row["photo_issue"]):
                        st.image(row["photo_issue"], caption="📸 Before Fix", use_container_width=True)
                with col_img2:
                    if row["photo_fixed"] and row["photo_fixed"] != "N/A" and os.path.exists(row["photo_fixed"]):
                        st.image(row["photo_fixed"], caption="✅ After Fix", use_container_width=True)

                if current_role in ["Admin", "Engineer"]:
                    st.markdown("**Workflow Management Actions:**")
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    
                    if row["status"] == "Logged" and btn_col1.button("📥 Confirm Received", key=f"rcv_{sid}"):
                        c.execute("UPDATE snags SET status='Received' WHERE id=?", (sid,))
                        conn.commit()
                        st.rerun()
                        
                    if row["status"] == "Received":
                        with btn_col2.expander("🚀 Submit Contractor Fix"):
                            uploaded_fixed_img = st.file_uploader("Upload Rectification Photo", type=["png", "jpg", "jpeg"], key=f"up_fix_{sid}")
                            if st.button("Submit for Inspection", key=f"sub_fix_{sid}"):
                                photo_fixed_path = "N/A"
                                if uploaded_fixed_img is not None:
                                    filename = f"fixed_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uploaded_fixed_img.name}"
                                    photo_fixed_path = os.path.join("uploads", filename)
                                    with open(photo_fixed_path, "wb") as f:
                                        f.write(uploaded_fixed_img.getbuffer())

