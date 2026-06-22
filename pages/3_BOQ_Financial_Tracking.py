
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

if "user" not in st.session_state:
    st.warning("⚠️ Please login via app.py first.")
    st.stop()

st.title("💰 Bill of Quantities (BOQ) & Project Cost Telemetry")
st.caption("Financial Engineering Module for Tracking Itemized BOQ budgets, Actual Cash Outflow, and Variance Analytics")

conn = sqlite3.connect("database/projects.db", check_same_thread=False)
c = conn.cursor()

# إنشاء جدول الحسابات والميزانيات في قاعدة البيانات
c.execute("""
CREATE TABLE IF NOT EXISTS boq_finance (
    id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, item_code TEXT,
    description TEXT, budgeted_cost REAL, actual_spent REAL
)
""")
conn.commit()

current_role = st.session_state.user["role"].replace("(", "").replace(")", "").replace("'", "").replace('"', '').replace(",", "").strip()

c.execute("SELECT id, name FROM projects")
all_projects = c.fetchall()

if not all_projects:
    st.warning("⚠️ Please create at least one project first in the Projects page to map financial accounts.")
else:
    project_dict = {name: pid for pid, name in all_projects}
    
    # 📥 نموذج إدخال بند مالي أو فاتورة مصروفة جديدة (Admins & Engineers)
    if current_role in ["Admin", "Engineer"]:
        with st.expander("💸 Link New Financial Budget/Outflow Item"):
            with st.form("finance_form", clear_on_submit=True):
                target_p = st.selectbox("Associated Project Account Link", list(project_dict.keys()))
                item_code = st.text_input("BOQ Reference Code (e.g., BOQ-DIV-03)")
                desc = st.text_input("Work Package Item Description (e.g., Concrete Substructure Works)")
                
                col_f1, col_f2 = st.columns(2)
                budget = col_f1.number_input("Allocated Budget Cost ($)", min_value=0.0, step=500.0)
                spent = col_f2.number_input("Actual Cash Amount Spent ($)", min_value=0.0, step=500.0)
                
                if st.form_submit_button("Commit Financial Allocation"):
                    if item_code and desc:
                        c.execute("""
                        INSERT INTO boq_finance (project_id, item_code, description, budgeted_cost, actual_spent)
                        VALUES (?,?,?,?,?)
                        """, (project_dict[target_p], item_code, desc, budget, spent))
                        conn.commit()
                        st.success("Financial ledger entry updated successfully!")
                        st.rerun()

    # 🔍 معالجة البيانات وبناء التحليل المالي والرسومات التفاعلية
    df_finance = pd.read_sql("""
        SELECT f.id, p.name as project, f.item_code, f.description, f.budgeted_cost, f.actual_spent,
        (f.budgeted_cost - f.actual_spent) as balance_remaining
        FROM boq_finance f JOIN projects p ON f.project_id = p.id ORDER BY f.id DESC
    """, conn)
    
    if df_finance.empty:
        st.info("No accounting entries mapped within target scoping assets ledger tables yet.")
    else:
        st.subheader("📊 Portfolio Budget Variance Overview")
        
        # رسم بياني تفاعلي يقارن الميزانية المرصودة بالمصروف الفعلي هندسياً
        fig_fin = px.bar(df_finance, x="item_code", y=["budgeted_cost", "actual_spent"], barmode="group",
                         title="BOQ Budgeted Cost vs Actual Spent Outflow Analysis", labels={"value": "Amount ($)", "variable": "Financial Ledger"})
        st.plotly_chart(fig_fin, use_container_width=True)
        
        st.subheader("📋 Master Accounts Balance Sheet Matrix")
        st.dataframe(df_finance, use_container_width=True)
        
        # 🚨 نظام حماية فوري وتنبيه للمشاريع المخترقة للميزانية (Cost Overrun Alerts)
        st.markdown("### 🚨 Critical Cost Overrun Alerts Telemetry")
        overrun_detected = False
        for _, row in df_finance.iterrows():
            if row["balance_remaining"] < 0:
                overrun_detected = True
                st.error(f"⚠️ **Budget Breached!** Project *{row['project']}* Item Code `{row['item_code']}` ({row['description']}) has breached its budget allocation loop by **${abs(row['balance_remaining']):,.2f}**!")
                
        if not overrun_detected:
            st.success("✅ Financial Health Stable: All tracked expenditure indexes are operating inside authorized allocation metrics parameters loops.")

conn.close()
