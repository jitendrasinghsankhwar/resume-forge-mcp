"""Import existing LaTeX resume files into the data model."""

from __future__ import annotations

import re
from pathlib import Path

from latex_resume_mcp.models.resume import (
	ContactInfo,
	Education,
	Experience,
	Project,
	Publication,
	ResumeData,
	SkillCategory,
)


def _unescape_latex(text: str) -> str:
	"""Remove LaTeX escaping from text."""
	text = text.replace(r"\&", "&")
	text = text.replace(r"\%", "%")
	text = text.replace(r"\$", "$")
	text = text.replace(r"\#", "#")
	text = text.replace(r"\_", "_")
	text = text.replace(r"\textasciitilde{}", "~")
	text = text.replace(r"\textasciicircum{}", "^")
	return text.strip()


def _extract_items(block: str) -> list[str]:
	"""Extract \\resumeItem{...} contents from a block."""
	items: list[str] = []
	for match in re.finditer(r"\\resumeItem\{(.+?)\}\s*$", block, re.MULTILINE):
		items.append(match.group(1).strip())
	return items


def _extract_subheadings(section_text: str) -> list[dict[str, str | list[str]]]:
	"""Extract \\resumeSubheading entries with their items."""
	entries: list[dict[str, str | list[str]]] = []
	# Split on \resumeSubheading
	parts = re.split(r"\\resumeSubheading\s*\n", section_text)
	for part in parts[1:]:  # skip text before first subheading
		# Extract the 4 arguments: {arg1}{arg2}\n{arg3}{arg4}
		args = re.findall(r"\{([^}]*)\}", part)
		if len(args) >= 4:
			bullets = _extract_items(part)
			entries.append({
				"arg1": args[0].strip(),
				"arg2": args[1].strip(),
				"arg3": args[2].strip(),
				"arg4": args[3].strip(),
				"bullets": bullets,
			})
	return entries


def _extract_project_headings(section_text: str) -> list[dict[str, str | list[str]]]:
	"""Extract \\resumeProjectHeading entries with their items."""
	entries: list[dict[str, str | list[str]]] = []
	parts = re.split(r"\\resumeProjectHeading\s*\n", section_text)
	for part in parts[1:]:
		# The first line has {content}{date}
		first_line_match = re.match(r"\s*\{(.+?)\}\{(.+?)\}", part, re.DOTALL)
		if first_line_match:
			content = first_line_match.group(1).strip()
			date = first_line_match.group(2).strip()
			bullets = _extract_items(part)
			entries.append({
				"content": content,
				"date": date,
				"bullets": bullets,
			})
	return entries


def _parse_heading(tex: str) -> ContactInfo:
	"""Parse the heading/contact section."""
	name = ""
	phone = ""
	email = ""
	linkedin = ""
	github = ""
	website = ""

	name_match = re.search(r"\\scshape\s+(.+?)\}", tex)
	if name_match:
		name = name_match.group(1).strip()

	phone_match = re.search(r"\\small\s+([\d-]+)", tex)
	if phone_match:
		phone = phone_match.group(1).strip()

	email_match = re.search(r"\\href\{mailto:([^}]+)\}", tex)
	if email_match:
		email = email_match.group(1).strip()

	linkedin_match = re.search(r"\\underline\{(linkedin\.com[^}]+)\}", tex)
	if linkedin_match:
		linkedin = linkedin_match.group(1).strip()

	github_match = re.search(r"\\underline\{(github\.com[^}]+)\}", tex)
	if github_match:
		github = github_match.group(1).strip()

	return ContactInfo(
		name=name or "Unknown",
		phone=phone,
		email=email,
		linkedin=linkedin,
		github=github,
		website=website,
	)


def _split_sections(tex: str) -> dict[str, str]:
	"""Split document body into named sections."""
	sections: dict[str, str] = {}
	# Find all \section{Name} blocks
	parts = re.split(r"\\section\{([^}]+)\}", tex)
	# parts[0] is before first section (heading area)
	sections["_heading"] = parts[0]
	for i in range(1, len(parts), 2):
		section_name = parts[i].strip()
		section_body = parts[i + 1] if i + 1 < len(parts) else ""
		sections[section_name] = section_body
	return sections


def _parse_experience_entry(entry: dict[str, str | list[str]]) -> Experience:
	"""Convert a parsed subheading entry to an Experience."""
	bullets = entry.get("bullets", [])
	if not isinstance(bullets, list):
		bullets = []
	return Experience(
		company=str(entry.get("arg1", "")),
		location=str(entry.get("arg2", "")),
		title=str(entry.get("arg3", "")),
		date=str(entry.get("arg4", "")),
		bullets=[str(b) for b in bullets],
	)


