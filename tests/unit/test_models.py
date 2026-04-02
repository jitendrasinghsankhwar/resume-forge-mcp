"""Tests for Pydantic resume and analysis models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from resume_forge_mcp.models.analysis import (
	ATSReport,
	BulletScore,
	JobDescription,
	KeywordMatch,
	PageAnalysis,
	ResumeScore,
	SectionScore,
)
from resume_forge_mcp.models.resume import (
	ContactInfo,
	Education,
	Experience,
	Project,
	Publication,
	ResumeData,
	ResumeVariant,
	SkillCategory,
)

# -- ContactInfo --


class TestContactInfo:
	def test_required_name(self) -> None:
		info = ContactInfo(name="Danny Liu")
		assert info.name == "Danny Liu"
		assert info.phone == ""

	def test_full_contact(self, sample_contact: ContactInfo) -> None:
		assert sample_contact.name == "Danny Willow Liu"
		assert sample_contact.email == "dannywillowliu@uchicago.edu"
		assert sample_contact.linkedin == "linkedin.com/in/dwliu2"

	def test_missing_name_fails(self) -> None:
		with pytest.raises(ValidationError):
			ContactInfo()  # type: ignore[call-arg]


# -- Education --


class TestEducation:
	def test_minimal(self) -> None:
		edu = Education(institution="MIT", degree="BS CS")
		assert edu.institution == "MIT"
		assert edu.bullets == []
		assert edu.tags == []

	def test_with_bullets(self, sample_education: list[Education]) -> None:
		edu = sample_education[0]
		assert len(edu.bullets) == 2
		assert "Coursework" in edu.bullets[0]


# -- Experience --


class TestExperience:
	def test_minimal(self) -> None:
		exp = Experience(company="Acme", title="SWE")
		assert exp.company == "Acme"
		assert exp.location == ""

	def test_with_tags(self, sample_experience: list[Experience]) -> None:
		assert "swe" in sample_experience[0].tags
		assert "ml" in sample_experience[1].tags

	def test_missing_required_fails(self) -> None:
		with pytest.raises(ValidationError):
			Experience(company="Acme")  # type: ignore[call-arg]


# -- Project --


class TestProject:
	def test_minimal(self) -> None:
		proj = Project(name="My Project")
		assert proj.name == "My Project"
		assert proj.technologies == ""

	def test_full_project(self, sample_projects: list[Project]) -> None:
		proj = sample_projects[0]
		assert "Flask" in proj.technologies
		assert len(proj.bullets) == 2


# -- Publication --


class TestPublication:
	def test_minimal(self) -> None:
		pub = Publication(title="My Paper")
		assert pub.link_text == "GitHub"

	def test_with_link(self, sample_publications: list[Publication]) -> None:
		assert "github.com" in sample_publications[0].link


# -- SkillCategory --


class TestSkillCategory:
	def test_creation(self) -> None:
		cat = SkillCategory(category="Languages", skills=["Python", "C"])
		assert len(cat.skills) == 2

	def test_empty_skills(self) -> None:
		cat = SkillCategory(category="Tools")
		assert cat.skills == []


# -- ResumeData --


class TestResumeData:
	def test_full_data(self, sample_resume_data: ResumeData) -> None:
		assert sample_resume_data.contact.name == "Danny Willow Liu"
		assert len(sample_resume_data.experience) == 2
		assert len(sample_resume_data.projects) == 1
		assert len(sample_resume_data.skills) == 3

	def test_serialization_roundtrip(self, sample_resume_data: ResumeData) -> None:
		json_str = sample_resume_data.model_dump_json()
		restored = ResumeData.model_validate_json(json_str)
		assert restored.contact.name == sample_resume_data.contact.name
		assert len(restored.experience) == len(sample_resume_data.experience)
		assert restored.experience[0].bullets == sample_resume_data.experience[0].bullets

	def test_empty_sections(self) -> None:
		data = ResumeData(contact=ContactInfo(name="Test"))
		assert data.education == []
		assert data.experience == []
		assert data.projects == []


# -- ResumeVariant --


class TestResumeVariant:
	def test_default_section_order(self) -> None:
		v = ResumeVariant(name="test")
		assert v.section_order == [
			"education",
			"publications",
			"experience",
			"projects",
			"skills",
		]

	def test_custom_order(self) -> None:
		v = ResumeVariant(
			name="custom",
			section_order=["experience", "education", "skills"],
		)
		assert v.section_order[0] == "experience"

	def test_skills_override(self, sample_skills: list[SkillCategory]) -> None:
		v = ResumeVariant(name="custom", skills_override=sample_skills)
		assert v.skills_override is not None
		assert len(v.skills_override) == 3

	def test_bullet_overrides(self) -> None:
		v = ResumeVariant(
			name="tailored",
			bullet_overrides={"experience_0": ["Custom bullet 1", "Custom bullet 2"]},
		)
		assert "experience_0" in v.bullet_overrides

	def test_variant_serialization(self, sample_variant: ResumeVariant) -> None:
		json_str = sample_variant.model_dump_json()
		restored = ResumeVariant.model_validate_json(json_str)
		assert restored.name == "swe"
		assert restored.experience_indices == [0, 1]


# -- BulletScore --


class TestBulletScore:
	def test_score_bounds(self) -> None:
		bs = BulletScore(text="test", score=0.5)
		assert bs.score == 0.5

	def test_score_too_high(self) -> None:
		with pytest.raises(ValidationError):
			BulletScore(text="test", score=1.5)

	def test_score_too_low(self) -> None:
		with pytest.raises(ValidationError):
			BulletScore(text="test", score=-0.1)

	def test_defaults(self) -> None:
		bs = BulletScore(text="Built a system")
		assert not bs.has_action_verb
		assert not bs.has_metric
		assert bs.suggestions == []


# -- SectionScore --


class TestSectionScore:
	def test_creation(self) -> None:
		ss = SectionScore(section="Experience", bullet_count=3, avg_bullet_score=0.7)
		assert ss.section == "Experience"


# -- ATSReport --


class TestATSReport:
	def test_defaults(self) -> None:
		report = ATSReport()
		assert report.is_compatible is True
		assert report.issues == []

	def test_with_issues(self) -> None:
		report = ATSReport(
			is_compatible=False,
			issues=["Uses graphics", "Non-standard headings"],
		)
		assert not report.is_compatible
		assert len(report.issues) == 2


# -- KeywordMatch --


class TestKeywordMatch:
	def test_calculation(self) -> None:
		km = KeywordMatch(
			matched=["Python", "AWS"],
			missing=["Kubernetes"],
			match_percentage=66.7,
		)
		assert len(km.matched) == 2
		assert len(km.missing) == 1


# -- PageAnalysis --


class TestPageAnalysis:
	def test_defaults(self) -> None:
		pa = PageAnalysis()
		assert pa.page_count == 1
		assert not pa.overflow

	def test_overflow(self) -> None:
		pa = PageAnalysis(page_count=2, overflow=True, estimated_fullness=1.0)
		assert pa.overflow

	def test_fullness_bounds(self) -> None:
		with pytest.raises(ValidationError):
			PageAnalysis(estimated_fullness=1.5)


# -- ResumeScore --


class TestResumeScore:
	def test_defaults(self) -> None:
		rs = ResumeScore()
		assert rs.overall_score == 0.0
		assert rs.keyword_match is None

	def test_full_score(self) -> None:
		rs = ResumeScore(
			overall_score=0.85,
			section_scores=[
				SectionScore(section="Experience", bullet_count=5, avg_bullet_score=0.8)
			],
			ats_report=ATSReport(is_compatible=True),
			keyword_match=KeywordMatch(
				matched=["Python"], missing=[], match_percentage=100.0
			),
			page_analysis=PageAnalysis(page_count=1, estimated_fullness=0.9),
			top_suggestions=["Add more metrics to bullets"],
		)
		assert rs.overall_score == 0.85
		assert len(rs.top_suggestions) == 1


# -- JobDescription --


class TestJobDescription:
	def test_minimal(self) -> None:
		jd = JobDescription()
		assert jd.title == ""
		assert jd.keywords == []

	def test_full_jd(self) -> None:
		jd = JobDescription(
			title="Software Engineer",
			company="Google",
			required_skills=["Python", "Go", "Kubernetes"],
			preferred_skills=["ML experience"],
			keywords=["Python", "Go", "Kubernetes", "ML", "distributed systems"],
			responsibilities=["Design and implement scalable systems"],
			raw_text="We are looking for a software engineer...",
		)
		assert len(jd.required_skills) == 3
		assert jd.company == "Google"
