"""
PDF / image text extraction service.
Strategy:
  1. PyMuPDF (fitz) for digital PDFs — primary, no cryptography dep
  2. pytesseract OCR fallback for scanned PDFs / images
Note: pdfplumber / pypdf both depend on 'cryptography' which may not be
available on all systems; they are probed lazily and used only if working.
"""
import io
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---- Primary: PyMuPDF (no cryptography dependency for text extraction) ----
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except Exception:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available")

# ---- OCR support ----
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except Exception:
    PYTESSERACT_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# ---- Fallback PDF libs (probed lazily — may fail on some systems) ----
_PDFPLUMBER_PROBED = False
_PDFPLUMBER_OK = False
_PYPDF_PROBED = False
_PYPDF_OK = False


def _try_pdfplumber(file_bytes: bytes) -> Optional[dict]:
    global _PDFPLUMBER_PROBED, _PDFPLUMBER_OK
    if not _PDFPLUMBER_PROBED:
        try:
            import pdfplumber as _pb  # noqa: F401
            _PDFPLUMBER_OK = True
        except Exception:
            _PDFPLUMBER_OK = False
        _PDFPLUMBER_PROBED = True
    if not _PDFPLUMBER_OK:
        return None
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append({"page": i, "text": text})
        full_text = "\n".join(p["text"] for p in pages)
        return {"pages": pages, "full_text": full_text, "method": "pdfplumber", "page_count": len(pages)}
    except Exception as e:
        logger.error("pdfplumber failed: %s", e)
        return None


def _try_pypdf(file_bytes: bytes) -> Optional[dict]:
    global _PYPDF_PROBED, _PYPDF_OK
    if not _PYPDF_PROBED:
        try:
            import pypdf as _pp  # noqa: F401
            _PYPDF_OK = True
        except Exception:
            _PYPDF_OK = False
        _PYPDF_PROBED = True
    if not _PYPDF_OK:
        return None
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"page": i, "text": text})
        full_text = "\n".join(p["text"] for p in pages)
        return {"pages": pages, "full_text": full_text, "method": "pypdf", "page_count": len(pages)}
    except Exception as e:
        logger.error("pypdf failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Main extraction entry point
# ---------------------------------------------------------------------------

def extract_text_from_file(file_bytes: bytes, filename: str) -> dict:
    """
    Extract text from an uploaded file.
    Returns:
        {
            "pages": [{"page": 1, "text": "..."},...],
            "full_text": "...",
            "method": "pymupdf" | "pdfplumber" | "pypdf" | "ocr" | "image_ocr" | "failed",
            "page_count": int,
        }
    """
    ext = os.path.splitext(filename.lower())[1]
    if ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"):
        return _extract_from_image(file_bytes)
    elif ext == ".pdf":
        return _extract_from_pdf(file_bytes)
    else:
        return {"pages": [], "full_text": "", "method": "unsupported", "page_count": 0}


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def _extract_from_pdf(file_bytes: bytes) -> dict:
    # 1. PyMuPDF direct text (best quality, no cryptography dep)
    if PYMUPDF_AVAILABLE:
        result = _pymupdf_text_extract(file_bytes)
        if result and result["full_text"].strip():
            return result

    # 2. pdfplumber (if available on this system)
    result = _try_pdfplumber(file_bytes)
    if result and result["full_text"].strip():
        return result

    # 3. pypdf (if available on this system)
    result = _try_pypdf(file_bytes)
    if result and result["full_text"].strip():
        return result

    # 4. OCR via PyMuPDF render + tesseract (scanned PDFs)
    if PYMUPDF_AVAILABLE and PYTESSERACT_AVAILABLE and PIL_AVAILABLE:
        return _pymupdf_ocr_extract(file_bytes)

    return {"pages": [], "full_text": "", "method": "failed", "page_count": 0}


def _pymupdf_text_extract(file_bytes: bytes) -> Optional[dict]:
    """Extract text from digital PDF using PyMuPDF's built-in parser."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            pages.append({"page": i, "text": text})
        doc.close()
        full_text = "\n".join(p["text"] for p in pages)
        return {
            "pages": pages,
            "full_text": full_text,
            "method": "pymupdf",
            "page_count": len(pages),
        }
    except Exception as e:
        logger.error("PyMuPDF text extraction failed: %s", e)
        return None


def _pymupdf_ocr_extract(file_bytes: bytes) -> dict:
    """Render PDF pages as images and run OCR (for scanned PDFs)."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(img, config="--psm 6")
            pages.append({"page": i, "text": text})
        doc.close()
        full_text = "\n".join(p["text"] for p in pages)
        return {
            "pages": pages,
            "full_text": full_text,
            "method": "ocr",
            "page_count": len(pages),
        }
    except Exception as e:
        logger.error("PyMuPDF OCR extraction failed: %s", e)
        return {"pages": [], "full_text": "", "method": "failed", "page_count": 0}


# ---------------------------------------------------------------------------
# Image extraction
# ---------------------------------------------------------------------------

def _extract_from_image(file_bytes: bytes) -> dict:
    if not (PYTESSERACT_AVAILABLE and PIL_AVAILABLE):
        return {"pages": [], "full_text": "", "method": "ocr_unavailable", "page_count": 0}
    try:
        img = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(img, config="--psm 6")
        return {
            "pages": [{"page": 1, "text": text}],
            "full_text": text,
            "method": "image_ocr",
            "page_count": 1,
        }
    except Exception as e:
        logger.error("Image OCR extraction failed: %s", e)
        return {"pages": [], "full_text": "", "method": "failed", "page_count": 0}
