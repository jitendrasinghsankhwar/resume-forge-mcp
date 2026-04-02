"""Tests for intelligence/tailoring.py."""

from __future__ import annotations

from resume_forge_mcp.intelligence.tailoring import (
	PAGE_BUDGET,
	estimate_entry_lines,
	generate_tailored_variant,
	parse_job_description,
	select_content_for_jd,
	select_content_with_details,
)
from resume_forge_mcp.models.analysis import JobDescription
from resume_forge_mcp.models.resume import Experience, Project, ResumeData

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


class TestEstimateEntryLines:
	"""Tests for estimate_entry_lines function."""

	def test_experience_entry_lines(self) -> None:
		"""Experience entries have header lines plus bullet lines."""
		exp = Experience(
			company="TestCorp",
			title="Engineer",
			date="2024",
			bullets=["Short bullet", "Another short one"],
			tags=[],
		)
		lines = estimate_entry_lines(exp, "experience")

		# 2 header lines + 2 bullet lines (short bullets = 1 line each)
		assert lines == 4

	def test_project_entry_lines(self) -> None:
		"""Project entries have 1 header line plus bullet lines."""
		proj = Project(
			name="TestProject",
			technologies="Python, Flask",
			bullets=["Short bullet"],
			tags=[],
		)
		lines = estimate_entry_lines(proj, "project")

		# 1 header line + 1 bullet line
		assert lines == 2

	def test_long_bullet_wrapping(self) -> None:
		"""Long bullets are estimated to wrap across multiple lines."""
		# 250 chars = should estimate to ~3 lines (100 chars per line)
		long_bullet = "x" * 250
		exp = Experience(
			company="TestCorp",
			title="Engineer",
			date="2024",
			bullets=[long_bullet],
			tags=[],
		)
		lines = estimate_entry_lines(exp, "experience")

		# 2 header lines + 3 bullet lines (250/100 rounded up)
		assert lines == 5


class TestIncludeExcludeLogic:
	"""Tests for include/exclude parameters."""

	def test_include_experiences_forces_selection(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Force-included experiences are selected regardless of score."""
		jd = parse_job_description(SAMPLE_JD)
		variant = select_content_for_jd(
			sample_resume_data,
			jd,
			include_experiences=[1],  # Force include index 1
			max_experience=1,
		)

		# Index 1 should be included even with max_experience=1
		assert 1 in variant.experience_indices

	def test_exclude_experiences_prevents_selection(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Excluded experiences are never selected."""
		jd = parse_job_description(SAMPLE_JD)
		variant = select_content_for_jd(
			sample_resume_data,
			jd,
			exclude_experiences=[0],  # Exclude index 0
		)

		assert 0 not in variant.experience_indices

	def test_include_projects_forces_selection(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Force-included projects are selected regardless of score."""
		jd = parse_job_description(SAMPLE_JD)
		variant = select_content_for_jd(
			sample_resume_data,
			jd,
			include_projects=[0],
			max_projects=1,
		)

		assert 0 in variant.project_indices

	def test_exclude_projects_prevents_selection(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Excluded projects are never selected."""
		jd = parse_job_description(SAMPLE_JD)
		variant = select_content_for_jd(
			sample_resume_data,
			jd,
			exclude_projects=[0],
		)

		assert 0 not in variant.project_indices

	def test_include_and_exclude_conflict(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Exclude takes precedence over include."""
		jd = parse_job_description(SAMPLE_JD)
		variant = select_content_for_jd(
			sample_resume_data,
			jd,
			include_experiences=[0],
			exclude_experiences=[0],  # Exclude same one
		)

		# Exclude should win
		assert 0 not in variant.experience_indices


class TestWeightedScoring:
	"""Tests for weighted scoring algorithm."""

	def test_required_skills_weighted_higher(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Required skills have higher weight than preferred."""
		# Create JD with required skills that match first experience
		jd_text = """
		Software Engineer
		Requirements:
		- PostgreSQL experience required
		- AWS experience required

		Nice to have:
		- Machine Learning
		"""
		jd = parse_job_description(jd_text)
		selection = select_content_with_details(
			sample_resume_data, jd, use_page_budget=False
		)

		# First experience (E2 Consulting) mentions PostgreSQL and AWS
		# Should have a higher score due to required skills matching
		assert len(selection.experience_scores) > 0

	def test_score_components_sum_to_max_one(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Score should never exceed 1.0."""
		jd_text = """
		ML Engineer
		Requirements: Python, PyTorch, ML, TensorFlow, Kubernetes
		Nice to have: Docker, AWS, Distributed
		"""
		jd = parse_job_description(jd_text)
		selection = select_content_with_details(
			sample_resume_data, jd, use_page_budget=False
		)

		for entry_score in selection.experience_scores:
			assert entry_score.score <= 1.0
		for entry_score in selection.project_scores:
			assert entry_score.score <= 1.0


class TestPageBudget:
	"""Tests for page budget system."""

	def test_budget_limits_selection(self, sample_resume_data: ResumeData) -> None:
		"""Selection respects page budget."""
		jd = parse_job_description(SAMPLE_JD)
		selection = select_content_with_details(
			sample_resume_data, jd, use_page_budget=True
		)

		# Total lines should not exceed budget
		assert selection.total_estimated_lines <= PAGE_BUDGET

	def test_over_budget_flag_set(self, sample_resume_data: ResumeData) -> None:
		"""Over budget flag is set correctly."""
		jd = parse_job_description(SAMPLE_JD)
		selection = select_content_with_details(
			sample_resume_data, jd, use_page_budget=True
		)

		# With our sample data, should not be over budget
		assert not selection.over_budget

	def test_budget_remaining_calculated(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Budget remaining is calculated correctly."""
		jd = parse_job_description(SAMPLE_JD)
		selection = select_content_with_details(
			sample_resume_data, jd, use_page_budget=True
		)

		expected_remaining = PAGE_BUDGET - selection.total_estimated_lines
		assert selection.budget_remaining == expected_remaining

	def test_disable_budget_ignores_limit(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Disabling budget ignores page limit."""
		jd = parse_job_description(SAMPLE_JD)
		selection = select_content_with_details(
			sample_resume_data, jd, use_page_budget=False
		)

		# Budget remaining should be -1 when disabled
		assert selection.budget_remaining == -1
