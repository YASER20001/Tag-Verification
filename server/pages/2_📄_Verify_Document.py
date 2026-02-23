import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import plotly.express as px
from db.db_sync import (
    init_db, verify_tags_sync, summarise, save_document,
    approve_document, create_relationships,
)
from services.pdf_extractor import extract_text_from_file
from services.tag_detector import extract_tags_from_text, flatten_detected_tags
from pages._shared import COMMON_CSS, STATUS_LABELS, STATUS_EMOJI, render_stepper, ensure_db

st.set_page_config(page_title="Verify Document — Tag Verify", page_icon="📄", layout="wide")
st.markdown(COMMON_CSS, unsafe_allow_html=True)
ensure_db()

# ---- Session state defaults ----
for key, default in {
    "step": 1,
    "verified_tags": None,
    "summary": None,
    "doc_id": None,
    "extraction_method": "",
    "page_count": 0,
    "relationships_saved": False,
    "approved": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def reset():
    for k in ["step", "verified_tags", "summary", "doc_id",
              "extraction_method", "page_count", "relationships_saved", "approved"]:
        del st.session_state[k]
    st.rerun()


# ---- Header ----
st.title("📄 Verify Document")
st.caption("Upload a document to extract and verify tag numbers against the CTDB")

render_stepper(st.session_state["step"])

# ===========================================================================
# STEP 1 — Upload
# ===========================================================================
if st.session_state["step"] == 1:
    with st.container(border=True):
        st.subheader("Step 1 — Upload Document")

        uploaded = st.file_uploader(
            "Drag and drop a file here, or click Browse",
            type=["pdf", "png", "jpg", "jpeg", "tiff", "tif"],
            help="PDF, PNG, JPG, TIFF up to 50 MB",
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            doc_number = st.text_input(
                "Document Number *",
                placeholder="e.g. P&ID-10-001",
                help="Required — unique identifier for this document",
            )
        with c2:
            doc_title = st.text_input("Document Title", placeholder="e.g. Feed Water System P&ID")
        with c3:
            doc_revision = st.text_input("Revision", placeholder="e.g. A, B, 0, 1")

        col_btn, col_hint = st.columns([2, 5])
        with col_btn:
            start = st.button(
                "▶ Start Verification",
                type="primary",
                use_container_width=True,
                disabled=not (uploaded and doc_number.strip()),
            )
        with col_hint:
            if not uploaded:
                st.caption("⬆ Select a file to begin")
            elif not doc_number.strip():
                st.caption("📋 Enter a document number to continue")
            else:
                st.caption(f"✅ Ready — {uploaded.name} ({uploaded.size / 1024:.0f} KB)")

    if start and uploaded and doc_number.strip():
        st.session_state["_pending_upload"] = {
            "file_bytes": uploaded.read(),
            "filename": uploaded.name,
            "doc_number": doc_number.strip(),
            "doc_title": doc_title.strip(),
            "doc_revision": doc_revision.strip(),
        }
        st.session_state["step"] = 2
        st.rerun()


# ===========================================================================
# STEP 2 — Scan (processing happens here)
# ===========================================================================
elif st.session_state["step"] == 2:
    pending = st.session_state.get("_pending_upload", {})
    if not pending:
        st.warning("No upload pending. Please start from Step 1.")
        if st.button("← Back"):
            st.session_state["step"] = 1
            st.rerun()
        st.stop()

    with st.spinner("🔍 Extracting text and detecting tag numbers…"):
        file_bytes = pending["file_bytes"]
        filename   = pending["filename"]

        # Extract text
        extraction  = extract_text_from_file(file_bytes, filename)
        full_text   = extraction["full_text"]

        # Detect tags
        detected    = extract_tags_from_text(full_text)
        flat_tags   = flatten_detected_tags(detected)

        # Annotate page numbers
        page_tag_map = {}
        for pg in extraction.get("pages", []):
            pnum = pg["page"]
            for t in flatten_detected_tags(extract_tags_from_text(pg["text"])):
                if t["tag_number"] not in page_tag_map:
                    page_tag_map[t["tag_number"]] = pnum
        for t in flat_tags:
            t["page_number"] = page_tag_map.get(t["tag_number"])

        # Verify
        verified = verify_tags_sync(flat_tags)
        summary  = summarise(verified)

        # Persist document record
        doc_id = save_document(
            pending["doc_number"], pending["doc_title"],
            pending["doc_revision"], filename, summary,
        )

    # Store results and advance
    st.session_state["verified_tags"]     = verified
    st.session_state["summary"]           = summary
    st.session_state["doc_id"]            = doc_id
    st.session_state["extraction_method"] = extraction["method"]
    st.session_state["page_count"]        = extraction["page_count"]
    st.session_state["step"]              = 3
    st.rerun()


# ===========================================================================
# STEP 3 / 4 — Report & Decide
# ===========================================================================
elif st.session_state["step"] in (3, 4):
    verified = st.session_state["verified_tags"]
    summary  = st.session_state["summary"]
    pending  = st.session_state.get("_pending_upload", {})
    is_pass  = summary["overall_status"] == "pass"
    approved = st.session_state["approved"]

    # ---- Document banner ----
    with st.container(border=True):
        b1, b2 = st.columns([3, 1])
        with b1:
            st.markdown(
                f"**`{pending.get('doc_number','—')}`**  "
                f"{('Rev ' + pending['doc_revision']) if pending.get('doc_revision') else ''}  \n"
                f"{pending.get('doc_title','')}  \n"
                f"<small style='color:#94a3b8'>{pending.get('filename','')} · "
                f"{st.session_state['page_count']} page(s) · "
                f"extracted via {st.session_state['extraction_method']}</small>",
                unsafe_allow_html=True,
            )
        with b2:
            if is_pass:
                st.success("✅ PASS — All Tags Valid")
            elif approved:
                st.info("✔️ Approved (with override)")
            else:
                st.error("❌ ISSUES FOUND")

    # ---- Summary metrics + pie ----
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Tags",     summary["total"])
    m2.metric("✅ Valid Active", summary["valid_active"])
    m3.metric("⚠️ Valid Void",  summary["valid_void"])
    m4.metric("❌ Not Found",   summary["not_found"])
    m5.metric("🔵 Shorthand",   summary["shorthand_detected"])

    if summary["total"] > 0:
        labels = ["Valid Active", "Valid Void", "Not Found", "Shorthand"]
        values = [
            summary["valid_active"],
            summary["valid_void"],
            summary["not_found"],
            summary["shorthand_detected"],
        ]
        pie_colors = ["#16a34a", "#d97706", "#dc2626", "#2563eb"]
        nonzero_labels = [l for l, v in zip(labels, values) if v > 0]
        nonzero_values = [v for v in values if v > 0]
        nonzero_colors = [c for c, v in zip(pie_colors, values) if v > 0]

        pie_fig = px.pie(
            names=nonzero_labels, values=nonzero_values,
            color_discrete_sequence=nonzero_colors, hole=0.4,
        )
        pie_fig.update_layout(
            margin=dict(l=0, r=0, t=20, b=0), height=220,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        )
        st.plotly_chart(pie_fig, use_container_width=False)

    st.divider()

    # ---- Tag table ----
    st.subheader(f"Tag Details ({len(verified)} tags)")

    status_filter = st.selectbox(
        "Filter by status",
        ["All", "✅ Valid Active", "⚠️ Valid Void", "❌ Not Found", "🔵 Shorthand"],
        horizontal=True if hasattr(st, "radio") else False,
    )
    status_map = {
        "All": None,
        "✅ Valid Active": "valid_active",
        "⚠️ Valid Void":  "valid_void",
        "❌ Not Found":   "not_found",
        "🔵 Shorthand":   "shorthand_detected",
    }
    filter_key = status_map[status_filter]
    rows = verified if filter_key is None else [t for t in verified if t["verification_status"] == filter_key]

    STATUS_COLOR_MAP = {
        "valid_active":       "background-color:#f0fdf4",
        "valid_void":         "background-color:#fefce8",
        "not_found":          "background-color:#fef2f2",
        "shorthand_detected": "background-color:#eff6ff",
    }

    if rows:
        df = pd.DataFrame(rows)
        df["Status"] = df["verification_status"].map(STATUS_LABELS)
        df["Shorthand?"] = df["is_shorthand"].map({True: "Yes", False: ""})
        df["Original"] = df.apply(
            lambda r: r["original_shorthand"] if r["is_shorthand"] and r["original_shorthand"] else "",
            axis=1,
        )
        display = df[[
            "tag_number", "ctdb_description", "ctdb_discipline",
            "Status", "page_number", "Shorthand?", "Original",
        ]].rename(columns={
            "tag_number":       "Tag Number",
            "ctdb_description": "Description (CTDB)",
            "ctdb_discipline":  "Discipline",
            "page_number":      "Page",
        })

        def row_color(row):
            st_key = None
            for k, v in STATUS_LABELS.items():
                if v == row["Status"]:
                    st_key = k
                    break
            bg = STATUS_COLOR_MAP.get(st_key, "")
            return [bg] * len(row)

        st.dataframe(
            display.style.apply(row_color, axis=1),
            use_container_width=True, hide_index=True, height=400,
        )
    else:
        st.info("No tags match the selected filter.")

    st.divider()

    # ---- Action buttons ----
    st.subheader("Step 4 — Decide")
    act1, act2, act3, act4 = st.columns(4)

    with act1:
        if st.button("🔄 Correct & Recheck", use_container_width=True):
            reset()

    with act2:
        if st.button("💾 Save Tag Links", use_container_width=True,
                     disabled=st.session_state["relationships_saved"]):
            n = create_relationships(st.session_state["doc_id"], verified)
            st.session_state["relationships_saved"] = True
            st.success(f"Saved {n} tag-document relationships.")

    with act3:
        if not is_pass and not approved:
            with st.popover("⚠️ Override & Issue", use_container_width=True):
                st.warning("This document has unresolved tag issues.")
                justification = st.text_area("Justification *", key="override_just")
                if st.button("Confirm Override", type="primary", key="confirm_override"):
                    if justification.strip():
                        approve_document(
                            st.session_state["doc_id"], "engineer", justification.strip()
                        )
                        st.session_state["approved"] = True
                        st.session_state["step"] = 4
                        st.rerun()
                    else:
                        st.error("Please enter a justification.")

    with act4:
        if is_pass and not approved:
            if st.button("✅ Proceed to Issue", type="primary", use_container_width=True):
                approve_document(st.session_state["doc_id"], "engineer")
                st.session_state["approved"] = True
                st.session_state["step"] = 4
                st.rerun()
        elif approved:
            st.success("✔️ Document approved")
