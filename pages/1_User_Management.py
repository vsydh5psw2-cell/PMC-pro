import streamlit as st
import sqlite3
import hashlib
import pandas as pd

if "user" not in st.session_state:
    st.warning("⚠️ Please login via app.py first.")
    st.stop()

# التحقق من أن المستخدم الحالي هو مسؤول النظام فقط
current_role = st.session_state.user["role"].replace("(", "").replace(")", "").replace("'", "").replace('"', '').replace(",", "").strip()
if current_role != "Admin":
    st.error("🔒 Access Denied. Only System Administrators can access User Management.")
    st.stop()

st.title("👥 User & Access Management Panel")
st.caption("Admin Dashboard to Create, Update, and Suspend Staff Credentials")

conn = sqlite3.connect("database/projects.db", check_same_thread=False)
c = conn.cursor()

def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()

# 📥 نموذج إنشاء حساب موظف أو مقاول جديد
with st.expander("➕ Register New Corporate User Account"):
    with st.form("new_user_form", clear_on_submit=True):
        new_username = st.text_input("Username (Unique ID)").strip().lower()
        new_password = st.text_input("Account Password", type="password")
        new_role = st.selectbox("Assigned System Role (RBAC)", ["Admin", "Engineer", "Viewer"])
        
        if st.form_submit_button("Create Account"):
            if new_username and new_password:
                try:
                    c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)", (new_username, hash_pw(new_password), new_role))
                    conn.commit()
                    st.success(f"🎉 User account '{new_username}' created successfully as '{new_role}'!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Username already exists. Please choose a different ID.")
            else:
                st.error("All credential fields are mandatory.")

# 📋 استعراض وحذف الحسابات الحالية داخل النظام
st.markdown("---")
st.subheader("📋 Active System User Registry")
df_users = pd.read_sql("SELECT id as ID, username as Username, role as Role FROM users", conn)

if not df_users.empty:
    for index, row in df_users.iterrows():
        uid = row["ID"]
        u_name = row["Username"]
        
        # منع الأدمن من حذف حسابه الشخصي بالخطأ لقفل النظام
        if u_name == "admin":
            st.write(f"🛡️ **Master Root Account:** `{u_name}` | Role: `{row['Role']}`")
            st.divider()
            continue
            
        with st.container():
            col_u1, col_u2 = st.columns([4, 1])
            with col_u1:
                st.write(f"👤 **User Identity:** `{u_name}` | System Privilege Level: **{row['Role']}**")
            with col_u2:
                if st.button("🗑️ Revoke Access", key=f"del_u_{uid}"):
                    c.execute("DELETE FROM users WHERE id=?", (uid,))
                    conn.commit()
                    st.success(f"Credentials revoked.")
                    st.rerun()
            st.divider()

conn.close()