def _parse_education_entry(entry: dict[str, str | list[str]]) -> Education:
	"""Convert a parsed subheading entry to an Education."""
	bullets = entry.get("bullets", [])
	if not isinstance(bullets, list):
		bullets = []
	return Education(
		institution=str(entry.get("arg1", "")),
		location=str(entry.get("arg2", "")),
		degree=str(entry.get("arg3", "")),
		date=str(entry.get("arg4", "")),
		bullets=[str(b) for b in bullets],
	)


def _parse_project_entry(entry: dict[str, str | list[str]]) -> Project:
	"""Convert a parsed project heading entry to a Project."""
	content = str(entry.get("content", ""))
	date = str(entry.get("date", ""))
	bullets = entry.get("bullets", [])
	if not isinstance(bullets, list):
		bullets = []

	# Parse name and tech from content like: \textbf{Name} $|$ \emph{Tech}
	name_match = re.search(r"\\textbf\{([^}]+)\}", content)
	name = name_match.group(1) if name_match else content

	tech_match = re.search(r"\\emph\{([^}]+)\}", content)
	technologies = tech_match.group(1) if tech_match else ""

	link_match = re.search(r"\\href\{([^}]+)\}", content)
	link = link_match.group(1) if link_match else ""

	return Project(
		name=name,
		technologies=technologies,
		link=link,
		date=date,
		bullets=[str(b) for b in bullets],
	)


def _parse_publication_entry(entry: dict[str, str | list[str]]) -> Publication:
	"""Convert a parsed project heading entry to a Publication."""
	content = str(entry.get("content", ""))
	date = str(entry.get("date", ""))
	bullets = entry.get("bullets", [])
	if not isinstance(bullets, list):
		bullets = []

	name_match = re.search(r"\\textbf\{([^}]+)\}", content)
	title = name_match.group(1) if name_match else content

	link_match = re.search(r"\\href\{([^}]+)\}", content)
	link = link_match.group(1) if link_match else ""

	link_text_match = re.search(r"\\underline\{([^}]+)\}", content)
	link_text = link_text_match.group(1) if link_text_match else "GitHub"

	return Publication(
		title=title,
		link=link,
		link_text=link_text,
		date=date,
		bullets=[str(b) for b in bullets],
	)


def _parse_skills(section_text: str) -> list[SkillCategory]:
	"""Parse the Technical Skills section."""
	categories: list[SkillCategory] = []
	for match in re.finditer(
		r"\\textbf\{([^}]+)\}\{:\s*([^}]+)\}", section_text
	):
		category = match.group(1).strip()
		skills_text = match.group(2).strip()
		skills = [s.strip() for s in skills_text.split(",") if s.strip()]
		categories.append(SkillCategory(category=category, skills=skills))
	return categories


def import_from_latex(tex_path: Path) -> ResumeData:
	"""Parse an existing LaTeX resume file into a ResumeData model.

	Args:
		tex_path: Path to a .tex file using Jake's Resume template format.

	Returns:
		Populated ResumeData with all extracted entries.

	Raises:
		FileNotFoundError: If the file doesn't exist.
	"""
	if not tex_path.exists():
		raise FileNotFoundError(f"LaTeX file not found: {tex_path}")

	tex = tex_path.read_text(encoding="utf-8")
	sections = _split_sections(tex)

	contact = _parse_heading(sections.get("_heading", ""))

	education: list[Education] = []
	if "Education" in sections:
		for entry in _extract_subheadings(sections["Education"]):
			education.append(_parse_education_entry(entry))

	publications: list[Publication] = []
	if "Publications" in sections:
		for entry in _extract_project_headings(sections["Publications"]):
			publications.append(_parse_publication_entry(entry))

	experience: list[Experience] = []
	if "Experience" in sections:
		for entry in _extract_subheadings(sections["Experience"]):
			experience.append(_parse_experience_entry(entry))

	projects: list[Project] = []
	if "Projects" in sections:
		for entry in _extract_project_headings(sections["Projects"]):
			projects.append(_parse_project_entry(entry))

	skills: list[SkillCategory] = []
	if "Technical Skills" in sections:
		skills = _parse_skills(sections["Technical Skills"])

	return ResumeData(
		contact=contact,
		education=education,
		publications=publications,
		experience=experience,
		projects=projects,
		skills=skills,
	)
