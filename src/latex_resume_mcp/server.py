"""LaTeX Resume MCP Server - Intelligent resume generation with visual verification."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP, Image

from latex_resume_mcp.compiler.latex import compile_latex
from latex_resume_mcp.compiler.preview import get_pdf_info, render_pdf_to_png
from latex_resume_mcp.intelligence.analyzer import score_resume
from latex_resume_mcp.intelligence.tailoring import (
	generate_tailored_variant,
	parse_job_description,
)
from latex_resume_mcp.models.resume import (
	Education,
	Experience,
	Project,
	Publication,
	ResumeVariant,
	SkillCategory,
)
from latex_resume_mcp.storage.resume_store import ResumeStore
from latex_resume_mcp.storage.tex_import import import_from_latex
from latex_resume_mcp.templates.engine import render_resume

logger = logging.getLogger(__name__)


def _get_data_dir() -> Path:
	"""Get data directory from environment or default."""
	default = Path.home() / ".latex-resume-mcp"
	return Path(os.environ.get("LATEX_RESUME_DATA_DIR", default))


def _get_output_dir() -> Path:
	"""Get output directory for generated files."""
	default = _get_data_dir() / "output"
	return Path(os.environ.get("LATEX_RESUME_OUTPUT_DIR", default))


def _get_store() -> ResumeStore:
	"""Get or create the resume store."""
	data_dir = _get_data_dir()
	data_dir.mkdir(parents=True, exist_ok=True)
	return ResumeStore(data_dir)


def _ensure_output_dir() -> Path:
	"""Ensure output directory exists and return it."""
	output_dir = _get_output_dir()
	output_dir.mkdir(parents=True, exist_ok=True)
	return output_dir


def _serialize_result(obj: Any) -> str:
	"""Serialize result to JSON string."""
	if hasattr(obj, "model_dump"):
		return json.dumps(obj.model_dump(), indent=2)
	elif hasattr(obj, "__dict__"):
		return json.dumps(asdict(obj), indent=2, default=str)
	return json.dumps(obj, indent=2, default=str)


mcp = FastMCP("latex-resume")


# =============================================================================
# Data Management Tools
# =============================================================================


@mcp.tool()
def import_from_latex_file(tex_path: str) -> str:
	"""Import an existing LaTeX resume file into the JSON data model.

	Parses a .tex file using Jake's Resume template format and extracts all
	entries (contact, education, experience, projects, skills) into structured
	data. The imported data becomes the master resume pool.

	Args:
		tex_path: Absolute path to the .tex file to import.

	Returns:
		JSON with import status and summary of extracted entries.
	"""
	store = _get_store()
	path = Path(tex_path).expanduser()

	try:
		data = import_from_latex(path)
		store.save_data(data)

		summary = {
			"success": True,
			"imported_from": str(path),
			"entries": {
				"education": len(data.education),
				"experience": len(data.experience),
				"projects": len(data.projects),
				"publications": len(data.publications),
				"skill_categories": len(data.skills),
			},
			"contact": data.contact.name,
		}
		return json.dumps(summary, indent=2)
	except FileNotFoundError:
		return json.dumps({"error": f"File not found: {tex_path}"})
	except Exception as e:
		return json.dumps({"error": f"Import failed: {str(e)}"})


@mcp.tool()
def get_resume_data() -> str:
	"""Read the master resume data pool.

	Returns the complete resume data including all entries across all sections.
	This is the source of truth for generating resume variants.

	Returns:
		JSON with complete resume data or error if not found.
	"""
	store = _get_store()
	data = store.load_data()

	if data is None:
		return json.dumps({
			"error": "No resume data found",
			"hint": "Use import_from_latex_file to import an existing resume",
		})

	return data.model_dump_json(indent=2)


@mcp.tool()
def update_resume_data(
	section: str,
	action: str,
	index: int | None = None,
	data: str | None = None,
) -> str:
	"""Add, edit, or remove entries in the master resume data.

	Args:
		section: Section to modify (experience, projects, education, publications, skills).
		action: Action to perform (add, update, delete).
		index: Index of entry to update/delete (required for update/delete).
		data: JSON string of entry data (required for add/update).

	Returns:
		JSON with update status.

	Examples:
		Add experience: section="experience", action="add", data='{"company":"Acme",...}'
		Update project: section="projects", action="update", index=0, data='{"name":"New",...}'
		Delete entry: section="education", action="delete", index=1
	"""
	store = _get_store()
	resume_data = store.load_data()

	if resume_data is None:
		return json.dumps({"error": "No resume data found. Import a resume first."})

	valid_sections = ["experience", "projects", "education", "publications", "skills"]
	if section not in valid_sections:
		return json.dumps({"error": f"Invalid section. Must be one of: {valid_sections}"})

	valid_actions = ["add", "update", "delete"]
	if action not in valid_actions:
		return json.dumps({"error": f"Invalid action. Must be one of: {valid_actions}"})

	try:
		section_list = getattr(resume_data, section)

		if action == "delete":
			if index is None or index < 0 or index >= len(section_list):
				return json.dumps({"error": f"Invalid index {index} for {section}"})
			del section_list[index]

		elif action in ("add", "update"):
			if data is None:
				return json.dumps({"error": "Data is required for add/update"})

			entry_data = json.loads(data)

			# Create appropriate model instance based on section
			entry: Experience | Project | Education | Publication | SkillCategory
			if section == "experience":
				entry = Experience.model_validate(entry_data)
			elif section == "projects":
				entry = Project.model_validate(entry_data)
			elif section == "education":
				entry = Education.model_validate(entry_data)
			elif section == "publications":
				entry = Publication.model_validate(entry_data)
			else:  # skills
				entry = SkillCategory.model_validate(entry_data)

			if action == "add":
				section_list.append(entry)  # type: ignore[arg-type]
			else:  # update
				if index is None or index < 0 or index >= len(section_list):
					return json.dumps({"error": f"Invalid index {index} for {section}"})
				section_list[index] = entry  # type: ignore[index]

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


@mcp.tool()
def list_variants() -> str:
	"""List all available resume variants.

	Returns:
		JSON array of variant names with descriptions.
	"""
	store = _get_store()
	names = store.list_variants()

	variants_info = []
	for name in names:
		variant = store.load_variant(name)
		if variant:
			variants_info.append({
				"name": name,
				"description": variant.description,
				"experience_count": len(variant.experience_indices),
				"project_count": len(variant.project_indices),
			})

	return json.dumps({"variants": variants_info, "count": len(variants_info)}, indent=2)


@mcp.tool()
def get_variant(name: str) -> str:
	"""Get a specific resume variant by name.

	Args:
		name: Variant name (e.g., "swe", "applied_ai").

	Returns:
		JSON with variant configuration or error if not found.
	"""
	store = _get_store()
	variant = store.load_variant(name)

	if variant is None:
		return json.dumps({"error": f"Variant '{name}' not found"})

	return variant.model_dump_json(indent=2)


@mcp.tool()
def save_variant(variant_json: str) -> str:
	"""Save a resume variant configuration.

	Args:
		variant_json: JSON string with variant configuration.

	Returns:
		JSON with save status.

	Example variant:
		{
			"name": "swe",
			"description": "Software engineering variant",
			"experience_indices": [0, 1, 2],
			"project_indices": [0, 1],
			"section_order": ["education", "experience", "projects", "skills"]
		}
	"""
	store = _get_store()

	try:
		variant_data = json.loads(variant_json)
		variant = ResumeVariant.model_validate(variant_data)
		store.save_variant(variant)
		return json.dumps({"success": True, "saved": variant.name})
	except json.JSONDecodeError as e:
		return json.dumps({"error": f"Invalid JSON: {str(e)}"})
	except Exception as e:
		return json.dumps({"error": f"Save failed: {str(e)}"})


# =============================================================================
# Generation & Compilation Tools
# =============================================================================


@mcp.tool()
def generate_resume(
	variant_name: str | None = None,
	output_filename: str = "resume",
) -> str:
	"""Render a resume variant to LaTeX source.

	Args:
		variant_name: Name of variant to use (None for all content).
		output_filename: Base filename for output (without extension).

	Returns:
		JSON with LaTeX file path and status.
	"""
	store = _get_store()
	output_dir = _ensure_output_dir()

	data = store.load_data()
	if data is None:
		return json.dumps({"error": "No resume data found"})

	variant = None
	if variant_name:
		variant = store.load_variant(variant_name)
		if variant is None:
			return json.dumps({"error": f"Variant '{variant_name}' not found"})

	try:
		tex_source = render_resume(data, variant)
		tex_path = output_dir / f"{output_filename}.tex"
		tex_path.write_text(tex_source, encoding="utf-8")

		return json.dumps({
			"success": True,
			"tex_path": str(tex_path),
			"variant": variant_name or "default",
			"size_bytes": len(tex_source),
		})
	except Exception as e:
		return json.dumps({"error": f"Generation failed: {str(e)}"})


@mcp.tool()
def compile_resume_tex(tex_path: str | None = None) -> str:
	"""Compile a LaTeX resume to PDF using pdflatex.

	Args:
		tex_path: Path to .tex file. If None, uses latest generated file.

	Returns:
		JSON with PDF path, compilation status, and any errors/warnings.
	"""
	output_dir = _ensure_output_dir()

	if tex_path is None:
		# Find most recent .tex file in output dir
		tex_files = list(output_dir.glob("*.tex"))
		if not tex_files:
			return json.dumps({"error": "No .tex file found. Use generate_resume first."})
		tex_path = str(max(tex_files, key=lambda p: p.stat().st_mtime))

	path = Path(tex_path).expanduser()
	if not path.exists():
		return json.dumps({"error": f"File not found: {tex_path}"})

	tex_source = path.read_text(encoding="utf-8")
	result = compile_latex(tex_source, output_dir, path.stem)

	response: dict[str, Any] = {
		"success": result.success,
		"pdf_path": str(result.pdf_path) if result.pdf_path else None,
	}

	if result.errors:
		response["errors"] = result.errors
	if result.warnings:
		response["warnings"] = result.warnings

	return json.dumps(response, indent=2)


@mcp.tool()
def compile_and_preview(
	variant_name: str | None = None,
	output_filename: str = "resume",
	dpi: int = 200,
) -> Any:
	"""Generate, compile, and render resume preview in one step.

	This is the primary tool for the visual verification workflow.
	Returns the rendered PDF as an image that Claude can see and analyze.

	Args:
		variant_name: Name of variant to use (None for all content).
		output_filename: Base filename for output files.
		dpi: Resolution for preview image (default 200).

	Returns:
		Image of the rendered resume, or error JSON string.
	"""
	store = _get_store()
	output_dir = _ensure_output_dir()

	# Load data
	data = store.load_data()
	if data is None:
		return json.dumps({"error": "No resume data found"})

	# Load variant if specified
	variant = None
	if variant_name:
		variant = store.load_variant(variant_name)
		if variant is None:
			return json.dumps({"error": f"Variant '{variant_name}' not found"})

	try:
		# Generate LaTeX
		tex_source = render_resume(data, variant)

		# Compile to PDF
		result = compile_latex(tex_source, output_dir, output_filename)

		if not result.success or result.pdf_path is None:
			return json.dumps({
				"error": "Compilation failed",
				"errors": result.errors,
			})

		# Render PDF to PNG
		png_bytes = render_pdf_to_png(result.pdf_path, dpi=dpi)

		# Return as Image that Claude can see
		return [Image(data=png_bytes, format="png")]

	except Exception as e:
		return json.dumps({"error": f"Compile and preview failed: {str(e)}"})


@mcp.tool()
def preview_resume(pdf_path: str | None = None, dpi: int = 200) -> Any:
	"""Render an existing PDF resume to PNG for visual inspection.

	Args:
		pdf_path: Path to PDF file. If None, uses latest in output directory.
		dpi: Resolution for preview image (default 200).

	Returns:
		Image of the resume, or error JSON string.
	"""
	output_dir = _ensure_output_dir()

	if pdf_path is None:
		pdf_files = list(output_dir.glob("*.pdf"))
		if not pdf_files:
			return json.dumps({"error": "No PDF found. Use compile_resume_tex first."})
		pdf_path = str(max(pdf_files, key=lambda p: p.stat().st_mtime))

	path = Path(pdf_path).expanduser()
	if not path.exists():
		return json.dumps({"error": f"PDF not found: {pdf_path}"})

	try:
		png_bytes = render_pdf_to_png(path, dpi=dpi)
		return [Image(data=png_bytes, format="png")]
	except Exception as e:
		return json.dumps({"error": f"Preview failed: {str(e)}"})


# =============================================================================
# Intelligence Tools
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


@mcp.tool()
def parse_job_description_text(jd_text: str) -> str:
	"""Parse a job description to extract skills, requirements, and keywords.

	Use this to understand what a job requires before tailoring a resume.

	Args:
		jd_text: Raw job description text (copy/paste from job posting).

	Returns:
		JSON with parsed job title, company, required/preferred skills, keywords.
	"""
	try:
		jd = parse_job_description(jd_text)
		return jd.model_dump_json(indent=2)
	except Exception as e:
		return json.dumps({"error": f"Parsing failed: {str(e)}"})


@mcp.tool()
def generate_tailored_resume(
	jd_text: str,
	variant_name: str = "tailored",
	target_tags: list[str] | None = None,
	compile_pdf: bool = True,
	dpi: int = 200,
) -> Any:
	"""Full automation: parse JD, select content, generate, compile, and preview.

	This is the highest-level tool for resume tailoring. It:
	1. Parses the job description for keywords and requirements
	2. Selects and ranks experiences/projects by relevance
	3. Generates a tailored variant
	4. Compiles to PDF
	5. Returns a preview image for visual verification

	Args:
		jd_text: Raw job description text.
		variant_name: Name to save the generated variant as.
		target_tags: Optional tags to prioritize (e.g., ["swe", "ml"]).
		compile_pdf: Whether to compile and preview (default True).
		dpi: Resolution for preview image.

	Returns:
		Preview image if compile_pdf=True, otherwise JSON with variant details.
	"""
	store = _get_store()
	output_dir = _ensure_output_dir()

	data = store.load_data()
	if data is None:
		return json.dumps({"error": "No resume data found"})

	try:
		# Generate tailored variant
		variant, jd = generate_tailored_variant(data, jd_text, variant_name, target_tags)

		# Save the variant
		store.save_variant(variant)

		if not compile_pdf:
			return json.dumps({
				"success": True,
				"variant_name": variant_name,
				"jd_title": jd.title,
				"keywords_matched": len(jd.keywords),
				"experience_selected": len(variant.experience_indices),
				"projects_selected": len(variant.project_indices),
			})

		# Generate and compile
		tex_source = render_resume(data, variant)
		result = compile_latex(tex_source, output_dir, variant_name)

		if not result.success or result.pdf_path is None:
			return json.dumps({
				"error": "Compilation failed",
				"errors": result.errors,
				"variant_saved": True,
			})

		# Render preview
		png_bytes = render_pdf_to_png(result.pdf_path, dpi=dpi)
		return [Image(data=png_bytes, format="png")]

	except Exception as e:
		return json.dumps({"error": f"Tailored resume generation failed: {str(e)}"})


# =============================================================================
# Utility Tools
# =============================================================================


@mcp.tool()
def assess_quality(pdf_path: str | None = None) -> str:
	"""Programmatic quality checks on a compiled resume.

	Checks page count, file size, encoding issues, and other technical aspects.

	Args:
		pdf_path: Path to PDF file. If None, uses latest in output directory.

	Returns:
		JSON with quality assessment results.
	"""
	output_dir = _ensure_output_dir()

	if pdf_path is None:
		pdf_files = list(output_dir.glob("*.pdf"))
		if not pdf_files:
			return json.dumps({"error": "No PDF found"})
		pdf_path = str(max(pdf_files, key=lambda p: p.stat().st_mtime))

	path = Path(pdf_path).expanduser()
	if not path.exists():
		return json.dumps({"error": f"PDF not found: {pdf_path}"})

	try:
		info = get_pdf_info(path)
		file_size = path.stat().st_size
		issues: list[str] = []
		status = "ok"

		# Check for issues
		page_count = info["page_count"]
		if isinstance(page_count, int) and page_count > 1:
			issues.append(f"Resume is {page_count} pages - consider condensing to 1")
			status = "warning"

		if file_size > 500 * 1024:
			issues.append("File size exceeds 500KB - may be rejected by ATS")
			status = "warning"

		# Check dimensions (letter: 8.5x11, A4: 8.27x11.69)
		width = info.get("width_in", 0)
		height = info.get("height_in", 0)
		if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
			width = 0.0
			height = 0.0
		is_letter = abs(width - 8.5) <= 0.5 and abs(height - 11) <= 0.5
		is_a4 = abs(width - 8.27) <= 0.5 and abs(height - 11.69) <= 0.5
		if not is_letter and not is_a4:
			issues.append("Unusual page dimensions - may not print correctly")

		assessment = {
			"pdf_path": str(path),
			"page_count": info["page_count"],
			"width_in": info["width_in"],
			"height_in": info["height_in"],
			"file_size_kb": round(file_size / 1024, 1),
			"issues": issues,
			"status": status,
		}

		return json.dumps(assessment, indent=2)

	except Exception as e:
		return json.dumps({"error": f"Assessment failed: {str(e)}"})


@mcp.tool()
def get_config() -> str:
	"""Show current configuration and tool availability.

	Returns:
		JSON with configuration details.
	"""
	store = _get_store()
	output_dir = _ensure_output_dir()

	# Check for data
	has_data = store.load_data() is not None
	variants = store.list_variants()

	# Check for pdflatex
	from latex_resume_mcp.compiler.latex import _find_pdflatex

	pdflatex = _find_pdflatex()

	config = {
		"data_directory": str(store.data_path.parent),
		"output_directory": str(output_dir),
		"has_resume_data": has_data,
		"variants_count": len(variants),
		"variants": variants,
		"pdflatex_available": pdflatex is not None,
		"pdflatex_path": pdflatex,
		"tools_available": [
			"import_from_latex_file",
			"get_resume_data",
			"update_resume_data",
			"list_variants",
			"get_variant",
			"save_variant",
			"generate_resume",
			"compile_resume_tex",
			"compile_and_preview",
			"preview_resume",
			"score_resume_quality",
			"parse_job_description_text",
			"generate_tailored_resume",
			"assess_quality",
			"get_config",
		],
	}

	return json.dumps(config, indent=2)


def main() -> None:
	"""Run the MCP server."""
	mcp.run()


if __name__ == "__main__":
	main()
