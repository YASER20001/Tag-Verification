import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
from db.db_sync import init_db, get_impact
from pages._shared import COMMON_CSS, STATUS_LABELS, ensure_db

st.set_page_config(page_title="Impact Analysis — Tag Verify", page_icon="🔗", layout="wide")
st.markdown(COMMON_CSS, unsafe_allow_html=True)
ensure_db()

SAMPLE_TAGS = [
    "10-P-101A", "10-P-102B", "20-HX-302", "20-XV-2004",
    "10-PSV-1004B", "10-V-203", "10-TT-1004",
]

# ---- Header ----
st.title("🔗 Impact Analysis")
st.caption("Find every document that references a tag — essential for change management when tags are voided.")

# Pre-fill from dashboard alert navigation
default_tag = st.session_state.pop("impact_tag", "")

# ---- Search input ----
with st.container(border=True):
    sc1, sc2 = st.columns([4, 1])
    with sc1:
        tag_input = st.text_input(
            "Enter Tag Number",
            value=default_tag,
            placeholder="e.g. 10-P-101A",
        ).strip().upper()
    with sc2:
        st.markdown("<br>", unsafe_allow_html=True)
        search_btn = st.button("🔍 Analyse", type="primary", use_container_width=True)

    # Quick-pick buttons
    st.caption("Quick examples:")
    cols = st.columns(len(SAMPLE_TAGS))
    for col, sample in zip(cols, SAMPLE_TAGS):
        if col.button(sample, key=f"qp_{sample}", use_container_width=True):
            tag_input = sample

# ---- Results ----
if tag_input and (search_btn or default_tag or True):
    impact = get_impact(tag_input)
    tag    = impact["tag"]
    docs   = impact["documents"]

    # Tag info card
    st.divider()
    ti1, ti2 = st.columns([3, 1])
    with ti1:
        if tag:
            status_badge = (
                '<span class="badge badge-active">✅ Active</span>'
                if tag["status"] == "Active"
                else '<span class="badge badge-voidtag">⚠️ Void</span>'
            )
            voided_note = (
                f" · Voided: **{tag['voided_at']}**" if tag["voided_at"] else ""
            )
            st.markdown(
                f"### `{tag['tag_number']}` {status_badge}",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"**{tag['tag_description']}**  \n"
                f"Discipline: **{tag['discipline']}**{voided_note}"
            )
        else:
            st.error(f"Tag **{tag_input}** is not registered in the CTDB.")

    with ti2:
        st.metric("Documents Referencing This Tag", impact["affected_count"])

    # Void impact warning
    if tag and tag["status"] == "Void" and docs:
        st.warning(
            f"🚨 **Change Management Alert** — Tag `{tag['tag_number']}` is **Void** "
            f"but is still referenced in **{len(docs)}** document(s). "
            f"These documents must be revised before re-issue."
        )

    st.divider()

    # Documents table
    st.subheader(f"Referencing Documents ({len(docs)})")
    if not docs:
        st.info(
            "No documents currently reference this tag. "
            "Documents will appear here after verification and 'Save Tag Links'."
        )
    else:
        df = pd.DataFrame(docs)
        df["Verification Status"] = df["verification_status"].map(STATUS_LABELS).fillna(
            df["verification_status"]
        )
        display = df[[
            "document_number", "document_title", "document_revision",
            "found_at", "Verification Status",
        ]].rename(columns={
            "document_number":   "Document No.",
            "document_title":    "Title",
            "document_revision": "Rev",
            "found_at":          "Verified On",
        })

        def row_color(row):
            if "Void" in row["Verification Status"]:
                return ["background:#fefce8"] * len(row)
            if "Not Found" in row["Verification Status"]:
                return ["background:#fef2f2"] * len(row)
            if "Valid" in row["Verification Status"]:
                return ["background:#f0fdf4"] * len(row)
            return [""] * len(row)

        st.dataframe(
            display.style.apply(row_color, axis=1),
            use_container_width=True, hide_index=True,
        )

elif not tag_input:
    st.info("Enter a tag number above and click **Analyse** to begin.")
