"""Jinja2 template engine for LaTeX resume rendering."""

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from latex_resume_mcp.models.resume import (
	Education,
	Experience,
	Project,
	Publication,
	ResumeData,
	ResumeVariant,
	SkillCategory,
)

TEMPLATE_DIR = Path(__file__).parent
TEMPLATE_NAME = "jake_resume.tex.j2"

# Characters that need escaping in LaTeX
LATEX_SPECIAL = {
	"&": r"\&",
	"%": r"\%",
	"$": r"\$",
	"#": r"\#",
	"_": r"\_",
	"~": r"\textasciitilde{}",
	"^": r"\textasciicircum{}",
}

# Characters that should NOT be escaped (they're intentional LaTeX)
LATEX_PASSTHROUGH_PATTERNS = [
	r"\\textbf\{",
	r"\\textit\{",
	r"\\emph\{",
	r"\\href\{",
	r"\\underline\{",
	r"\\\$",
	r"\\&",
	r"\\%",
	r"\\#",
	r"\\_",
]


def escape_latex(text: str) -> str:
	"""Escape special LaTeX characters in user-provided text.

	Handles the common case where text contains & or % that aren't
	intended as LaTeX commands. Leaves already-escaped sequences alone.
	"""
	if not text:
		return text

	# Don't escape text that already contains LaTeX commands
	for pattern in LATEX_PASSTHROUGH_PATTERNS:
		if re.search(pattern, text):
			return text

	result = []
	i = 0
	while i < len(text):
		char = text[i]
		if char == "\\" and i + 1 < len(text):
			# Already escaped, pass through
			result.append(char)
			result.append(text[i + 1])
			i += 2
		elif char in LATEX_SPECIAL:
			result.append(LATEX_SPECIAL[char])
			i += 1
		else:
			result.append(char)
			i += 1
	return "".join(result)


def _resolve_variant(data: ResumeData, variant: ResumeVariant) -> dict[str, object]:
	"""Resolve a variant's index selections into actual content lists."""
	education: list[Education] = []
	for idx in variant.education_indices:
		if 0 <= idx < len(data.education):
			education.append(data.education[idx])
	if not education:
		education = list(data.education)

	publications: list[Publication] = []
	for idx in variant.publication_indices:
		if 0 <= idx < len(data.publications):
			publications.append(data.publications[idx])
	if not publications and data.publications:
		publications = list(data.publications)

	experience: list[Experience] = []
	for idx in variant.experience_indices:
		if 0 <= idx < len(data.experience):
			experience.append(data.experience[idx])
	if not experience:
		experience = list(data.experience)

	projects: list[Project] = []
	for idx in variant.project_indices:
		if 0 <= idx < len(data.projects):
			projects.append(data.projects[idx])
	if not projects:
		projects = list(data.projects)

	skills: list[SkillCategory] = variant.skills_override or list(data.skills)

	# Apply bullet overrides
	for key, bullets in variant.bullet_overrides.items():
		parts = key.split("_")
		if len(parts) != 2:
			continue
		section, idx_str = parts
		try:
			idx = int(idx_str)
		except ValueError:
			continue

		if section == "experience" and 0 <= idx < len(experience):
			experience[idx] = experience[idx].model_copy(update={"bullets": bullets})
		elif section == "project" and 0 <= idx < len(projects):
			projects[idx] = projects[idx].model_copy(update={"bullets": bullets})

	return {
		"education": education,
		"publications": publications,
		"experience": experience,
		"projects": projects,
		"skills": skills,
		"section_order": variant.section_order,
	}


def create_jinja_env() -> Environment:
	"""Create a Jinja2 environment with LaTeX-safe delimiters."""
	env = Environment(  # nosec B701 - LaTeX output, not HTML
		loader=FileSystemLoader(str(TEMPLATE_DIR)),
		block_start_string="<%",
		block_end_string="%>",
		variable_start_string="<<",
		variable_end_string=">>",
		comment_start_string="<#",
		comment_end_string="#>",
		autoescape=False,
		trim_blocks=True,
		lstrip_blocks=True,
	)
	env.filters["latex"] = escape_latex
	return env


def render_resume(
	data: ResumeData,
	variant: ResumeVariant | None = None,
) -> str:
	"""Render a resume to LaTeX source using the Jinja2 template.

	Args:
		data: Master resume data pool.
		variant: Optional variant for content selection. If None, uses all content.

	Returns:
		Complete LaTeX source string.
	"""
	env = create_jinja_env()
	template = env.get_template(TEMPLATE_NAME)

	if variant:
		resolved = _resolve_variant(data, variant)
	else:
		resolved = {
			"education": data.education,
			"publications": data.publications,
			"experience": data.experience,
			"projects": data.projects,
			"skills": data.skills,
			"section_order": [
				"education",
				"publications",
				"experience",
				"projects",
				"skills",
			],
		}

	return template.render(
		contact=data.contact,
		**resolved,
	)
