# Tag Verify — Engineering Tag Verification System

A self-service web application that allows engineers and drafters to upload project documents (PDF or images), automatically extract equipment tag numbers, compare them against a Central Tag Database (CTDB), and generate a verification report — all before the document is issued.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | Python 3.11+ + FastAPI |
| Database | SQLite (via SQLAlchemy async) |
| PDF Extraction | pdfplumber (digital), PyMuPDF + pytesseract (scanned) |
| Charts | Recharts |

---

## Project Structure

```
tag-verify/
├── client/                    # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx          # Overview & alerts
│   │   │   ├── Upload.jsx             # 4-step upload flow
│   │   │   ├── VerificationReport.jsx # Tag verification results
│   │   │   ├── TagDatabase.jsx        # CTDB admin view
│   │   │   └── ImpactAnalysis.jsx     # Tag-to-document lookup
│   │   ├── utils/
│   │   │   ├── api.js                 # Axios API calls
│   │   │   └── helpers.js             # Status configs & formatting
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
│
├── server/                    # FastAPI backend
│   ├── routes/
│   │   ├── tags.py            # CTDB CRUD + CSV import
│   │   ├── documents.py       # Upload & verification
│   │   ├── relationships.py   # Tag-document links
│   │   └── dashboard.py       # Stats & alerts
│   ├── services/
│   │   ├── pdf_extractor.py   # PDF/image text extraction
│   │   ├── tag_detector.py    # Regex + shorthand expansion
│   │   └── verifier.py        # Compare against CTDB
│   ├── db/
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   └── database.py        # DB init, session, seed data
│   ├── uploads/               # Uploaded files (auto-created)
│   └── main.py                # FastAPI app entry point
│
├── sample_docs/               # Test PDFs
│   ├── test_doc_1_should_pass.pdf
│   ├── test_doc_2_has_issues.pdf
│   └── test_doc_3_shorthand.pdf
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) Tesseract OCR for scanned PDFs: `apt install tesseract-ocr` or `brew install tesseract`

### 1. Backend

```bash
cd server
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The server will:
- Auto-create `db/tag_verify.db`
- Seed **50 sample tags** across Mechanical, Instrumentation, Electrical, and Piping disciplines

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd client
npm install
npm run dev
```

Open: http://localhost:5173

---

## Features

### Upload Flow (4 Steps)
1. **Drop** — Drag-and-drop PDF/image, enter document metadata
2. **Scan** — Text extraction + tag detection (with progress indicator)
3. **Report** — Interactive verification results with pie chart
4. **Decide** — Approve, override, or correct & recheck

### Verification Statuses
| Status | Meaning | Colour |
|--------|---------|--------|
| `valid_active` | Tag exists in CTDB and is Active | ✅ Green |
| `valid_void` | Tag exists but has been Voided | ⚠️ Amber |
| `not_found` | Tag not in CTDB | ❌ Red |
| `shorthand_detected` | Shorthand expanded (e.g. A/B/C or range) | 🔵 Blue |

### Tag Shorthand Detection
The engine detects and expands:
- **Multi-suffix**: `10-P-101A/B/C` → `10-P-101A`, `10-P-101B`, `10-P-101C`
- **Ranges**: `10-FT-1001 to 1005` → `10-FT-1001`, `10-FT-1002`, ..., `10-FT-1005`
- **Implicit prefix**: `"All tags prefixed with 10-"` followed by `P-101` → `10-P-101`

### Central Tag Database
- Search, filter by discipline/status
- Toggle Active ↔ Void with timestamp
- Add new tags
- Import from CSV (`tag_number, tag_description, discipline, status, created_by`)

### Impact Analysis
- Enter any tag number to see all documents referencing it
- Void tag alert: identifies every document that needs revision

### Dashboard
- Live stats: total tags, docs verified, pass/fail counts
- Void tag alerts with affected document count
- Recent verification history (clickable to re-open report)

---

## API Reference

```
GET    /api/tags                         List tags (search, discipline, status filters)
POST   /api/tags                         Create tag
PUT    /api/tags/:id                     Update tag (status, description)
POST   /api/tags/import                  Import CSV
GET    /api/tags/:tag_number/documents   Documents referencing tag

POST   /api/documents/upload             Upload & verify document
GET    /api/documents/:id/report         Get full verification report
POST   /api/documents/:id/approve        Approve for issue
GET    /api/documents/:doc_number/tags   All tags in document

POST   /api/relationships/create         Save tag-document links
GET    /api/relationships/impact/:tag    Impact analysis for a tag

GET    /api/dashboard/stats              Summary statistics
GET    /api/dashboard/recent             Last 10 verifications
GET    /api/dashboard/alerts             Void tags in active documents
```

---

## Test Documents

Three sample PDFs are provided in `sample_docs/`:

| File | Expected Result |
|------|----------------|
| `test_doc_1_should_pass.pdf` | ✅ PASS — all tags valid & active |
| `test_doc_2_has_issues.pdf` | ❌ ISSUES — `10-PSV-9999` not in CTDB |
| `test_doc_3_shorthand.pdf` | 🔵 Shorthand — `10-P-101A/B/C` and `10-FT-1001 to 1005` expanded |

To regenerate the PDFs: `cd sample_docs && python create_test_pdfs.py`

---

## Business Rules

1. Tag numbers are **unique** in CTDB — no duplicates
2. Voided tags are **never deleted** — only marked Void with a timestamp
3. A document with Void or Not Found tags cannot be issued without engineer override + justification
4. Tag-document relationships are created only after the user confirms verification
5. When a tag is voided, Impact Analysis immediately shows all affected documents

---

## CSV Import Format

```csv
tag_number,tag_description,discipline,status,created_by
30-P-201A,Transfer Pump A,Mechanical,Active,engineer
30-FT-3001,Flow Transmitter - Transfer Line,Instrumentation,Active,engineer
```