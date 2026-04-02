"""Shared test fixtures."""

from __future__ import annotations

import pytest

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


@pytest.fixture
def sample_contact() -> ContactInfo:
	return ContactInfo(
		name="Danny Willow Liu",
		phone="510-876-2949",
		email="dannywillowliu@uchicago.edu",
		linkedin="linkedin.com/in/dwliu2",
		github="github.com/dannywillowliu-uchi",
	)


@pytest.fixture
def sample_education() -> list[Education]:
	return [
		Education(
			institution="The University of Chicago",
			location="Chicago, IL",
			degree="Bachelor of Science in Computer Science (A.I Specialization)",
			date="Expected June 2028",
			bullets=[
				"Coursework: Systems Programming I & II, Machine Learning, Theory of Algorithms",
				"Activities: Kappa Theta Pi, TASA, Maroon Capital (Quant Club)",
			],
			tags=["cs", "ai"],
		),
	]


@pytest.fixture
def sample_experience() -> list[Experience]:
	return [
		Experience(
			company="E2 Consulting Engineers",
			location="Emeryville, CA",
			title="Software Engineer Intern",
			date="June 2025 -- September 2025",
			bullets=[
				"Shipped Apache Superset + PostgreSQL dashboard for 600+ projects",
				"Built agentic workflows with AWS Bedrock, Lambda, and RAG API",
			],
			tags=["swe", "cloud"],
		),
		Experience(
			company="Yotta-Labs",
			location="Seattle, WA",
			title="ML Engineer Intern",
			date="June 2025 -- Present",
			bullets=[
				"Building BloomBee, a decentralized LLM inference platform",
				"Developed batched tensor distributed inference sessions",
			],
			tags=["ml", "distributed"],
		),
	]


@pytest.fixture
def sample_projects() -> list[Project]:
	return [
		Project(
			name="Prediction Market Information Arbitrage",
			technologies="Flask, Playwright, Kalshi/Polymarket APIs",
			date="August 2025 -- Present",
			bullets=[
				"Exploited 2-second delay between live sports and market prices",
				"Built cross-correlation analysis on orderbook data",
			],
			tags=["trading", "swe"],
		),
	]


@pytest.fixture
def sample_publications() -> list[Publication]:
	return [
		Publication(
			title="Network Effect Prediction Framework for Crypto Technologies",
			link="https://github.com/dannywillowliu-uchi/Metcalf_Law_Crypto_Valuation",
			date="2025",
			bullets=["Extended Metcalfe's Law + Markov-switching models"],
			tags=["research", "crypto"],
		),
	]


@pytest.fixture
def sample_skills() -> list[SkillCategory]:
	return [
		SkillCategory(category="Languages", skills=["Python", "C", "SQL", "JavaScript"]),
		SkillCategory(category="Frameworks", skills=["Flask", "PostgreSQL", "PyTorch"]),
		SkillCategory(category="Developer Tools", skills=["Git", "Linux", "Docker"]),
	]


@pytest.fixture
def sample_resume_data(
	sample_contact: ContactInfo,
	sample_education: list[Education],
	sample_experience: list[Experience],
	sample_projects: list[Project],
	sample_publications: list[Publication],
	sample_skills: list[SkillCategory],
) -> ResumeData:
	return ResumeData(
		contact=sample_contact,
		education=sample_education,
		experience=sample_experience,
		projects=sample_projects,
		publications=sample_publications,
		skills=sample_skills,
	)


@pytest.fixture
def sample_variant() -> ResumeVariant:
	return ResumeVariant(
		name="swe",
		description="Software engineering variant",
		experience_indices=[0, 1],
		project_indices=[0],
		publication_indices=[0],
		education_indices=[0],
		section_order=["education", "publications", "experience", "projects", "skills"],
	)
