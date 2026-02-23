import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db.db_sync import init_db, get_stats, get_recent_documents, get_void_alerts
from pages._shared import COMMON_CSS, DOC_STATUS, ensure_db

st.set_page_config(page_title="Dashboard — Tag Verify", page_icon="📊", layout="wide")
st.markdown(COMMON_CSS, unsafe_allow_html=True)
ensure_db()

# ---- Header ----
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.title("📊 Dashboard")
    st.caption("Engineering Tag Verification — Overview")
with col_h2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()

stats = get_stats()

# ---- Metrics ----
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Tags (CTDB)", stats["total_tags"])
c2.metric("Active Tags", stats["active_tags"],
          delta=f"{stats['active_tags']} of {stats['total_tags']}")
c3.metric("Void Tags", stats["void_tags"])
c4.metric("Documents Verified", stats["total_documents"])
c5.metric("Issues Found", stats["issue_documents"])
st.divider()

# ---- Charts + Alerts ----
chart_col, alert_col = st.columns([2, 1])

with chart_col:
    st.subheader("Tag & Document Statistics")
    categories = ["Active Tags", "Void Tags", "Docs Passed", "Docs with Issues"]
    values     = [
        stats["active_tags"],
        stats["void_tags"],
        stats["passed_documents"],
        stats["issue_documents"],
    ]
    colors = ["#16a34a", "#d97706", "#2563eb", "#dc2626"]
    fig = go.Figure(go.Bar(
        x=categories, y=values,
        marker_color=colors,
        text=values, textposition="outside",
        hovertemplate="%{x}: %{y}<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(gridcolor="#f0f0f0"),
        showlegend=False, height=280,
    )
    st.plotly_chart(fig, use_container_width=True)

with alert_col:
    st.subheader("⚠️ Void Tag Alerts")
    alerts = get_void_alerts()
    if not alerts:
        st.success("No void tag alerts.")
    else:
        for a in alerts[:8]:
            with st.container(border=True):
                st.markdown(
                    f"**`{a['tag_number']}`** — "
                    f"{a['affected_count']} doc(s) affected",
                )
                st.caption(a["tag_description"])
                if st.button("Analyse →", key=f"alert_{a['tag_number']}", use_container_width=True):
                    st.session_state["impact_tag"] = a["tag_number"]
                    st.switch_page("pages/4_🔗_Impact_Analysis.py")

st.divider()

# ---- Recent verifications ----
st.subheader("Recent Verifications")
recent = get_recent_documents(10)
if not recent:
    st.info("No documents verified yet. Go to **Verify Document** to upload one.")
else:
    df = pd.DataFrame(recent)
    df["status_label"] = df["verification_status"].map(DOC_STATUS).fillna("⏳ Pending")
    df["summary"] = (
        df["tags_valid"].astype(str) + "✅ " +
        df["tags_void"].astype(str)  + "⚠️ " +
        df["tags_not_found"].astype(str) + "❌"
    )

    display = df[[
        "document_number", "document_title", "document_revision",
        "uploaded_at", "tags_found", "summary", "status_label"
    ]].rename(columns={
        "document_number":   "Doc No.",
        "document_title":    "Title",
        "document_revision": "Rev",
        "uploaded_at":       "Uploaded",
        "tags_found":        "Tags",
        "summary":           "Breakdown",
        "status_label":      "Status",
    })

    def highlight_status(row):
        val = row["Status"]
        if "Pass" in val or "Approved" in val:
            return ["background-color:#f0fdf4"] * len(row)
        elif "Issues" in val:
            return ["background-color:#fef2f2"] * len(row)
        return [""] * len(row)

    st.dataframe(
        display.style.apply(highlight_status, axis=1),
        use_container_width=True, hide_index=True,
    )
