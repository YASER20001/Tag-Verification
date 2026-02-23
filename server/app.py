"""
Tag Verify — Streamlit entry point.
Run:  streamlit run app.py   (from the server/ directory)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from db.db_sync import init_db, get_stats, get_recent_documents, get_void_alerts

st.set_page_config(
    page_title="Tag Verify",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Initialise database once ----
@st.cache_resource
def _init():
    init_db()
    return True

_init()

# ---- Shared CSS ----
st.markdown("""
<style>
/* Hide default Streamlit chrome */
#MainMenu {visibility: hidden;}
footer    {visibility: hidden;}

/* Sidebar branding */
[data-testid="stSidebar"] { background: #0f1b2d; }
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2 { color: #f1f5f9 !important; }

/* Status badges */
.badge { display:inline-block; padding:2px 10px; border-radius:12px;
         font-size:12px; font-weight:600; }
.badge-valid    { background:#dcfce7; color:#166534; }
.badge-void     { background:#fef9c3; color:#854d0e; }
.badge-notfound { background:#fee2e2; color:#991b1b; }
.badge-shorthand{ background:#dbeafe; color:#1e40af; }
.badge-active   { background:#dcfce7; color:#166534; }
.badge-voidtag  { background:#fef9c3; color:#854d0e; }

/* Stepper */
.stepper-wrap { display:flex; align-items:center; margin-bottom:28px; }
.step-node {
    width:36px; height:36px; border-radius:50%; display:flex;
    align-items:center; justify-content:center; font-weight:700;
    font-size:14px; flex-shrink:0;
}
.step-done  { background:#22c55e; color:#fff; }
.step-active{ background:#1e3a5f; color:#fff;
              box-shadow:0 0 0 4px #bfdbfe; }
.step-todo  { background:#e5e7eb; color:#9ca3af; }
.step-label { font-size:12px; margin-top:4px; text-align:center; }
.step-done-label  { color:#15803d; font-weight:600; }
.step-active-label{ color:#1e3a5f; font-weight:700; }
.step-todo-label  { color:#9ca3af; }
.step-line  { flex:1; height:2px; margin:0 6px; margin-bottom:18px; }
.step-line-done { background:#22c55e; }
.step-line-todo { background:#e5e7eb; }

/* Cards */
.metric-card {
    background:#fff; border:1px solid #e2e8f0; border-radius:12px;
    padding:20px; text-align:center;
}
.metric-value { font-size:2rem; font-weight:800; }
.metric-label { font-size:0.8rem; color:#64748b; margin-top:4px; }

/* Alerts */
.alert-void {
    background:#fffbeb; border:1px solid #fbbf24; border-radius:8px;
    padding:12px 16px; margin-bottom:8px;
}
</style>
""", unsafe_allow_html=True)


# ---- Home / landing page ----
st.markdown("## 🏷️ Tag Verify")
st.markdown(
    "**Engineering Tag Verification System** — Upload documents, extract tag numbers, "
    "verify against the Central Tag Database, and manage traceability."
)
st.divider()

stats = get_stats()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Tags (CTDB)", stats["total_tags"],
              delta=f"{stats['active_tags']} active")
with col2:
    st.metric("Documents Verified", stats["total_documents"])
with col3:
    st.metric("Passed", stats["passed_documents"],
              delta=None if not stats["total_documents"] else None)
with col4:
    st.metric("Issues Found", stats["issue_documents"])

st.divider()

st.markdown("### Navigate")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.page_link("pages/1_📊_Dashboard.py", label="📊 Dashboard", use_container_width=True)
with c2:
    st.page_link("pages/2_📄_Verify_Document.py", label="📄 Verify Document", use_container_width=True)
with c3:
    st.page_link("pages/3_🗃️_Tag_Database.py", label="🗃️ Tag Database", use_container_width=True)
with c4:
    st.page_link("pages/4_🔗_Impact_Analysis.py", label="🔗 Impact Analysis", use_container_width=True)
