"""Import resume data from PDF files."""

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


def import_from_pdf(pdf_path: Path) -> ResumeData:
	"""Extract resume data from a PDF file.

	Uses pymupdf to extract text, then applies heuristic parsing to identify
	sections and entries. Works best with single-column, text-based PDFs.

	Args:
		pdf_path: Path to the PDF file.

	Returns:
		Populated ResumeData.

	Raises:
		ImportError: If pymupdf is not installed.
		FileNotFoundError: If the file doesn't exist.
	"""
	if not pdf_path.exists():
		raise FileNotFoundError(f"PDF not found: {pdf_path}")

	try:
		import pymupdf
	except ImportError:
		raise ImportError(
			"pymupdf is required for PDF import. "
			"If using uvx: uvx --with pymupdf resume-forge-mcp"
		)

	doc = pymupdf.open(str(pdf_path))
	text = "\n".join(page.get_text() for page in doc)
	doc.close()

	return _parse_resume_text(text)


def _parse_resume_text(text: str) -> ResumeData:
	"""Parse plain text extracted from a PDF into ResumeData."""
	lines = [line.strip() for line in text.splitlines()]
	sections = _split_into_sections(lines)

	contact = _parse_contact(sections.get("_header", []))
	education = _parse_education(sections.get("education", []))
	experience = _parse_experience(sections.get("experience", []))
	skills = _parse_skills(
		sections.get("skills", []) or sections.get("technical skills", [])
	)

	return ResumeData(
		contact=contact,
		education=education,
		experience=experience,
		skills=skills,
	)


def _split_into_sections(lines: list[str]) -> dict[str, list[str]]:
	"""Split lines into named sections based on common resume headings."""
	section_names = {
		"experience", "work experience", "professional experience",
		"education", "skills", "technical skills", "projects",
		"publications", "certifications", "summary", "about me",
	}

	sections: dict[str, list[str]] = {"_header": []}
	current = "_header"

	for line in lines:
		lower = line.lower().strip()
		if lower in section_names:
			current = lower
			sections.setdefault(current, [])
		else:
			sections.setdefault(current, [])
			if line.strip():
				sections[current].append(line.strip())

	return sections


def _parse_contact(lines: list[str]) -> ContactInfo:
	"""Extract contact info from header lines."""
	name = lines[0] if lines else "Unknown"
	phone = ""
	email = ""
	linkedin = ""
	github = ""

	text = " ".join(lines)

	email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
	if email_match:
		email = email_match.group()

	phone_match = re.search(r"\+?[\d\s\-().]{10,}", text)
	if phone_match:
		phone = phone_match.group().strip()

	linkedin_match = re.search(r"linkedin\.com/in/([\w-]+)", text, re.IGNORECASE)
	if linkedin_match:
		linkedin = f"https://www.linkedin.com/in/{linkedin_match.group(1)}"

	github_match = re.search(r"github\.com/([\w-]+)", text, re.IGNORECASE)
	if github_match:
		github = f"https://github.com/{github_match.group(1)}"

	return ContactInfo(
		name=name, phone=phone, email=email, linkedin=linkedin, github=github,
	)


def _parse_experience(lines: list[str]) -> list[Experience]:
	"""Parse experience section lines into Experience entries."""
	entries: list[Experience] = []
	if not lines:
		return entries

	# Heuristic: lines with dates are entry headers, indented/bulleted lines are bullets
	date_pattern = re.compile(
		r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{4}|"
		r"\d{4})\s*[-–—]\s*(Present|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{4}|\d{4})",
		re.IGNORECASE,
	)

	i = 0
	while i < len(lines):
		date_match = date_pattern.search(lines[i])
		if date_match:
			date_str = date_match.group().strip()
			header = lines[i][:date_match.start()].strip().rstrip("–—-").strip()

			# Try to split header into company/title
			company, title = header, ""
			if i + 1 < len(lines) and not date_pattern.search(lines[i + 1]):
				next_line = lines[i + 1]
				if not next_line.startswith(("•", "-", "·", "▪")):
					title = next_line
					i += 1

			# Collect bullets
			bullets: list[str] = []
			i += 1
			while i < len(lines):
				line = lines[i]
				if date_pattern.search(line):
					break
				if line.startswith(("•", "-", "·", "▪")):
					bullets.append(line.lstrip("•-·▪ ").strip())
				elif bullets and not line[0].isupper():
					bullets[-1] += " " + line
				else:
					break
				i += 1

			entries.append(Experience(
				company=company or "Unknown",
				title=title,
				date=date_str,
				bullets=bullets,
			))
		else:
			i += 1

	return entries


def _parse_education(lines: list[str]) -> list[Education]:
	"""Parse education section lines."""
	entries: list[Education] = []
	if not lines:
		return entries

	date_pattern = re.compile(r"\d{4}\s*[-–—]\s*(?:\d{4}|Present)", re.IGNORECASE)

	i = 0
	while i < len(lines):
		date_match = date_pattern.search(lines[i])
		if date_match:
			date_str = date_match.group().strip()
			institution = lines[i][:date_match.start()].strip().rstrip("–—-,").strip()
			degree = ""
			if i + 1 < len(lines) and not date_pattern.search(lines[i + 1]):
				degree = lines[i + 1]
				i += 1
			entries.append(Education(
				institution=institution or "Unknown",
				degree=degree,
				date=date_str,
			))
		i += 1

	return entries


def _parse_skills(lines: list[str]) -> list[SkillCategory]:
	"""Parse skills section lines."""
	categories: list[SkillCategory] = []
	if not lines:
		return categories

	for line in lines:
		# Pattern: "Category: skill1, skill2, skill3" or "Category — skill1, skill2"
		match = re.match(r"^([^:–—]+)[:\s–—]+(.+)$", line)
		if match:
			cat = match.group(1).strip()
			skills = [s.strip() for s in match.group(2).split(",") if s.strip()]
			if skills:
				categories.append(SkillCategory(category=cat, skills=skills))

	return categories
