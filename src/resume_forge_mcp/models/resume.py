"""Pydantic models for resume data."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
	"""Contact information for resume header."""

	name: str = Field(..., description="Full name")
	phone: str = Field(default="", description="Phone number")
	email: str = Field(default="", description="Email address")
	linkedin: str = Field(default="", description="LinkedIn URL or handle")
	github: str = Field(default="", description="GitHub URL or handle")
	website: str = Field(default="", description="Personal website URL")
	summary: str = Field(default="", description="Professional summary / about me")


class Education(BaseModel):
	"""Education entry."""

	institution: str = Field(..., description="University/school name")
	location: str = Field(default="", description="City, State")
	degree: str = Field(..., description="Degree and major")
	date: str = Field(default="", description="Date or expected date")
	bullets: list[str] = Field(default_factory=list, description="Coursework, activities, etc.")
	tags: list[str] = Field(default_factory=list, description="Tags for filtering")


class Publication(BaseModel):
	"""Publication entry."""

	title: str = Field(..., description="Publication title")
	link: str = Field(default="", description="URL to paper/repo")
	link_text: str = Field(default="GitHub", description="Display text for link")
	date: str = Field(default="", description="Publication year")
	bullets: list[str] = Field(default_factory=list, description="Description bullets")
	tags: list[str] = Field(default_factory=list, description="Tags for filtering")


class Experience(BaseModel):
	"""Work experience entry."""

	company: str = Field(..., description="Company name")
	location: str = Field(default="", description="City, State")
	title: str = Field(..., description="Job title")
	date: str = Field(default="", description="Date range")
	bullets: list[str] = Field(default_factory=list, description="Achievement bullets")
	tags: list[str] = Field(default_factory=list, description="Tags for variant filtering")


class Project(BaseModel):
	"""Project entry."""

	name: str = Field(..., description="Project name")
	technologies: str = Field(default="", description="Tech stack description")
	link: str = Field(default="", description="URL to project")
	link_text: str = Field(default="GitHub", description="Display text for link")
	date: str = Field(default="", description="Date or date range")
	bullets: list[str] = Field(default_factory=list, description="Description bullets")
	tags: list[str] = Field(default_factory=list, description="Tags for variant filtering")


class SkillCategory(BaseModel):
	"""A category of skills (e.g., Languages, Frameworks)."""

	category: str = Field(..., description="Category name")
	skills: list[str] = Field(default_factory=list, description="Skills in this category")


class ResumeData(BaseModel):
	"""Master resume data pool containing all entries across variants."""

	contact: ContactInfo
	education: list[Education] = Field(default_factory=list)
	publications: list[Publication] = Field(default_factory=list)
	experience: list[Experience] = Field(default_factory=list)
	projects: list[Project] = Field(default_factory=list)
	skills: list[SkillCategory] = Field(default_factory=list)


class ResumeVariant(BaseModel):
	"""A variant selects and orders entries from the master pool."""

	name: str = Field(..., description="Variant name (e.g., 'swe', 'applied_ai')")
	description: str = Field(default="", description="What this variant targets")
	experience_indices: list[int] = Field(
		default_factory=list,
		description="Indices into ResumeData.experience, in display order",
	)
	project_indices: list[int] = Field(
		default_factory=list,
		description="Indices into ResumeData.projects, in display order",
	)
	publication_indices: list[int] = Field(
		default_factory=list,
		description="Indices into ResumeData.publications, in display order",
	)
	education_indices: list[int] = Field(
		default_factory=list,
		description="Indices into ResumeData.education, in display order",
	)
	skills_override: list[SkillCategory] | None = Field(
		default=None,
		description="Override skill categories for this variant (None = use master)",
	)
	section_order: list[str] = Field(
		default_factory=lambda: [
			"education",
			"publications",
			"experience",
			"projects",
			"skills",
		],
		description="Order of sections in the resume",
	)
	bullet_overrides: dict[str, list[str]] = Field(
		default_factory=dict,
		description="Per-entry bullet overrides keyed by 'section_index' (e.g., 'experience_0')",
	)
