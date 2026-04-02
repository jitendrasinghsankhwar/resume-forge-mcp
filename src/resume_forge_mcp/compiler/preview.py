"""PDF to PNG preview rendering using PyMuPDF (optional dependency)."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
	import fitz  # type: ignore[import-untyped]  # PyMuPDF
	HAS_PYMUPDF = True
except ImportError:
	HAS_PYMUPDF = False

# Default rendering DPI for preview images
DEFAULT_DPI = 200


def render_pdf_to_png(
	pdf_path: Path,
	output_path: Path | None = None,
	dpi: int = DEFAULT_DPI,
	page_number: int = 0,
) -> bytes:
	"""Render a PDF page to PNG bytes.

	Args:
		pdf_path: Path to PDF file.
		output_path: Optional path to save the PNG file.
		dpi: Resolution for rendering (default 200).
		page_number: Which page to render (0-indexed).

	Returns:
		PNG image bytes.

	Raises:
		FileNotFoundError: If PDF doesn't exist.
		ImportError: If pymupdf is not installed.
	"""
	if not HAS_PYMUPDF:
		raise ImportError("pymupdf is required for preview. Install with: pip install resume-forge-mcp[preview]")

	if not pdf_path.exists():
		raise FileNotFoundError(f"PDF not found: {pdf_path}")

	doc = fitz.open(str(pdf_path))
	try:
		if page_number >= len(doc):
			raise ValueError(
				f"Page {page_number} out of range (document has {len(doc)} pages)"
			)

		page = doc[page_number]
		zoom = dpi / 72.0
		mat = fitz.Matrix(zoom, zoom)
		pix = page.get_pixmap(matrix=mat)
		png_bytes: bytes = pix.tobytes("png")

		if output_path:
			output_path.parent.mkdir(parents=True, exist_ok=True)
			output_path.write_bytes(png_bytes)

		return png_bytes
	finally:
		doc.close()


def get_pdf_info(pdf_path: Path) -> dict[str, object]:
	"""Get basic info about a PDF file.

	Args:
		pdf_path: Path to PDF file.

	Returns:
		Dict with page_count, width, height (of first page in points).
	"""
	if not HAS_PYMUPDF:
		raise ImportError("pymupdf is required for PDF info. Install with: pip install resume-forge-mcp[preview]")

	if not pdf_path.exists():
		raise FileNotFoundError(f"PDF not found: {pdf_path}")

	doc = fitz.open(str(pdf_path))
	try:
		page_count = len(doc)
		if page_count > 0:
			page = doc[0]
			rect = page.rect
			width = rect.width
			height = rect.height
		else:
			width = 0.0
			height = 0.0

		return {
			"page_count": page_count,
			"width_pt": width,
			"height_pt": height,
			"width_in": round(width / 72.0, 2),
			"height_in": round(height / 72.0, 2),
		}
	finally:
		doc.close()
