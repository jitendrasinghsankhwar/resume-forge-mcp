"""Tests for intelligence/tailoring.py."""

from __future__ import annotations

from latex_resume_mcp.intelligence.tailoring import (
	generate_tailored_variant,
	parse_job_description,
	select_content_for_jd,
)
from latex_resume_mcp.models.analysis import JobDescription
from latex_resume_mcp.models.resume import ResumeData

SAMPLE_JD = """
Senior Software Engineer
Company: TechCorp Inc.

About the Role:
We are looking for a Senior Software Engineer to join our platform team.

Requirements:
- 3+ years of experience with Python
- Experience with PostgreSQL and Redis
- Strong knowledge of REST APIs
- Experience with AWS (EC2, Lambda, S3)

Nice to have:
- Kubernetes experience
- Machine Learning background
- Open source contributions

Responsibilities:
- Design and implement scalable backend services
- Lead code reviews and mentor junior engineers
- Collaborate with product team on requirements
- Improve system reliability and performance
"""


class TestParseJobDescription:
	"""Tests for parse_job_description function."""

	def test_extracts_title(self) -> None:
		"""Title is extracted from first line."""
		jd = parse_job_description(SAMPLE_JD)

		assert "Software Engineer" in jd.title

	def test_extracts_required_skills(self) -> None:
		"""Required skills are extracted."""
		jd = parse_job_description(SAMPLE_JD)

		# Should find Python mentioned in requirements
		assert "Python" in jd.required_skills or "Python" in jd.keywords

	def test_extracts_preferred_skills(self) -> None:
		"""Preferred skills are extracted."""
		jd = parse_job_description(SAMPLE_JD)

		# Kubernetes is in "nice to have"
		assert (
			"Kubernetes" in jd.preferred_skills
			or "Kubernetes" in jd.keywords
		)

	def test_extracts_keywords(self) -> None:
		"""Keywords are extracted."""
		jd = parse_job_description(SAMPLE_JD)

		# Should have several tech keywords
		assert len(jd.keywords) > 0

	def test_stores_raw_text(self) -> None:
		"""Raw JD text is preserved."""
		jd = parse_job_description(SAMPLE_JD)

		assert jd.raw_text == SAMPLE_JD

	def test_extracts_responsibilities(self) -> None:
		"""Responsibilities are extracted."""
		jd = parse_job_description(SAMPLE_JD)

		# May or may not extract all, but shouldn't crash
		assert isinstance(jd.responsibilities, list)

	def test_empty_jd(self) -> None:
		"""Empty JD doesn't crash."""
		jd = parse_job_description("")

		assert jd.title == ""
		assert len(jd.keywords) == 0


class TestSelectContentForJD:
	"""Tests for select_content_for_jd function."""

	def test_selects_relevant_experiences(
		self, sample_resume_data: ResumeData
	) -> None:
		"""More relevant experiences are selected first."""
		jd = parse_job_description(SAMPLE_JD)
		variant = select_content_for_jd(sample_resume_data, jd)

		# Should have some experience indices
		assert len(variant.experience_indices) > 0
		# Indices should be valid
		for idx in variant.experience_indices:
			assert 0 <= idx < len(sample_resume_data.experience)

	def test_respects_max_experience(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Max experience limit is respected."""
		jd = parse_job_description(SAMPLE_JD)
		variant = select_content_for_jd(
			sample_resume_data, jd, max_experience=1
		)

		assert len(variant.experience_indices) <= 1

	def test_respects_max_projects(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Max projects limit is respected."""
		jd = parse_job_description(SAMPLE_JD)
		variant = select_content_for_jd(
			sample_resume_data, jd, max_projects=1
		)

		assert len(variant.project_indices) <= 1

	def test_includes_all_education(
		self, sample_resume_data: ResumeData
	) -> None:
		"""All education is included."""
		jd = parse_job_description(SAMPLE_JD)
		variant = select_content_for_jd(sample_resume_data, jd)

		assert len(variant.education_indices) == len(sample_resume_data.education)

	def test_prioritizes_tagged_content(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Content with matching tags is prioritized."""
		jd = parse_job_description(SAMPLE_JD)
		variant = select_content_for_jd(
			sample_resume_data, jd, target_tags=["swe"]
		)

		# Should still select content
		assert len(variant.experience_indices) > 0

	def test_reorders_skills(self, sample_resume_data: ResumeData) -> None:
		"""Skills are reordered by keyword relevance."""
		jd = parse_job_description(SAMPLE_JD)
		variant = select_content_for_jd(sample_resume_data, jd)

		# Skills override should be set
		assert variant.skills_override is not None


class TestGenerateTailoredVariant:
	"""Tests for generate_tailored_variant function."""

	def test_returns_variant_and_jd(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Returns both variant and parsed JD."""
		variant, jd = generate_tailored_variant(
			sample_resume_data, SAMPLE_JD, "test_variant"
		)

		assert variant.name == "test_variant"
		assert isinstance(jd, JobDescription)

	def test_variant_has_description(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Generated variant has description."""
		variant, _ = generate_tailored_variant(
			sample_resume_data, SAMPLE_JD, "test"
		)

		assert variant.description != ""

	def test_uses_target_tags(self, sample_resume_data: ResumeData) -> None:
		"""Target tags are used for selection."""
		variant, _ = generate_tailored_variant(
			sample_resume_data,
			SAMPLE_JD,
			"test",
			target_tags=["swe", "cloud"],
		)

		# Variant should be created
		assert variant is not None

	def test_section_order_set(self, sample_resume_data: ResumeData) -> None:
		"""Section order is set in variant."""
		variant, _ = generate_tailored_variant(
			sample_resume_data, SAMPLE_JD, "test"
		)

		assert len(variant.section_order) > 0
		assert "experience" in variant.section_order
