"""Import resume data from DOCX files."""

from __future__ import annotations

import re
from pathlib import Path

from resume_forge_mcp.models.resume import (
	ContactInfo,
	Education,
	Experience,
	ResumeData,
	SkillCategory,
)


def import_from_docx(docx_path: Path) -> ResumeData:
	"""Extract resume data from a DOCX file.

	Uses python-docx to extract text, then applies heuristic parsing.

	Args:
		docx_path: Path to the DOCX file.

	Returns:
		Populated ResumeData.

	Raises:
		ImportError: If python-docx is not installed.
		FileNotFoundError: If the file doesn't exist.
	"""
	if not docx_path.exists():
		raise FileNotFoundError(f"DOCX not found: {docx_path}")

	try:
		from docx import Document
	except ImportError:
		raise ImportError(
			"python-docx is required for DOCX import. "
			"If using uvx: uvx --with python-docx resume-forge-mcp"
		)

	doc = Document(str(docx_path))
	lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

	# Reuse the same parsing logic as PDF import
	from resume_forge_mcp.storage.pdf_import import _parse_resume_text

	text = "\n".join(lines)
	return _parse_resume_text(text)
