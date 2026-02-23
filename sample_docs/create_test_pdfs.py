#!/usr/bin/env python3
"""
Generate three test PDF documents for the Tag Verify prototype.
Run:  pip install reportlab && python create_test_pdfs.py
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
import os

OUT = os.path.dirname(__file__)


def make_pdf(filename, title, doc_number, revision, body_text):
    path = os.path.join(OUT, filename)
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]

    header_data = [
        ["Document No.:", doc_number, "Revision:", revision],
        ["Title:", title, "Status:", "DRAFT"],
        ["Project:", "Unit 10/20 Process Plant", "Date:", "2024-03-15"],
    ]
    header_table = Table(header_data, colWidths=[3.5*cm, 7*cm, 2.5*cm, 4*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1e2a6e")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#1e2a6e")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))

    story = []
    story.append(header_table)
    story.append(Spacer(1, 0.6*cm))

    # Title
    story.append(Paragraph(title, h1))
    story.append(Spacer(1, 0.4*cm))

    # Body paragraphs
    para_style = ParagraphStyle(
        "body", parent=normal, fontSize=10, leading=16,
        spaceAfter=10, fontName="Helvetica"
    )
    for para in body_text:
        story.append(Paragraph(para, para_style))

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("<b>End of Document</b>", normal))

    doc.build(story)
    print(f"Created: {path}")


# ---- Test Doc 1: Should PASS ----
make_pdf(
    "test_doc_1_should_pass.pdf",
    "Feed Water & Cooling System — Functional Description",
    "FD-10-001",
    "A",
    [
        "<b>1. Scope</b>",
        "This document describes the functional requirements for the feed water system and cooling "
        "water circuit associated with Unit 10 of the process plant.",
        "<b>2. Feed Water System</b>",
        "The feed water system consists of two centrifugal pumps, 10-P-101A and 10-P-101B, "
        "operating in a duty/standby configuration. Pump discharge flow is monitored by flow "
        "transmitter 10-FT-1001. Discharge pressure is measured by 10-PT-1001.",
        "Feed water temperature at the inlet is monitored by temperature transmitter 10-TT-1001, "
        "and at the outlet by 10-TT-1002. Overpressure protection is provided by 10-PSV-1001 on "
        "the pump discharge header.",
        "<b>3. Cooling Water Circuit</b>",
        "Heat exchanger 20-E-301 provides primary cooling for process fluids. Cooling water flow "
        "is controlled by 20-FCV-2001 and metered by 20-FT-2001. Note: use the shell-and-tube "
        "heat exchanger 20-HX-301 for secondary duty.",
        "<b>4. Instrumentation Summary</b>",
        "The following instruments are installed on this system: 10-LT-1001 (feed vessel level), "
        "10-LT-1002 (condensate vessel level), 10-TT-1003 (cooling water temperature), and "
        "10-PT-1002 (feed header pressure). The motor control centre for this unit is 10-MCC-101.",
        "<b>5. Motor Drives</b>",
        "Feed pumps 10-P-101A and 10-P-101B are driven by electric motors 10-MTR-101A and "
        "10-MTR-101B respectively. Both motors are fed from 10-MCC-101.",
    ]
)

# ---- Test Doc 2: Should have ISSUES (10-PSV-9999 not in CTDB) ----
make_pdf(
    "test_doc_2_has_issues.pdf",
    "Pre-Commissioning Checklist — Feed & Fuel System",
    "CHK-10-002",
    "B",
    [
        "<b>1. Purpose</b>",
        "This checklist shall be completed prior to commissioning of the feed water and fuel gas "
        "systems on Unit 10.",
        "<b>2. Feed Water Pump Checks</b>",
        "Verify installation and alignment of pumps 10-P-101A and 10-P-101B. Check mechanical "
        "seals, alignment reports, and lube oil level on lube oil tank 10-TK-102.",
        "<b>3. Valve Lineup</b>",
        "Install valve 20-XV-2001 downstream of 10-P-101A. Confirm that shutdown valve "
        "20-XV-2002 is in the closed position prior to line fill.",
        "<b>4. Pressure Relief Checks</b>",
        "Check pressure safety valve 10-PSV-9999 before commissioning. Verify set-point and "
        "confirm lift pressure. Also check 10-PSV-1001 and 10-PSV-1002 are correctly installed.",
        "<b>5. Instrumentation Checks</b>",
        "Loop check all instruments including 10-FT-1001, 10-FT-1002, 10-PT-1001, and "
        "10-TT-1001. Confirm signals are received at 10-MCC-101.",
        "<b>6. Note</b>",
        "Tag 10-PSV-9999 referenced in Section 4 must be verified against the Central Tag "
        "Database before this document can be issued. If no record exists, raise a Tag Query "
        "through the project document controller.",
    ]
)

# ---- Test Doc 3: Has shorthand notation ----
make_pdf(
    "test_doc_3_shorthand.pdf",
    "Inspection & Test Plan — Pumps and Instruments",
    "ITP-10-003",
    "0",
    [
        "<b>1. Scope</b>",
        "This Inspection and Test Plan covers rotating equipment and instrumentation installed "
        "within Unit 10 process plant.",
        "<b>2. Pump Testing</b>",
        "All pumps 10-P-101A/B/C shall be hydrostatically tested at 1.5 times design pressure "
        "prior to installation. Performance curve testing is required for 10-P-101A and "
        "10-P-101B in accordance with API 610.",
        "Chemical dosing pump 10-P-103 shall be calibrated against the vendor data sheet.",
        "<b>3. Instrument Calibration</b>",
        "Instruments 10-FT-1001 to 1005 require calibration prior to loop check. Calibration "
        "certificates shall be submitted to the document controller within 5 days of completion.",
        "Temperature transmitters 10-TT-1001 to 1003 shall be calibrated against a certified "
        "reference standard. Level transmitters 10-LT-1001, 10-LT-1002, and 10-LT-1003 shall "
        "be calibrated using a water column.",
        "<b>4. Pressure Safety Valves</b>",
        "Pressure safety valves 10-PSV-1001, 10-PSV-1002, 10-PSV-1003, and 10-PSV-1004A/B "
        "shall be bench-tested and certified by an approved PSV workshop prior to installation.",
        "<b>5. Strainers</b>",
        "Y-strainer 10-STR-101 and duplex strainer 10-STR-102 shall be flushed and inspected "
        "prior to commissioning.",
    ]
)

print("\nAll test PDFs created successfully.")
print("Upload these files to the Tag Verify application to test the verification flow.")
