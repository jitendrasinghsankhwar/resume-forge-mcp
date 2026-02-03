"""Job description parsing and resume tailoring."""

from __future__ import annotations

import re
from dataclasses import dataclass

from latex_resume_mcp.intelligence.knowledge import TECH_KEYWORDS
from latex_resume_mcp.models.analysis import JobDescription
from latex_resume_mcp.models.resume import (
	Experience,
	Project,
	ResumeData,
	ResumeVariant,
	SkillCategory,
)

# Page budget constants
PAGE_BUDGET = 52  # Conservative single-page line limit
FIXED_OVERHEAD = 12  # Header + education + skills baseline


@dataclass
class EntryScore:
	"""Score and metadata for a single entry."""

	index: int
	score: float
	estimated_lines: int
	entry_type: str  # "experience" or "project"


@dataclass
class ContentSelection:
	"""Result of content selection with details."""

	experience_indices: list[int]
	project_indices: list[int]
	experience_scores: list[EntryScore]
	project_scores: list[EntryScore]
	total_estimated_lines: int
	budget_remaining: int
	over_budget: bool


def estimate_entry_lines(entry: Experience | Project, entry_type: str) -> int:
	"""Estimate rendered lines for an entry.

	Args:
		entry: An Experience or Project entry.
		entry_type: Either "experience" or "project".

	Returns:
		Estimated number of rendered lines.
	"""
	# Header lines: company/title line + date line for experience, project name line for project
	header_lines = 2 if entry_type == "experience" else 1

	# Bullet lines: estimate ~100 chars per line after wrapping
	bullet_lines = 0
	for bullet in entry.bullets:
		bullet_lines += max(1, (len(bullet) + 99) // 100)

	return header_lines + bullet_lines


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
	jd: JobDescription,
	target_tags: list[str] | None = None,
) -> float:
	"""Score an entry's relevance to a job description.

	Uses weighted scoring:
	- Required skills: 40% weight (must-haves)
	- Preferred skills: 20% weight (nice-to-haves)
	- General keywords: 20% weight
	- Tag matching: 20% weight

	Args:
		entry_text: Combined text from the entry (title, bullets, etc.).
		entry_tags: Tags assigned to the entry.
		jd: Full JobDescription object.
		target_tags: Optional list of tags to prioritize.

	Returns:
		Relevance score from 0 to 1.
	"""
	score = 0.0
	entry_lower = entry_text.lower()

	# Required skills (40% weight) - must-haves
	if jd.required_skills:
		matched = sum(1 for s in jd.required_skills if s.lower() in entry_lower)
		score += (matched / len(jd.required_skills)) * 0.4

	# Preferred skills (20% weight) - nice-to-haves
	if jd.preferred_skills:
		matched = sum(1 for s in jd.preferred_skills if s.lower() in entry_lower)
		score += (matched / len(jd.preferred_skills)) * 0.2

	# General keywords (20% weight)
	if jd.keywords:
		matched = sum(1 for kw in jd.keywords if kw.lower() in entry_lower)
		score += min(1.0, matched / 5) * 0.2

	# Tag matching (20% weight)
	if target_tags and entry_tags:
		overlap = len(set(entry_tags) & set(target_tags))
		score += min(1.0, overlap / 2) * 0.2
	elif not target_tags:
		# No target tags specified, give partial score based on having any tags
		score += 0.1 if entry_tags else 0.0

	return score


