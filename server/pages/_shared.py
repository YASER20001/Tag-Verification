"""
Shared helpers imported by all Streamlit pages.
"""
import sys, os
# Ensure server/ is on path when pages are imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from db.db_sync import init_db

COMMON_CSS = """
<style>
#MainMenu {visibility: hidden;}
footer    {visibility: hidden;}
[data-testid="stSidebar"] { background: #0f1b2d; }
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

.badge { display:inline-block; padding:2px 10px; border-radius:12px;
         font-size:12px; font-weight:600; }
.badge-valid    { background:#dcfce7; color:#166534; }
.badge-void     { background:#fef9c3; color:#854d0e; }
.badge-notfound { background:#fee2e2; color:#991b1b; }
.badge-shorthand{ background:#dbeafe; color:#1e40af; }

.stepper-wrap { display:flex; align-items:center; gap:0; margin-bottom:24px; }
.step-col { display:flex; flex-direction:column; align-items:center; }
.step-node {
    width:36px; height:36px; border-radius:50%; display:flex;
    align-items:center; justify-content:center; font-weight:700; font-size:14px;
}
.step-done   { background:#22c55e; color:#fff; }
.step-active { background:#1e3a5f; color:#fff; box-shadow:0 0 0 4px #bfdbfe; }
.step-todo   { background:#e5e7eb; color:#9ca3af; }
.step-lbl    { font-size:11px; margin-top:3px; font-weight:600; }
.step-lbl-done   { color:#15803d; }
.step-lbl-active { color:#1e3a5f; }
.step-lbl-todo   { color:#9ca3af; }
.step-line   { flex:1; height:2px; margin-bottom:18px; }
.step-line-done { background:#22c55e; }
.step-line-todo { background:#e5e7eb; }
</style>
"""

STATUS_LABELS = {
    "valid_active":       "✅ Valid (Active)",
    "valid_void":         "⚠️ Valid (Void)",
    "not_found":          "❌ Not Found",
    "shorthand_detected": "🔵 Shorthand",
}

STATUS_EMOJI = {
    "valid_active":       "✅",
    "valid_void":         "⚠️",
    "not_found":          "❌",
    "shorthand_detected": "🔵",
}

DOC_STATUS = {
    "pass":     "✅ Pass",
    "issues":   "❌ Issues",
    "approved": "✔️ Approved",
    "pending":  "⏳ Pending",
}


def render_stepper(current: int):
    steps = [("Drop", "1"), ("Scan", "2"), ("Report", "3"), ("Decide", "4")]
    html = '<div class="stepper-wrap">'
    for i, (label, num) in enumerate(steps, 1):
        if i < current:
            node_cls = "step-done"; lbl_cls = "step-lbl-done"; node_html = "✓"
        elif i == current:
            node_cls = "step-active"; lbl_cls = "step-lbl-active"; node_html = num
        else:
            node_cls = "step-todo"; lbl_cls = "step-lbl-todo"; node_html = num
        html += f"""
        <div class="step-col">
          <div class="step-node {node_cls}">{node_html}</div>
          <div class="step-lbl {lbl_cls}">{label}</div>
        </div>"""
        if i < len(steps):
            line_cls = "step-line-done" if i < current else "step-line-todo"
            html += f'<div class="step-line {line_cls}"></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


@st.cache_resource
def ensure_db():
    init_db()
    return True
