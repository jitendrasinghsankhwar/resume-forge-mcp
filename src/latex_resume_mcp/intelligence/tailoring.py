"""Job description parsing and resume tailoring."""

from __future__ import annotations

import re

from latex_resume_mcp.intelligence.knowledge import TECH_KEYWORDS
from latex_resume_mcp.models.analysis import JobDescription
from latex_resume_mcp.models.resume import (
	ResumeData,
	ResumeVariant,
	SkillCategory,
)


def _extract_keywords_from_text(text: str) -> list[str]:
	"""Extract potential keywords from text."""
	# Normalize text
	text = text.lower()

	# Build a set of known tech keywords (lowercased)
	known_keywords: set[str] = set()
	for category_keywords in TECH_KEYWORDS.values():
		known_keywords.update(kw.lower() for kw in category_keywords)

	# Find known keywords in text
	found: list[str] = []
	for kw in known_keywords:
		# Word boundary search
		if re.search(rf"\b{re.escape(kw)}\b", text):
			# Return original case from TECH_KEYWORDS
			for category_keywords in TECH_KEYWORDS.values():
				for original in category_keywords:
					if original.lower() == kw:
						found.append(original)
						break

	return list(set(found))  # Deduplicate


def _extract_requirements(text: str) -> tuple[list[str], list[str]]:
	"""Extract required and preferred skills from JD text.

	Returns:
		Tuple of (required_skills, preferred_skills).
	"""
	lines = text.split("\n")
	required: list[str] = []
	preferred: list[str] = []

	# Patterns that indicate requirements section
	required_patterns = [
		r"required",
		r"must have",
		r"requirements",
		r"qualifications",
		r"you will need",
	]
	preferred_patterns = [
		r"nice to have",
		r"preferred",
		r"bonus",
		r"plus",
		r"ideally",
	]

	current_section = "general"

	for line in lines:
		line_lower = line.lower()

		# Check section headers
		if any(re.search(p, line_lower) for p in required_patterns):
			current_section = "required"
		elif any(re.search(p, line_lower) for p in preferred_patterns):
			current_section = "preferred"

		# Extract keywords from line
		keywords = _extract_keywords_from_text(line)

		if current_section == "required":
			required.extend(keywords)
		elif current_section == "preferred":
			preferred.extend(keywords)
		else:
			# Default to required for general mentions
			required.extend(keywords)

	return list(set(required)), list(set(preferred))


def _extract_responsibilities(text: str) -> list[str]:
	"""Extract job responsibilities from JD text."""
	lines = text.split("\n")
	responsibilities: list[str] = []

	# Patterns that indicate responsibilities section
	resp_patterns = [
		r"responsibilities",
		r"you will",
		r"what you.ll do",
		r"role overview",
		r"about the role",
		r"job description",
	]

	in_resp_section = False

	for line in lines:
		line_stripped = line.strip()
		line_lower = line_stripped.lower()

		# Check if entering responsibilities section
		if any(re.search(p, line_lower) for p in resp_patterns):
			in_resp_section = True
			continue

		# Check if leaving (new section header)
		if (
			in_resp_section
			and line_stripped
			and not line_stripped.startswith(("-", "•", "*"))
			and re.match(r"^[A-Z][a-z]+:", line_stripped)
		):
			in_resp_section = False
			continue

		# Collect bullet points in responsibilities section
		if in_resp_section and line_stripped:
			# Clean bullet markers
			cleaned = re.sub(r"^[-•*]\s*", "", line_stripped)
			if len(cleaned) > 10:  # Skip very short lines
				responsibilities.append(cleaned)

	return responsibilities[:10]  # Limit to top 10


def parse_job_description(text: str) -> JobDescription:
	"""Parse a job description to extract structured data.

	Args:
		text: Raw job description text.

	Returns:
		JobDescription with extracted title, company, skills, and keywords.
	"""
	# Extract title (usually first line or after "Title:")
	title = ""
	lines = text.strip().split("\n")
	for line in lines[:5]:  # Check first 5 lines
		line = line.strip()
		if line and not line.lower().startswith(("about", "we are", "company")):
			# Remove common prefixes
			title = re.sub(r"^(title|position|role):\s*", "", line, flags=re.IGNORECASE)
			break

	# Extract company (look for "Company:" or "at <Company>")
	company = ""
	company_match = re.search(r"(?:company|at|@):\s*([^\n]+)", text, re.IGNORECASE)
	if company_match:
		company = company_match.group(1).strip()

	# Extract required and preferred skills
	required_skills, preferred_skills = _extract_requirements(text)

	# Extract all keywords
	all_keywords = _extract_keywords_from_text(text)

	# Extract responsibilities
	responsibilities = _extract_responsibilities(text)

	return JobDescription(
		title=title,
		company=company,
		required_skills=required_skills,
		preferred_skills=preferred_skills,
		keywords=all_keywords,
		responsibilities=responsibilities,
		raw_text=text,
	)


