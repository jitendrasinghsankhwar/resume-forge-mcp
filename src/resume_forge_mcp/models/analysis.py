"""Pydantic models for resume analysis and scoring."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BulletScore(BaseModel):
	"""Quality score for a single resume bullet point."""

	text: str = Field(..., description="The bullet text being scored")
	has_action_verb: bool = Field(default=False, description="Starts with a strong action verb")
	has_metric: bool = Field(default=False, description="Contains quantifiable result")
	has_technical_detail: bool = Field(
		default=False, description="Mentions specific technology or method"
	)
	has_xyz_structure: bool = Field(
		default=False,
		description="Follows XYZ impact format: did X, with Y, achieving Z",
	)
	has_line_orphan: bool = Field(
		default=False,
		description="Last line has orphaned word(s) creating whitespace",
	)
	appropriate_length: bool = Field(
		default=False, description="Between 15 and 150 characters"
	)
	score: float = Field(
		default=0.0, ge=0.0, le=1.0, description="Overall bullet quality 0-1"
	)
	suggestions: list[str] = Field(
		default_factory=list, description="Improvement suggestions"
	)


class SectionScore(BaseModel):
	"""Quality score for a resume section."""

	section: str = Field(..., description="Section name")
	bullet_count: int = Field(default=0, description="Number of bullets")
	avg_bullet_score: float = Field(default=0.0, description="Average bullet quality")
	bullet_scores: list[BulletScore] = Field(default_factory=list)
	suggestions: list[str] = Field(default_factory=list)


class ATSReport(BaseModel):
	"""ATS (Applicant Tracking System) compatibility report."""

	is_compatible: bool = Field(default=True, description="Overall ATS compatibility")
	issues: list[str] = Field(default_factory=list, description="ATS compatibility issues")
	warnings: list[str] = Field(default_factory=list, description="Non-critical ATS warnings")


class KeywordMatch(BaseModel):
	"""Keyword match analysis against a job description."""

	matched: list[str] = Field(default_factory=list, description="Keywords found in resume")
	missing: list[str] = Field(default_factory=list, description="Keywords not found in resume")
	match_percentage: float = Field(default=0.0, description="Percentage of JD keywords matched")


class PageAnalysis(BaseModel):
	"""Analysis of resume page layout."""

	page_count: int = Field(default=1, description="Number of pages")
	estimated_fullness: float = Field(
		default=0.0,
		ge=0.0,
		le=1.0,
		description="Estimated page utilization 0-1",
	)
	overflow: bool = Field(default=False, description="Content overflows to second page")
	underflow: bool = Field(
		default=False, description="Significant whitespace at bottom"
	)


class ResumeScore(BaseModel):
	"""Complete resume quality assessment."""

	overall_score: float = Field(
		default=0.0, ge=0.0, le=1.0, description="Overall quality 0-1"
	)
	section_scores: list[SectionScore] = Field(default_factory=list)
	ats_report: ATSReport = Field(default_factory=ATSReport)
	keyword_match: KeywordMatch | None = Field(
		default=None, description="Keyword match if JD provided"
	)
	page_analysis: PageAnalysis = Field(default_factory=PageAnalysis)
	top_suggestions: list[str] = Field(
		default_factory=list,
		description="Top 5 actionable improvements",
	)


class JobDescription(BaseModel):
	"""Parsed job description for tailoring."""

	title: str = Field(default="", description="Job title")
	company: str = Field(default="", description="Company name")
	required_skills: list[str] = Field(default_factory=list)
	preferred_skills: list[str] = Field(default_factory=list)
	keywords: list[str] = Field(
		default_factory=list, description="All extracted keywords"
	)
	responsibilities: list[str] = Field(default_factory=list)
	raw_text: str = Field(default="", description="Original JD text")
