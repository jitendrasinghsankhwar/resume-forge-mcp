"""LaTeX Resume MCP Server - Intelligent resume generation with visual verification."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP, Image

from resume_forge_mcp.compiler.latex import compile_latex
from resume_forge_mcp.compiler.preview import render_pdf_to_png
from resume_forge_mcp.intelligence.analyzer import score_resume
from resume_forge_mcp.intelligence.tailoring import (
	generate_tailored_variant,
)
from resume_forge_mcp.models.resume import (
	ContactInfo,
	Education,
	Experience,
	Project,
	Publication,
	SkillCategory,
)
from resume_forge_mcp.storage.resume_store import ResumeStore
from resume_forge_mcp.storage.tex_import import import_from_latex
from resume_forge_mcp.templates.engine import BUILTIN_TEMPLATES, render_resume

logger = logging.getLogger(__name__)


def _base_dir() -> Path:
	try:
		return Path.home() / ".resume-forge"
	except Exception:
		return Path("/tmp/resume-forge")


def _get_data_dir() -> Path:
	env_dir = os.environ.get("RESUME_DATA_DIR")
	if env_dir:
		return Path(env_dir)
	return _base_dir() / "data"


def _get_template_dir() -> Path:
	env_dir = os.environ.get("RESUME_TEMPLATE_DIR")
	if env_dir:
		return Path(env_dir)
	return _base_dir() / "templates"


def _get_output_dir() -> Path:
	env_dir = os.environ.get("RESUME_OUTPUT_DIR")
	if env_dir:
		return Path(env_dir)
	return _base_dir() / "output"


def _get_store() -> ResumeStore:
	data_dir = _get_data_dir()
	try:
		data_dir.mkdir(parents=True, exist_ok=True)
	except OSError:
		pass
	return ResumeStore(data_dir)


def _ensure_dir(d: Path) -> Path:
	try:
		d.mkdir(parents=True, exist_ok=True)
	except OSError:
		pass
	return d


mcp = FastMCP("resume-forge")


# =============================================================================
# 1. get_config
# =============================================================================


@mcp.tool()
def get_config() -> str:
	"""Show current configuration and tool availability.

	Returns:
		JSON with configuration details.
	"""
	store = _get_store()
	output_dir = _ensure_dir(_get_output_dir())
	template_dir = _ensure_dir(_get_template_dir())

	has_data = store.load_data() is not None

	from resume_forge_mcp.compiler.latex import _find_pdflatex
	pdflatex = _find_pdflatex()

	return json.dumps({
		"data_directory": str(store.data_path.parent),
		"template_directory": str(template_dir),
		"output_directory": str(output_dir),
		"has_resume_data": has_data,
		"pdflatex_available": pdflatex is not None,
		"pdflatex_path": pdflatex,
		"tools_available": [
			"get_config",
			"list_templates",
			"browse_overleaf_templates",
			"fetch_overleaf_template",
			"import_resume",
			"get_resume_data",
			"update_resume_data",
			"generate_resume",
			"compile_and_preview",
			"score_resume_quality",
			"generate_tailored_resume",
		],
	}, indent=2)


# =============================================================================
# 2. list_templates
# =============================================================================


@mcp.tool()
def list_templates() -> str:
	"""List available resume templates.

	Shows built-in templates for generate_resume, plus info on
	fetching additional templates from Overleaf dynamically.

	Returns:
		JSON with built-in templates and Overleaf integration details.
	"""
	builtin = {name: info["description"] for name, info in BUILTIN_TEMPLATES.items()}

	return json.dumps({
		"builtin_templates": builtin,
		"overleaf": {
			"description": "Browse and fetch 350+ templates dynamically from Overleaf",
			"browse_tool": "browse_overleaf_templates",
			"fetch_tool": "fetch_overleaf_template",
		},
	}, indent=2)


# =============================================================================
# 3. browse_overleaf_templates
# =============================================================================


@mcp.tool()
def browse_overleaf_templates(tag: str = "cv", page: int = 1) -> str:
	"""Browse Overleaf's template gallery to discover LaTeX templates.

	Args:
		tag: Gallery category (cv, cover-letter, report, presentation, etc.)
		page: Page number (1-indexed).

	Returns:
		JSON with list of templates (name, url) and pagination info.
	"""
	from resume_forge_mcp.overleaf import browse_gallery, get_gallery_page_count

	try:
		templates = browse_gallery(tag=tag, page=page)
		total_pages = get_gallery_page_count(tag=tag) if page == 1 else None

		result: dict[str, object] = {
			"tag": tag,
			"page": page,
			"templates": templates,
			"count": len(templates),
		}
		if total_pages:
			result["total_pages"] = total_pages

		return json.dumps(result, indent=2)
	except Exception as e:
		return json.dumps({"error": f"Failed to browse gallery: {str(e)}"})


# =============================================================================
# 4. fetch_overleaf_template
# =============================================================================


@mcp.tool()
def fetch_overleaf_template(template_url: str, save_as: str | None = None) -> str:
	"""Fetch LaTeX source code from an Overleaf template page.

	Args:
		template_url: Full Overleaf template URL.
		save_as: Optional filename to save locally (without .tex extension).

	Returns:
		JSON with template name, source code (or saved path), and status.
	"""
	from resume_forge_mcp.overleaf import fetch_template_source, save_template_locally

	try:
		if save_as:
			template_dir = _ensure_dir(_get_template_dir())
			result = save_template_locally(template_url, template_dir, save_as)
		else:
			result = fetch_template_source(template_url)

		return json.dumps(result, indent=2, default=str)
	except Exception as e:
		return json.dumps({"error": f"Failed to fetch template: {str(e)}"})


# =============================================================================
# 5. import_resume
# =============================================================================


@mcp.tool()
def import_resume(file_path: str) -> str:
	"""Import resume data from a file (PDF, DOCX, or LaTeX .tex).

	Parses the file and extracts contact, education, experience, projects,
	and skills into structured data. The imported data becomes the master
	resume pool used by generate_resume.

	Args:
		file_path: Absolute path to the file (.tex, .pdf, or .docx).

	Returns:
		JSON with import status and summary of extracted entries.
	"""
	store = _get_store()
	path = Path(file_path).expanduser()

	if not path.exists():
		return json.dumps({"error": f"File not found: {file_path}"})

	ext = path.suffix.lower()

	try:
		if ext == ".tex":
			data = import_from_latex(path)
		elif ext == ".pdf":
			from resume_forge_mcp.storage.pdf_import import import_from_pdf
			data = import_from_pdf(path)
		elif ext in (".docx", ".doc"):
			from resume_forge_mcp.storage.docx_import import import_from_docx
			data = import_from_docx(path)
		else:
			return json.dumps({"error": f"Unsupported file type: {ext}. Use .tex, .pdf, or .docx"})

		store.save_data(data)

		return json.dumps({
			"success": True,
			"imported_from": str(path),
			"format": ext,
			"entries": {
				"education": len(data.education),
				"experience": len(data.experience),
				"projects": len(data.projects),
				"publications": len(data.publications),
				"skill_categories": len(data.skills),
			},
			"contact": data.contact.name,
		}, indent=2)
	except Exception as e:
		return json.dumps({"error": f"Import failed: {str(e)}"})


# =============================================================================
# 6. get_resume_data
# =============================================================================


@mcp.tool()
def get_resume_data() -> str:
	"""Read the master resume data pool.

	Returns the complete resume data including all entries across all sections.

	Returns:
		JSON with complete resume data or error if not found.
	"""
	store = _get_store()
	data = store.load_data()

	if data is None:
		return json.dumps({
			"error": "No resume data found",
			"hint": "Use import_resume to import from PDF, DOCX, or .tex file",
		})

	return data.model_dump_json(indent=2)


# =============================================================================
# 7. update_resume_data
# =============================================================================


@mcp.tool()
def update_resume_data(
	section: str,
	action: str,
	index: int | None = None,
	data: str | dict | None = None,
) -> str:
	"""Add, edit, or remove entries in the master resume data.

	Args:
		section: Section to modify (contact, experience, projects, education, publications, skills).
		action: Action to perform (add, update, delete). Contact only supports update.
		index: Index of entry to update/delete (required for update/delete, not used for contact).
		data: JSON string or dict of entry data (required for add/update).

	Returns:
		JSON with update status.
	"""
	store = _get_store()
	resume_data = store.load_data()

	if resume_data is None:
		return json.dumps({"error": "No resume data found. Import a resume first."})

	valid_sections = ["contact", "experience", "projects", "education", "publications", "skills"]
	if section not in valid_sections:
		return json.dumps({"error": f"Invalid section. Must be one of: {valid_sections}"})

	if action not in ("add", "update", "delete"):
		return json.dumps({"error": "Invalid action. Must be one of: add, update, delete"})

	try:
		if data is not None and not isinstance(data, str):
			data = json.dumps(data)

		if section == "contact":
			if action != "update":
				return json.dumps({"error": "Contact section only supports 'update' action"})
			if data is None:
				return json.dumps({"error": "Data is required for update"})
			entry_data = json.loads(data)
			current = resume_data.contact.model_dump()
			current.update(entry_data)
			resume_data.contact = ContactInfo.model_validate(current)
			store.save_data(resume_data)
			return json.dumps({"success": True, "action": "update", "section": "contact"})

		section_list = getattr(resume_data, section)

		if action == "delete":
			if index is None or index < 0 or index >= len(section_list):
				return json.dumps({"error": f"Invalid index {index} for {section}"})
			del section_list[index]

		elif action in ("add", "update"):
			if data is None:
				return json.dumps({"error": "Data is required for add/update"})

			entry_data = json.loads(data)

			model_map = {
				"experience": Experience,
				"projects": Project,
				"education": Education,
				"publications": Publication,
				"skills": SkillCategory,
			}
			entry = model_map[section].model_validate(entry_data)

			if action == "add":
				section_list.append(entry)
			else:
				if index is None or index < 0 or index >= len(section_list):
					return json.dumps({"error": f"Invalid index {index} for {section}"})
				section_list[index] = entry

		store.save_data(resume_data)
		return json.dumps({
			"success": True,
			"action": action,
			"section": section,
			"new_count": len(section_list),
		})

	except json.JSONDecodeError as e:
		return json.dumps({"error": f"Invalid JSON data: {str(e)}"})
	except Exception as e:
		return json.dumps({"error": f"Update failed: {str(e)}"})


# =============================================================================
# 8. generate_resume
# =============================================================================


@mcp.tool()
def generate_resume(
	output_filename: str = "resume",
	template_name: str = "modern",
) -> str:
	"""Render resume data to LaTeX source using a template.

	Args:
		output_filename: Base filename for output (without extension).
		template_name: Template style ('modern', 'classic', 'minimal').

	Returns:
		JSON with LaTeX file path and status.
	"""
	store = _get_store()
	output_dir = _ensure_dir(_get_output_dir())

	data = store.load_data()
	if data is None:
		return json.dumps({"error": "No resume data found"})

	try:
		tex_source = render_resume(data, template_name=template_name)
		tex_path = output_dir / f"{output_filename}.tex"
		tex_path.write_text(tex_source, encoding="utf-8")

		return json.dumps({
			"success": True,
			"tex_path": str(tex_path),
			"template": template_name,
			"size_bytes": len(tex_source),
		})
	except Exception as e:
		return json.dumps({"error": f"Generation failed: {str(e)}"})


# =============================================================================
# 9. compile_and_preview
# =============================================================================


@mcp.tool()
def compile_and_preview(
	tex_path: str | None = None,
	output_filename: str = "resume",
	template_name: str = "modern",
	dpi: int = 200,
) -> Any:
	"""Compile a LaTeX resume to PDF and return a preview image.

	If tex_path is provided, compiles that file directly.
	Otherwise generates from resume data using the specified template, then compiles.

	Args:
		tex_path: Path to existing .tex file. If None, generates from data first.
		output_filename: Base filename for output files (used when generating).
		template_name: Template style when generating ('modern', 'classic', 'minimal').
		dpi: Resolution for preview image (default 200).

	Returns:
		Image of the rendered resume, or error JSON string.
	"""
	output_dir = _ensure_dir(_get_output_dir())

	try:
		if tex_path:
			path = Path(tex_path).expanduser()
			if not path.exists():
				return json.dumps({"error": f"File not found: {tex_path}"})
			tex_source = path.read_text(encoding="utf-8")
			stem = path.stem
		else:
			store = _get_store()
			data = store.load_data()
			if data is None:
				return json.dumps({"error": "No resume data found"})
			tex_source = render_resume(data, template_name=template_name)
			stem = output_filename

		result = compile_latex(tex_source, output_dir, stem)

		if not result.success or result.pdf_path is None:
			return json.dumps({
				"error": "Compilation failed",
				"errors": result.errors,
			})

		png_bytes = render_pdf_to_png(result.pdf_path, dpi=dpi)
		return [Image(data=png_bytes, format="png")]

	except Exception as e:
		return json.dumps({"error": f"Compile and preview failed: {str(e)}"})


# =============================================================================
# 10. score_resume_quality
# =============================================================================


@mcp.tool()
def score_resume_quality(keywords: list[str] | None = None) -> str:
	"""Analyze resume quality with detailed scoring.

	Evaluates bullet quality, ATS compatibility, keyword matching,
	and page layout. Returns actionable improvement suggestions.

	Args:
		keywords: Optional list of keywords to match (from job description).

	Returns:
		JSON with detailed quality scores and suggestions.
	"""
	store = _get_store()
	data = store.load_data()

	if data is None:
		return json.dumps({"error": "No resume data found"})

	try:
		score = score_resume(data, keywords)
		return score.model_dump_json(indent=2)
	except Exception as e:
		return json.dumps({"error": f"Scoring failed: {str(e)}"})


# =============================================================================
# 11. generate_tailored_resume
# =============================================================================


@mcp.tool()
def generate_tailored_resume(
	jd_text: str,
	template_name: str = "modern",
	output_filename: str = "tailored",
	target_tags: list[str] | None = None,
	include_experiences: list[int] | None = None,
	exclude_experiences: list[int] | None = None,
	include_projects: list[int] | None = None,
	exclude_projects: list[int] | None = None,
	max_experiences: int = 4,
	max_projects: int = 3,
	compile_pdf: bool = True,
	dpi: int = 200,
) -> Any:
	"""Tailor resume to a job description: parse JD, select content, generate.

	Parses the job description, selects and ranks experiences/projects by
	relevance, generates a tailored resume, and optionally compiles to PDF.

	Args:
		jd_text: Raw job description text.
		template_name: Template style ('modern', 'classic', 'minimal').
		output_filename: Base filename for output.
		target_tags: Optional tags to prioritize (e.g., ["swe", "ml"]).
		include_experiences: Force include these experience indices.
		exclude_experiences: Exclude these experience indices.
		include_projects: Force include these project indices.
		exclude_projects: Exclude these project indices.
		max_experiences: Maximum experience entries (default 4).
		max_projects: Maximum project entries (default 3).
		compile_pdf: Whether to compile and preview (default True).
		dpi: Resolution for preview image.

	Returns:
		Preview image if compile_pdf=True, otherwise JSON with details.
	"""
	store = _get_store()
	output_dir = _ensure_dir(_get_output_dir())

	data = store.load_data()
	if data is None:
		return json.dumps({"error": "No resume data found"})

	try:
		variant, jd = generate_tailored_variant(
			data,
			jd_text,
			output_filename,
			target_tags,
			max_experience=max_experiences,
			max_projects=max_projects,
			include_experiences=include_experiences,
			exclude_experiences=exclude_experiences,
			include_projects=include_projects,
			exclude_projects=exclude_projects,
		)

		if not compile_pdf:
			return json.dumps({
				"success": True,
				"variant_name": output_filename,
				"jd_title": jd.title,
				"keywords_matched": len(jd.keywords),
				"experience_selected": len(variant.experience_indices),
				"projects_selected": len(variant.project_indices),
			})

		tex_source = render_resume(data, variant, template_name=template_name)
		result = compile_latex(tex_source, output_dir, output_filename)

		if not result.success or result.pdf_path is None:
			return json.dumps({
				"error": "Compilation failed",
				"errors": result.errors,
			})

		png_bytes = render_pdf_to_png(result.pdf_path, dpi=dpi)
		return [Image(data=png_bytes, format="png")]

	except Exception as e:
		return json.dumps({"error": f"Tailored resume generation failed: {str(e)}"})


def main() -> None:
	"""Run the MCP server."""
	mcp.run()


if __name__ == "__main__":
	main()