def _score_entry_relevance(
	entry_text: str,
	entry_tags: list[str],
	keywords: list[str],
	target_tags: list[str] | None = None,
) -> float:
	"""Score an entry's relevance to a job description.

	Args:
		entry_text: Combined text from the entry (title, bullets, etc.).
		entry_tags: Tags assigned to the entry.
		keywords: Keywords from the job description.
		target_tags: Optional list of tags to prioritize.

	Returns:
		Relevance score from 0 to 1.
	"""
	score = 0.0
	entry_lower = entry_text.lower()

	# Keyword matching (60% weight)
	if keywords:
		matched = sum(1 for kw in keywords if kw.lower() in entry_lower)
		keyword_score = min(1.0, matched / max(3, len(keywords) * 0.3))
		score += keyword_score * 0.6

	# Tag matching (40% weight)
	if target_tags and entry_tags:
		tag_overlap = len(set(entry_tags) & set(target_tags))
		tag_score = min(1.0, tag_overlap / max(1, len(target_tags) * 0.5))
		score += tag_score * 0.4
	elif not target_tags:
		# No target tags specified, give partial score based on having any tags
		score += 0.2 if entry_tags else 0.0

	return score


def select_content_for_jd(
	data: ResumeData,
	jd: JobDescription,
	target_tags: list[str] | None = None,
	max_experience: int = 4,
	max_projects: int = 4,
) -> ResumeVariant:
	"""Select and order resume content based on job description relevance.

	Args:
		data: Master resume data pool.
		jd: Parsed job description.
		target_tags: Optional list of tags to prioritize (e.g., ["swe", "ml"]).
		max_experience: Maximum number of experience entries to include.
		max_projects: Maximum number of project entries to include.

	Returns:
		ResumeVariant with selected and ordered content.
	"""
	keywords = jd.keywords

	# Score and rank experiences
	exp_scores: list[tuple[int, float]] = []
	for i, exp in enumerate(data.experience):
		entry_text = f"{exp.title} {exp.company} {' '.join(exp.bullets)}"
		score = _score_entry_relevance(entry_text, exp.tags, keywords, target_tags)
		exp_scores.append((i, score))

	exp_scores.sort(key=lambda x: x[1], reverse=True)
	experience_indices = [idx for idx, _ in exp_scores[:max_experience]]

	# Score and rank projects
	proj_scores: list[tuple[int, float]] = []
	for i, proj in enumerate(data.projects):
		entry_text = f"{proj.name} {proj.technologies} {' '.join(proj.bullets)}"
		score = _score_entry_relevance(entry_text, proj.tags, keywords, target_tags)
		proj_scores.append((i, score))

	proj_scores.sort(key=lambda x: x[1], reverse=True)
	project_indices = [idx for idx, _ in proj_scores[:max_projects]]

	# Include all education (usually limited already)
	education_indices = list(range(len(data.education)))

	# Include all publications (usually limited already)
	publication_indices = list(range(len(data.publications)))

	# Prioritize skills that match JD keywords
	skills_override = _prioritize_skills(data.skills, keywords)

	return ResumeVariant(
		name="tailored",
		description=f"Tailored for: {jd.title or 'Job Description'}",
		experience_indices=experience_indices,
		project_indices=project_indices,
		education_indices=education_indices,
		publication_indices=publication_indices,
		skills_override=skills_override,
		section_order=[
			"education",
			"publications",
			"experience",
			"projects",
			"skills",
		],
	)


def _prioritize_skills(
	skills: list[SkillCategory],
	keywords: list[str],
) -> list[SkillCategory]:
	"""Reorder skills to prioritize those matching JD keywords.

	Args:
		skills: Original skill categories.
		keywords: Keywords from job description.

	Returns:
		Skill categories with skills reordered by relevance.
	"""
	keywords_lower = {kw.lower() for kw in keywords}

	result: list[SkillCategory] = []
	for cat in skills:
		# Score each skill
		scored_skills: list[tuple[str, int]] = []
		for skill in cat.skills:
			# Check if skill matches any keyword
			score = 2 if skill.lower() in keywords_lower else 0
			# Partial match bonus
			if score == 0:
				for kw in keywords_lower:
					if kw in skill.lower() or skill.lower() in kw:
						score = 1
						break
			scored_skills.append((skill, score))

		# Sort by score (descending), maintaining original order for ties
		scored_skills.sort(key=lambda x: -x[1])
		reordered_skills = [skill for skill, _ in scored_skills]

		result.append(SkillCategory(category=cat.category, skills=reordered_skills))

	return result


def generate_tailored_variant(
	data: ResumeData,
	jd_text: str,
	variant_name: str = "tailored",
	target_tags: list[str] | None = None,
) -> tuple[ResumeVariant, JobDescription]:
	"""High-level function to generate a tailored resume variant from JD text.

	Args:
		data: Master resume data pool.
		jd_text: Raw job description text.
		variant_name: Name for the generated variant.
		target_tags: Optional list of tags to prioritize.

	Returns:
		Tuple of (generated variant, parsed job description).
	"""
	jd = parse_job_description(jd_text)
	variant = select_content_for_jd(data, jd, target_tags)
	variant = variant.model_copy(update={"name": variant_name})
	return variant, jd
