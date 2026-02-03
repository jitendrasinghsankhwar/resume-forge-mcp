"""Integration tests for MCP server tools."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from latex_resume_mcp.models.resume import ResumeData, ResumeVariant
from latex_resume_mcp.storage.resume_store import ResumeStore


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
			patch("latex_resume_mcp.server._get_store", return_value=store),
			patch("latex_resume_mcp.server._ensure_output_dir", return_value=output_dir),
			patch("latex_resume_mcp.server._get_data_dir", return_value=data_dir),
			patch("latex_resume_mcp.server._get_output_dir", return_value=output_dir),
		):
			yield store, output_dir


class TestDataManagementTools:
	"""Integration tests for data management tools."""

	def test_get_resume_data_returns_json(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""get_resume_data returns valid JSON."""
		from latex_resume_mcp.server import get_resume_data

		result = get_resume_data()
		data = json.loads(result)

		assert "contact" in data
		assert data["contact"]["name"] == "Danny Willow Liu"

	def test_get_resume_data_missing(self) -> None:
		"""get_resume_data returns error when no data."""
		from latex_resume_mcp.server import get_resume_data

		with tempfile.TemporaryDirectory() as tmpdir:
			store = ResumeStore(Path(tmpdir))
			with patch("latex_resume_mcp.server._get_store", return_value=store):
				result = get_resume_data()
				data = json.loads(result)

				assert "error" in data

	def test_list_variants_returns_list(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""list_variants returns variant list."""
		from latex_resume_mcp.server import list_variants

		result = list_variants()
		data = json.loads(result)

		assert "variants" in data
		assert len(data["variants"]) == 1
		assert data["variants"][0]["name"] == "swe"

	def test_get_variant_returns_details(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""get_variant returns variant configuration."""
		from latex_resume_mcp.server import get_variant

		result = get_variant("swe")
		data = json.loads(result)

		assert data["name"] == "swe"
		assert "experience_indices" in data

	def test_get_variant_not_found(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""get_variant returns error for unknown variant."""
		from latex_resume_mcp.server import get_variant

		result = get_variant("nonexistent")
		data = json.loads(result)

		assert "error" in data

	def test_save_variant_creates_new(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""save_variant creates a new variant."""
		from latex_resume_mcp.server import save_variant

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
		from latex_resume_mcp.server import update_resume_data

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
		from latex_resume_mcp.server import generate_resume

		_, output_dir = integration_setup

		result = generate_resume(output_filename="test_resume")
		data = json.loads(result)

		assert data["success"] is True
		assert (output_dir / "test_resume.tex").exists()

	def test_generate_resume_with_variant(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""generate_resume uses variant when specified."""
		from latex_resume_mcp.server import generate_resume

		result = generate_resume(variant_name="swe", output_filename="swe_resume")
		data = json.loads(result)

		assert data["success"] is True
		assert data["variant"] == "swe"

	def test_generate_resume_invalid_variant(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""generate_resume errors on invalid variant."""
		from latex_resume_mcp.server import generate_resume

		result = generate_resume(variant_name="nonexistent")
		data = json.loads(result)

		assert "error" in data


class TestIntelligenceTools:
	"""Integration tests for intelligence tools."""

	def test_score_resume_quality(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""score_resume_quality returns detailed scores."""
		from latex_resume_mcp.server import score_resume_quality

		result = score_resume_quality()
		data = json.loads(result)

		assert "overall_score" in data
		assert "section_scores" in data
		assert "ats_report" in data

	def test_score_resume_quality_with_keywords(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""score_resume_quality includes keyword match."""
		from latex_resume_mcp.server import score_resume_quality

		result = score_resume_quality(keywords=["Python", "Flask"])
		data = json.loads(result)

		assert "keyword_match" in data
		assert data["keyword_match"] is not None

	def test_parse_job_description_text(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""parse_job_description_text extracts JD info."""
		from latex_resume_mcp.server import parse_job_description_text

		jd_text = """
		Software Engineer
		Requirements: Python, AWS, PostgreSQL
		Nice to have: Kubernetes, Docker
		"""

		result = parse_job_description_text(jd_text)
		data = json.loads(result)

		assert "keywords" in data
		assert len(data["keywords"]) > 0


class TestUtilityTools:
	"""Integration tests for utility tools."""

	def test_get_config(
		self, integration_setup: tuple[ResumeStore, Path]
	) -> None:
		"""get_config returns configuration."""
		from latex_resume_mcp.server import get_config

		result = get_config()
		data = json.loads(result)

		assert "has_resume_data" in data
		assert data["has_resume_data"] is True
		assert "tools_available" in data
		assert len(data["tools_available"]) == 15
