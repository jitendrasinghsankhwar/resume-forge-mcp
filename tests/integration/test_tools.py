"""Integration tests for MCP server tools."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from resume_forge_mcp.models.resume import ResumeData, ResumeVariant
from resume_forge_mcp.storage.resume_store import ResumeStore


@pytest.fixture
def integration_setup(
	sample_resume_data: ResumeData, sample_variant: ResumeVariant
) -> Generator[tuple[ResumeStore, Path], None, None]:
	"""Set up integration test environment."""
	with tempfile.TemporaryDirectory() as tmpdir:
		data_dir = Path(tmpdir) / "data"
		output_dir = Path(tmpdir) / "output"
		data_dir.mkdir()
		output_dir.mkdir()

		store = ResumeStore(data_dir)
		store.save_data(sample_resume_data)
		store.save_variant(sample_variant)

		# Patch the helper functions to use our test directories
		with (
			patch("resume_forge_mcp.server._get_store", return_value=store),
			patch("resume_forge_mcp.server._ensure_output_dir", return_value=output_dir),
			patch("resume_forge_mcp.server._get_data_dir", return_value=data_dir),
			patch("resume_forge_mcp.server._get_output_dir", return_value=output_dir),
		):
			yield store, output_dir


class TestDataManagementTools:
	"""Integration tests for data management tools."""

	def test_get_resume_data_returns_json(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""get_resume_data returns valid JSON."""
		from resume_forge_mcp.server import get_resume_data

		result = get_resume_data()
		data = json.loads(result)

		assert "contact" in data
		assert data["contact"]["name"] == "Danny Willow Liu"

	def test_get_resume_data_missing(self) -> None:
		"""get_resume_data returns error when no data."""
		from resume_forge_mcp.server import get_resume_data

		with tempfile.TemporaryDirectory() as tmpdir:
			store = ResumeStore(Path(tmpdir))
			with patch("resume_forge_mcp.server._get_store", return_value=store):
				result = get_resume_data()
				data = json.loads(result)

				assert "error" in data

	def test_list_variants_returns_list(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""list_variants returns variant list."""
		from resume_forge_mcp.server import list_variants

		result = list_variants()
		data = json.loads(result)

		assert "variants" in data
		assert len(data["variants"]) == 1
		assert data["variants"][0]["name"] == "swe"

	def test_get_variant_returns_details(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""get_variant returns variant configuration."""
		from resume_forge_mcp.server import get_variant

		result = get_variant("swe")
		data = json.loads(result)

		assert data["name"] == "swe"
		assert "experience_indices" in data

	def test_get_variant_not_found(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""get_variant returns error for unknown variant."""
		from resume_forge_mcp.server import get_variant

		result = get_variant("nonexistent")
		data = json.loads(result)

		assert "error" in data

	def test_save_variant_creates_new(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""save_variant creates a new variant."""
		from resume_forge_mcp.server import save_variant

		store, _ = integration_setup

		variant_json = json.dumps({
			"name": "ml",
			"description": "ML variant",
			"experience_indices": [1],
			"project_indices": [0],
		})

		result = save_variant(variant_json)
		data = json.loads(result)

		assert data["success"] is True
		assert store.load_variant("ml") is not None

	def test_update_resume_data_add(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""update_resume_data can add entries."""
		from resume_forge_mcp.server import update_resume_data

		entry = json.dumps({
			"company": "New Company",
			"title": "New Role",
			"date": "2026",
			"bullets": ["Did stuff"],
		})

		result = update_resume_data(
			section="experience", action="add", data=entry
		)
		data = json.loads(result)

		assert data["success"] is True
		assert data["new_count"] == 3  # Originally 2 + 1


class TestGenerationTools:
	"""Integration tests for generation and compilation tools."""

	def test_generate_resume_creates_tex(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""generate_resume creates .tex file."""
		from resume_forge_mcp.server import generate_resume

		_, output_dir = integration_setup

		result = generate_resume(output_filename="test_resume")
		data = json.loads(result)

		assert data["success"] is True
		assert (output_dir / "test_resume.tex").exists()

	def test_generate_resume_with_variant(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""generate_resume uses variant when specified."""
		from resume_forge_mcp.server import generate_resume

		result = generate_resume(variant_name="swe", output_filename="swe_resume")
		data = json.loads(result)

		assert data["success"] is True
		assert data["variant"] == "swe"

	def test_generate_resume_invalid_variant(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""generate_resume errors on invalid variant."""
		from resume_forge_mcp.server import generate_resume

		result = generate_resume(variant_name="nonexistent")
		data = json.loads(result)

		assert "error" in data


class TestIntelligenceTools:
	"""Integration tests for intelligence tools."""

	def test_score_resume_quality(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""score_resume_quality returns detailed scores."""
		from resume_forge_mcp.server import score_resume_quality

		result = score_resume_quality()
		data = json.loads(result)

		assert "overall_score" in data
		assert "section_scores" in data
		assert "ats_report" in data

	def test_score_resume_quality_with_keywords(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""score_resume_quality includes keyword match."""
		from resume_forge_mcp.server import score_resume_quality

		result = score_resume_quality(keywords=["Python", "Flask"])
		data = json.loads(result)

		assert "keyword_match" in data
		assert data["keyword_match"] is not None

	def test_parse_job_description_text(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""parse_job_description_text extracts JD info."""
		from resume_forge_mcp.server import parse_job_description_text

		jd_text = """
		Software Engineer
		Requirements: Python, AWS, PostgreSQL
		Nice to have: Kubernetes, Docker
		"""

		result = parse_job_description_text(jd_text)
		data = json.loads(result)

		assert "keywords" in data
		assert len(data["keywords"]) > 0


class TestPreviewContentSelection:
	"""Integration tests for preview_content_selection tool."""

	def test_preview_returns_selection_details(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""preview_content_selection returns detailed selection info."""
		from resume_forge_mcp.server import preview_content_selection

		jd_text = """
		Software Engineer
		Requirements: Python, PostgreSQL, AWS
		Nice to have: Docker, Kubernetes
		"""

		result = preview_content_selection(jd_text)
		data = json.loads(result)

		assert "selected_experiences" in data
		assert "selected_projects" in data
		assert "total_estimated_lines" in data
		assert "page_budget" in data
		assert "budget_remaining" in data

	def test_preview_shows_scores(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""preview_content_selection shows scores for each entry."""
		from resume_forge_mcp.server import preview_content_selection

		jd_text = "Software Engineer at TechCorp. Requirements: Python, SQL"

		result = preview_content_selection(jd_text)
		data = json.loads(result)

		# Each experience should have score info
		if data["selected_experiences"]:
			exp = data["selected_experiences"][0]
			assert "index" in exp
			assert "score" in exp
			assert "estimated_lines" in exp
			assert "company" in exp

	def test_preview_with_include_exclude(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""preview_content_selection respects include/exclude params."""
		from resume_forge_mcp.server import preview_content_selection

		jd_text = "Software Engineer"

		result = preview_content_selection(
			jd_text,
			include_experiences=[1],
			exclude_experiences=[0],
		)
		data = json.loads(result)

		# Check that index 1 is included and marked as forced
		indices = [e["index"] for e in data["selected_experiences"]]
		assert 1 in indices
		assert 0 not in indices

		# Check forced flag
		forced_entry = next(
			e for e in data["selected_experiences"] if e["index"] == 1
		)
		assert forced_entry["forced"] is True

	def test_preview_shows_jd_info(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""preview_content_selection shows parsed JD info."""
		from resume_forge_mcp.server import preview_content_selection

		jd_text = """
		Software Engineer
		Requirements: Python, AWS
		"""

		result = preview_content_selection(jd_text)
		data = json.loads(result)

		assert "required_skills" in data
		assert "preferred_skills" in data
		assert "keywords_found" in data


class TestUtilityTools:
	"""Integration tests for utility tools."""

	def test_get_config(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""get_config returns configuration."""
		from resume_forge_mcp.server import get_config

		result = get_config()
		data = json.loads(result)

		assert "has_resume_data" in data
		assert data["has_resume_data"] is True
		assert "tools_available" in data
		assert len(data["tools_available"]) == 19  # 16 + 3 work history tools