def select_content_for_jd(
	data: ResumeData,
	jd: JobDescription,
	target_tags: list[str] | None = None,
	max_experience: int = 4,
	max_projects: int = 3,
	include_experiences: list[int] | None = None,
	exclude_experiences: list[int] | None = None,
	include_projects: list[int] | None = None,
	exclude_projects: list[int] | None = None,
	use_page_budget: bool = True,
) -> ResumeVariant:
	"""Select and order resume content based on job description relevance.

	Args:
		data: Master resume data pool.
		jd: Parsed job description.
		target_tags: Optional list of tags to prioritize (e.g., ["swe", "ml"]).
		max_experience: Maximum number of experience entries to include.
		max_projects: Maximum number of project entries to include.
		include_experiences: Force include these experience indices (in given order).
		exclude_experiences: Exclude these experience indices from selection.
		include_projects: Force include these project indices (in given order).
		exclude_projects: Exclude these project indices from selection.
		use_page_budget: Whether to respect page budget (default True).

	Returns:
		ResumeVariant with selected and ordered content.
	"""
	selection = select_content_with_details(
		data=data,
		jd=jd,
		target_tags=target_tags,
		max_experience=max_experience,
		max_projects=max_projects,
		include_experiences=include_experiences,
		exclude_experiences=exclude_experiences,
		include_projects=include_projects,
		exclude_projects=exclude_projects,
		use_page_budget=use_page_budget,
	)

	# Include all education (usually limited already)
	education_indices = list(range(len(data.education)))

	# Include all publications (usually limited already)
	publication_indices = list(range(len(data.publications)))

	# Prioritize skills that match JD keywords
	skills_override = _prioritize_skills(data.skills, jd.keywords)

	return ResumeVariant(
		name="tailored",
		description=f"Tailored for: {jd.title or 'Job Description'}",
		experience_indices=selection.experience_indices,
		project_indices=selection.project_indices,
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


def select_content_with_details(
	data: ResumeData,
	jd: JobDescription,
	target_tags: list[str] | None = None,
	max_experience: int = 4,
	max_projects: int = 3,
	include_experiences: list[int] | None = None,
	exclude_experiences: list[int] | None = None,
	include_projects: list[int] | None = None,
	exclude_projects: list[int] | None = None,
	use_page_budget: bool = True,
) -> ContentSelection:
	"""Select and order resume content with detailed scoring information.

	This is the core selection logic that returns full details for preview.

	Args:
		data: Master resume data pool.
		jd: Parsed job description.
		target_tags: Optional list of tags to prioritize.
		max_experience: Maximum number of experience entries to include.
		max_projects: Maximum number of project entries to include.
		include_experiences: Force include these experience indices (in given order).
		exclude_experiences: Exclude these experience indices from selection.
		include_projects: Force include these project indices (in given order).
		exclude_projects: Exclude these project indices from selection.
		use_page_budget: Whether to respect page budget (default True).

	Returns:
		ContentSelection with indices, scores, and budget info.
	"""
	# Initialize budget tracking
	budget_used = FIXED_OVERHEAD if use_page_budget else 0
	budget = PAGE_BUDGET if use_page_budget else float("inf")

	# Normalize include/exclude lists
	include_exp = set(include_experiences or [])
	exclude_exp = set(exclude_experiences or [])
	include_proj = set(include_projects or [])
	exclude_proj = set(exclude_projects or [])

	# Score all experiences
	exp_scores: list[EntryScore] = []
	for i, exp in enumerate(data.experience):
		if i in exclude_exp:
			continue
		entry_text = f"{exp.title} {exp.company} {' '.join(exp.bullets)}"
		score = _score_entry_relevance(entry_text, exp.tags, jd, target_tags)
		lines = estimate_entry_lines(exp, "experience")
		exp_scores.append(EntryScore(
			index=i, score=score, estimated_lines=lines, entry_type="experience"
		))

	# Score all projects
	proj_scores: list[EntryScore] = []
	for i, proj in enumerate(data.projects):
		if i in exclude_proj:
			continue
		entry_text = f"{proj.name} {proj.technologies} {' '.join(proj.bullets)}"
		score = _score_entry_relevance(entry_text, proj.tags, jd, target_tags)
		lines = estimate_entry_lines(proj, "project")
		proj_scores.append(EntryScore(
			index=i, score=score, estimated_lines=lines, entry_type="project"
		))

	# Select experiences: forced includes first, then by score
	selected_exp: list[int] = []
	selected_exp_scores: list[EntryScore] = []

	# Add forced includes first (in specified order)
	for idx in include_experiences or []:
		if idx in exclude_exp:
			continue
		entry_score = next((e for e in exp_scores if e.index == idx), None)
		if entry_score:
			if use_page_budget and budget_used + entry_score.estimated_lines > budget:
				break  # Over budget, stop adding
			selected_exp.append(idx)
			selected_exp_scores.append(entry_score)
			budget_used += entry_score.estimated_lines

	# Sort remaining by score and fill remaining slots
	remaining_exp = [
		e for e in exp_scores
		if e.index not in selected_exp and e.index not in include_exp
	]
	remaining_exp.sort(key=lambda x: x.score, reverse=True)

	for entry_score in remaining_exp:
		if len(selected_exp) >= max_experience:
			break
		if use_page_budget and budget_used + entry_score.estimated_lines > budget:
			continue  # Skip this entry, try next (might fit)
		selected_exp.append(entry_score.index)
		selected_exp_scores.append(entry_score)
		budget_used += entry_score.estimated_lines

	# Select projects: forced includes first, then by score
	selected_proj: list[int] = []
	selected_proj_scores: list[EntryScore] = []

	# Add forced includes first (in specified order)
	for idx in include_projects or []:
		if idx in exclude_proj:
			continue
		entry_score = next((e for e in proj_scores if e.index == idx), None)
		if entry_score:
			if use_page_budget and budget_used + entry_score.estimated_lines > budget:
				break  # Over budget, stop adding
			selected_proj.append(idx)
			selected_proj_scores.append(entry_score)
			budget_used += entry_score.estimated_lines

	# Sort remaining by score and fill remaining slots
	remaining_proj = [
		e for e in proj_scores
		if e.index not in selected_proj and e.index not in include_proj
	]
	remaining_proj.sort(key=lambda x: x.score, reverse=True)

	for entry_score in remaining_proj:
		if len(selected_proj) >= max_projects:
			break
		if use_page_budget and budget_used + entry_score.estimated_lines > budget:
			continue  # Skip this entry, try next (might fit)
		selected_proj.append(entry_score.index)
		selected_proj_scores.append(entry_score)
		budget_used += entry_score.estimated_lines

	return ContentSelection(
		experience_indices=selected_exp,
		project_indices=selected_proj,
		experience_scores=selected_exp_scores,
		project_scores=selected_proj_scores,
		total_estimated_lines=budget_used,
		budget_remaining=int(budget - budget_used) if use_page_budget else -1,
		over_budget=budget_used > budget if use_page_budget else False,
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
	max_experience: int = 4,
	max_projects: int = 3,
	include_experiences: list[int] | None = None,
	exclude_experiences: list[int] | None = None,
	include_projects: list[int] | None = None,
	exclude_projects: list[int] | None = None,
) -> tuple[ResumeVariant, JobDescription]:
	"""High-level function to generate a tailored resume variant from JD text.

	Args:
		data: Master resume data pool.
		jd_text: Raw job description text.
		variant_name: Name for the generated variant.
		target_tags: Optional list of tags to prioritize.
		max_experience: Maximum number of experience entries to include.
		max_projects: Maximum number of project entries to include.
		include_experiences: Force include these experience indices (in given order).
		exclude_experiences: Exclude these experience indices from selection.
		include_projects: Force include these project indices (in given order).
		exclude_projects: Exclude these project indices from selection.

	Returns:
		Tuple of (generated variant, parsed job description).
	"""
	jd = parse_job_description(jd_text)
	variant = select_content_for_jd(
		data,
		jd,
		target_tags,
		max_experience=max_experience,
		max_projects=max_projects,
		include_experiences=include_experiences,
		exclude_experiences=exclude_experiences,
		include_projects=include_projects,
		exclude_projects=exclude_projects,
	)
	variant = variant.model_copy(update={"name": variant_name})
	return variant, jd
