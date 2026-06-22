import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

# فحص أمني لمنع الدخول العشوائي
if "user" not in st.session_state:
    st.warning("⚠️ Please login via app.py first.")
    st.stop()

st.title("📄 Engineering Drawings & Blueprint Management (EDMS)")
st.caption("Central Control Repository for Approved IFC Drawings & Revision History")

# الاتصال بقاعدة البيانات المركزية الموحدة لـ PMC PRO
conn = sqlite3.connect("database/projects.db", check_same_thread=False)
c = conn.cursor()

# إنشاء مجلد حفظ المخططات تلقائياً لمنع أي أخطاء في النظام
os.makedirs("blueprints", exist_ok=True)

# إنشاء جدول المخططات والوثائق الهندسية في قاعدة البيانات
c.execute("""
CREATE TABLE IF NOT EXISTS drawings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    drawing_title TEXT,
    drawing_number TEXT,
    category TEXT,
    revision TEXT,
    file_path TEXT,
    uploaded_by TEXT,
    upload_time TEXT
)
""")
conn.commit()

current_role = st.session_state.user["role"]

# جلب قائمة المشاريع لربط المخططات المرفوعة بها
c.execute("SELECT id, name FROM projects")
all_projects = c.fetchall()

if not all_projects:
    st.warning("⚠️ No active projects found. Please create a project first before staging engineering drawings.")
else:
    project_dict = {name: pid for pid, name in all_projects}
    
    # -------------------------------------------------------------
    # 1️⃣ بوابة رفع المخططات الهندسية المعتمدة (Admin / Engineer Only)
    # -------------------------------------------------------------
    if current_role in ["Admin", "Engineer"]:
        with st.expander("📤 Upload Approved Document / Shop Drawing"):
            with st.form("drawing_form", clear_on_submit=True):
                target_p = st.selectbox("Link Drawing to Project", list(project_dict.keys()))
                title = st.text_input("Drawing Title (e.g., Foundation Layout Plan)")
                dwg_num = st.text_input("Drawing Reference Number (e.g., CED-Z1-STR-004)")
                
                col_form1, col_form2 = st.columns(2)
                category = col_form1.selectbox("Engineering Discipline", ["Structural (STR)", "Architectural (ARC)", "Mechanical (MEP)", "Electrical (ELC)", "General Infrastructure"])
                revision = col_form2.text_input("Revision Level (e.g., Rev 0, Rev 1, IFC)", value="Rev 0")
                
                # منفذ استقبال الملفات الهندسية بكافة الصيغ المشهورة
                uploaded_drawing = st.file_uploader("Choose Blueprint File (PDF, DWG, DXF, PNG, JPG)", type=["pdf", "dwg", "dxf", "png", "jpg", "jpeg"])
                
                if st.form_submit_button("Commit Drawing to Archive"):
                    if title and dwg_num and uploaded_drawing is not None:
                        # توليد مسار واسم فريد للمخطط لمنع تداخل الملفات المتشابهة
                        filename = f"dwg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uploaded_drawing.name}"
                        drawing_path = os.path.join("blueprints", filename)
                        
                        # حفظ الملف بصيغته الثنائية الأصلية داخل مجلد blueprints
                        with open(drawing_path, "wb") as f:
                            f.write(uploaded_drawing.getbuffer())
                            
                        # تسجيل البيانات الوصفية للمخطط في قاعدة البيانات
                        c.execute("""
                        INSERT INTO drawings (project_id, drawing_title, drawing_number, category, revision, file_path, uploaded_by, upload_time)
                        VALUES (?,?,?,?,?,?,?,?)
                        """, (project_dict[target_p], title, dwg_num, category, revision, drawing_path, st.session_state.user["name"], datetime.now().strftime("%Y-%m-%d %H:%M")))
                        conn.commit()
                        st.success(f"🎉 Blueprint '{title}' successfully securely cataloged into engineering archives!")
                        st.rerun()
                    else:
                        st.error("Operation halted. Drawing Title, Reference Number, and File Attachment are mandatory.")

    # -------------------------------------------------------------
    # 2️⃣ محرك تصفية، عرض، وتحميل المخططات الهندسية للموقع
    # -------------------------------------------------------------
    st.markdown("---")
    st.subheader("🔍 Master Drawing List & Search Engine")
    
    # أدوات تصفية ذكية للمهندس في الموقع للبحث عن مخطط محدد بسرعة
    col_filter1, col_filter2 = st.columns(2)
    search_query = col_filter1.text_input("🔍 Search Drawings by Title or Reference Number")
    filter_discipline = col_filter2.selectbox("Filter by Engineering Discipline", ["All Disciplines", "Structural (STR)", "Architectural (ARC)", "Mechanical (MEP)", "Electrical (ELC)", "General Infrastructure"])
    
    # بناء استعلام البحث الديناميكي مع دمج جدول المشاريع
    query_str = """
        SELECT d.id, p.name as project, d.drawing_title, d.drawing_number, d.category, d.revision, d.file_path, d.uploaded_by, d.upload_time 
        FROM drawings d 
        JOIN projects p ON d.project_id = p.id 
        WHERE 1=1
    """
    params = []
    
    if search_query:
        query_str += " AND (d.drawing_title LIKE ? OR d.drawing_number LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
        
    if filter_discipline != "All Disciplines":
        query_str += " AND d.category = ?"
        params.append(filter_discipline)
        
    query_str += " ORDER BY d.id DESC"
    
    df_drawings = pd.read_sql(query_str, conn, params=params)
    
    if df_drawings.empty:
        st.info("No approved engineering drawings or blueprints match the current search filters.")
    else:
        # عرض المخططات على شكل لوحة تحكم شبكية تفاعلية وجذابة للموقع
        for _, row in df_drawings.iterrows():
            d_id = row["id"]
            with st.container():
                col_d1, col_d2, col_d3 = st.columns([5, 3, 2])
                
                with col_d1:
                    st.markdown(f"### 📐 {row['drawing_title']}")
                    st.write(f"**Ref Number:** `{row['drawing_number']}` | **Discipline:** {row['category']}")
                    st.caption(f"Project Node: **{row['project']}** | Uploaded By: {row['uploaded_by']} ({row['upload_time']})")
                    
                with col_d2:
                    # شارة توضح رقم الإصدار الحالي للمخطط لمنع الخطأ في الموقع
                    st.warning(f"📌 Version Status: **{row['revision']}**")
                    
                with col_d3:
                    # محرك تحميل الملف الهندسي فوراً إلى حاسوب أو هاتف المهندس
                    if row["file_path"] and os.path.exists(row["file_path"]):
                        with open(row["file_path"], "rb") as file_bytes:
                            # استخراج الامتداد الأصلي للملف المرفوع لتوفير صيغة صحيحة عند التنزيل
                            file_ext = os.path.splitext(row["file_path"])[1]
                            st.download_button(
                                label="📥 Download DWG/PDF",
                                data=file_bytes.read(),
                                file_name=f"{row['drawing_number']}_{row['revision']}{file_ext}",
                                key=f"dwg_dl_{d_id}"
                            )
                    else:
                        st.error("Attachment File Missing on Server")
                        
                st.divider()

conn.close()

