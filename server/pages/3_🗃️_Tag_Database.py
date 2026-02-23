import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
from db.db_sync import init_db, get_tags, create_tag, toggle_tag_status, import_tags_csv
from pages._shared import COMMON_CSS, ensure_db

st.set_page_config(page_title="Tag Database — Tag Verify", page_icon="🗃️", layout="wide")
st.markdown(COMMON_CSS, unsafe_allow_html=True)
ensure_db()

DISCIPLINES = ["Mechanical", "Electrical", "Instrumentation", "Piping", "Civil", "Process"]

# ---- Header ----
h1, h2 = st.columns([4, 1])
with h1:
    st.title("🗃️ Central Tag Database (CTDB)")
with h2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ---- Sidebar filters ----
with st.sidebar:
    st.markdown("### Filters")
    search     = st.text_input("🔍 Search tag / description", "")
    discipline = st.selectbox("Discipline", ["All"] + DISCIPLINES)
    status     = st.selectbox("Status", ["All", "Active", "Void"])

disc_filter   = "" if discipline == "All" else discipline
status_filter = "" if status == "All" else status

tags, total = get_tags(
    search=search,
    discipline=disc_filter,
    status=status_filter,
)

st.caption(f"Showing {len(tags)} of {total} tags")

# ---- Tag table ----
if tags:
    df = pd.DataFrame(tags)
    df["Status Badge"] = df["status"].apply(
        lambda s: "✅ Active" if s == "Active" else "⚠️ Void"
    )
    display = df[[
        "tag_number", "tag_description", "discipline",
        "Status Badge", "created_at", "voided_at", "created_by",
    ]].rename(columns={
        "tag_number":       "Tag Number",
        "tag_description":  "Description",
        "discipline":       "Discipline",
        "created_at":       "Created",
        "voided_at":        "Voided",
        "created_by":       "Created By",
    })

    def row_style(row):
        if row["Status Badge"] == "⚠️ Void":
            return ["opacity:0.7; background:#fffbeb"] * len(row)
        return [""] * len(row)

    st.dataframe(
        display.style.apply(row_style, axis=1),
        use_container_width=True, hide_index=True, height=420,
    )
else:
    st.info("No tags match the current filters.")

st.divider()

# ---- Actions row ----
tab_add, tab_toggle, tab_import = st.tabs(["➕ Add Tag", "🔄 Toggle Status", "📥 Import CSV"])

# ---- Add Tag ----
with tab_add:
    with st.form("add_tag_form", clear_on_submit=True):
        st.subheader("Add New Tag")
        c1, c2 = st.columns(2)
        with c1:
            new_tag    = st.text_input("Tag Number *", placeholder="e.g. 10-P-105A").upper()
            new_desc   = st.text_input("Description",  placeholder="Equipment description")
        with c2:
            new_disc   = st.selectbox("Discipline", [""] + DISCIPLINES)
            new_status = st.selectbox("Status", ["Active", "Void"])
            new_by     = st.text_input("Created By", value="admin")

        submitted = st.form_submit_button("Create Tag", type="primary")
        if submitted:
            if not new_tag.strip():
                st.error("Tag number is required.")
            else:
                try:
                    create_tag(new_tag.strip(), new_desc, new_disc, new_status, new_by or "admin")
                    st.success(f"✅ Tag **{new_tag.strip()}** created successfully.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

# ---- Toggle Status ----
with tab_toggle:
    st.subheader("Toggle Tag Status (Active ↔ Void)")
    st.caption(
        "Enter the tag number and click Toggle. "
        "Voiding a tag records a timestamp and will appear in Impact Analysis alerts."
    )
    col_t, col_b = st.columns([3, 1])
    with col_t:
        toggle_input = st.text_input("Tag Number to toggle", placeholder="e.g. 10-P-102B").upper()
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        do_toggle = st.button("🔄 Toggle Status", type="primary", use_container_width=True)

    if do_toggle and toggle_input.strip():
        # Find tag id
        match, _ = get_tags(search=toggle_input.strip())
        exact = [t for t in match if t["tag_number"] == toggle_input.strip()]
        if not exact:
            st.error(f"Tag **{toggle_input.strip()}** not found in CTDB.")
        else:
            tag_id   = exact[0]["id"]
            new_stat = toggle_tag_status(tag_id)
            st.success(
                f"Tag **{toggle_input.strip()}** is now **{new_stat}**."
            )
            st.rerun()

# ---- Import CSV ----
with tab_import:
    st.subheader("Import Tags from CSV")
    st.code("tag_number,tag_description,discipline,status,created_by", language="text")
    st.caption("Column names must match exactly (case-sensitive headers).")

    csv_file = st.file_uploader("Upload CSV file", type=["csv"], key="csv_import")
    if csv_file:
        if st.button("Import", type="primary"):
            result = import_tags_csv(csv_file.read())
            st.success(
                f"Import complete — **{result['created']}** tags created, "
                f"**{result['skipped']}** skipped (duplicates)."
            )
            st.rerun()
