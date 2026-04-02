"""Tests for the Jinja2 template engine."""

from __future__ import annotations

from resume_forge_mcp.models.resume import (
	ContactInfo,
	Education,
	ResumeData,
	ResumeVariant,
	SkillCategory,
)
from resume_forge_mcp.templates.engine import (
	_resolve_variant,
	create_jinja_env,
	escape_latex,
	render_resume,
)


class TestEscapeLatex:
	def test_ampersand(self) -> None:
		assert escape_latex("R&D") == r"R\&D"

	def test_percent(self) -> None:
		assert escape_latex("50%") == r"50\%"

	def test_dollar(self) -> None:
		assert escape_latex("$100") == r"\$100"

	def test_hash(self) -> None:
		assert escape_latex("#1") == r"\#1"

	def test_underscore(self) -> None:
		assert escape_latex("my_var") == r"my\_var"

	def test_already_escaped(self) -> None:
		assert escape_latex(r"\&") == r"\&"

	def test_empty(self) -> None:
		assert escape_latex("") == ""

	def test_no_special_chars(self) -> None:
		assert escape_latex("Hello World") == "Hello World"

	def test_passthrough_latex_commands(self) -> None:
		text = r"\textbf{Bold text}"
		assert escape_latex(text) == text

	def test_passthrough_href(self) -> None:
		text = r"\href{https://example.com}{\underline{link}}"
		assert escape_latex(text) == text


class TestCreateJinjaEnv:
	def test_custom_delimiters(self) -> None:
		env = create_jinja_env()
		assert env.block_start_string == "<%"
		assert env.variable_start_string == "<<"

	def test_latex_filter_available(self) -> None:
		env = create_jinja_env()
		assert "latex" in env.filters


class TestResolveVariant:
	def test_selects_by_indices(
		self, sample_resume_data: ResumeData, sample_variant: ResumeVariant
	) -> None:
		resolved = _resolve_variant(sample_resume_data, sample_variant)
		assert len(resolved["experience"]) == 2
		assert len(resolved["projects"]) == 1

	def test_falls_back_to_all(self, sample_resume_data: ResumeData) -> None:
		variant = ResumeVariant(name="empty")
		resolved = _resolve_variant(sample_resume_data, variant)
		assert len(resolved["experience"]) == len(sample_resume_data.experience)

	def test_out_of_range_indices(self, sample_resume_data: ResumeData) -> None:
		variant = ResumeVariant(name="bad", experience_indices=[99])
		resolved = _resolve_variant(sample_resume_data, variant)
		# Falls back to all since no valid indices
		assert len(resolved["experience"]) == len(sample_resume_data.experience)

	def test_bullet_overrides(self, sample_resume_data: ResumeData) -> None:
		variant = ResumeVariant(
			name="custom",
			experience_indices=[0],
			bullet_overrides={"experience_0": ["Custom bullet"]},
		)
		resolved = _resolve_variant(sample_resume_data, variant)
		exp_list = resolved["experience"]
		assert isinstance(exp_list, list)
		assert exp_list[0].bullets == ["Custom bullet"]

	def test_skills_override(
		self, sample_resume_data: ResumeData
	) -> None:
		custom_skills = [SkillCategory(category="Custom", skills=["Skill1"])]
		variant = ResumeVariant(name="custom", skills_override=custom_skills)
		resolved = _resolve_variant(sample_resume_data, variant)
		skills_list = resolved["skills"]
		assert isinstance(skills_list, list)
		assert len(skills_list) == 1
		assert skills_list[0].category == "Custom"


class TestRenderResume:
	def test_renders_complete_resume(self, sample_resume_data: ResumeData) -> None:
		tex = render_resume(sample_resume_data)
		assert r"\documentclass[letterpaper,11pt]{article}" in tex
		assert "Danny Willow Liu" in tex
		assert r"\section{Education}" in tex
		assert r"\section{Experience}" in tex
		assert r"\section{Projects}" in tex
		assert r"\section{Technical Skills}" in tex
		assert r"\end{document}" in tex

	def test_renders_contact_info(self, sample_resume_data: ResumeData) -> None:
		tex = render_resume(sample_resume_data)
		assert "510-876-2949" in tex
		assert "dannywillowliu@uchicago.edu" in tex
		assert "linkedin.com/in/dwliu2" in tex

	def test_renders_experience_bullets(self, sample_resume_data: ResumeData) -> None:
		tex = render_resume(sample_resume_data)
		assert "Shipped Apache Superset" in tex
		assert "Building BloomBee" in tex

	def test_renders_skills(self, sample_resume_data: ResumeData) -> None:
		tex = render_resume(sample_resume_data)
		assert "Python, C, SQL, JavaScript" in tex
		assert "Flask, PostgreSQL, PyTorch" in tex

	def test_renders_with_variant(
		self,
		sample_resume_data: ResumeData,
		sample_variant: ResumeVariant,
	) -> None:
		tex = render_resume(sample_resume_data, sample_variant)
		assert "Danny Willow Liu" in tex
		assert r"\section{Experience}" in tex

	def test_section_order(self, sample_resume_data: ResumeData) -> None:
		variant = ResumeVariant(
			name="reordered",
			section_order=["experience", "education", "skills"],
		)
		tex = render_resume(sample_resume_data, variant)
		exp_pos = tex.index(r"\section{Experience}")
		edu_pos = tex.index(r"\section{Education}")
		assert exp_pos < edu_pos

	def test_empty_section_skipped(self) -> None:
		data = ResumeData(
			contact=ContactInfo(name="Test Person"),
			education=[
				Education(institution="MIT", degree="BS CS"),
			],
		)
		tex = render_resume(data)
		assert r"\section{Education}" in tex
		assert r"\section{Experience}" not in tex
		assert r"\section{Projects}" not in tex

	def test_preamble_matches_format(self, sample_resume_data: ResumeData) -> None:
		tex = render_resume(sample_resume_data)
		assert r"\usepackage{latexsym}" in tex
		assert r"\usepackage[empty]{fullpage}" in tex
		assert r"\resumeSubHeadingListStart" in tex
		assert r"\resumeItem{" in tex

	def test_publications_rendered(self, sample_resume_data: ResumeData) -> None:
		tex = render_resume(sample_resume_data)
		assert r"\section{Publications}" in tex
		assert "Network Effect Prediction Framework" in tex
