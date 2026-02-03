"""Resume analysis and scoring functions."""

from __future__ import annotations

import re

from latex_resume_mcp.intelligence.knowledge import (
	ALL_ACTION_VERBS,
	METRIC_PATTERNS,
	SECTION_GUIDELINES,
)
from latex_resume_mcp.models.analysis import (
	ATSReport,
	BulletScore,
	KeywordMatch,
	PageAnalysis,
	ResumeScore,
	SectionScore,
)
from latex_resume_mcp.models.resume import ResumeData


def _check_xyz_structure(text: str) -> bool:
	"""Check if bullet follows XYZ impact structure: did X, with/using Y, achieving Z.

	The XYZ format ensures bullets have:
	- X: What you did (action)
	- Y: How you did it (method/tools)
	- Z: Impact/result (quantified outcome)
	"""
	text_lower = text.lower()

	# Method indicators (the "Y" - how you did it)
	method_patterns = [
		r"\busing\b",
		r"\bwith\b",
		r"\bvia\b",
		r"\bleveraging\b",
		r"\butilizing\b",
		r"\bthrough\b",
		r"\bin\b\s+\w+",  # "in Python", "in React"
	]
	has_method = any(re.search(p, text_lower) for p in method_patterns)

	# Impact indicators (the "Z" - the result)
	impact_patterns = [
		r"\bachieving\b",
		r"\bresulting\s+in\b",
		r"\breducing\b",
		r"\bimproving\b",
		r"\bincreasing\b",
		r"\bsaving\b",
		r"\benabling\b",
		r"\bdelivering\b",
		r"\bdriving\b",
		r",\s*(which|that)\s+",  # "which reduced", "that improved"
		r"\d+%",  # Direct percentage impact
		r"\d+x\b",  # Multiplier impact
		r"\d+\s*(hrs?|hours?|minutes?)\b",  # Time savings
	]
	has_impact = any(re.search(p, text_lower) for p in impact_patterns)

	return has_method and has_impact


def _check_line_orphan(text: str, chars_per_line: int = 95) -> bool:
	"""Check if bullet would create an orphaned word on the last line.

	An orphan is when the last line has very few characters (< 20% of line width),
	creating wasted whitespace. This is a heuristic based on character count.

	Args:
		text: The bullet text.
		chars_per_line: Approximate characters per line (95 for Jake template at 11pt).

	Returns:
		True if last line would be orphaned (< 20% full).
	"""
	# Rough estimate: strip LaTeX commands for length calculation
	clean_text = re.sub(r"\$[^$]+\$", "X" * 3, text)  # Math mode -> 3 chars
	clean_text = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", lambda m: "X" * 5, clean_text)  # Commands

	length = len(clean_text)
	if length <= chars_per_line:
		return False  # Single line, no orphan possible

	# Calculate last line length
	last_line_len = length % chars_per_line
	orphan_threshold = chars_per_line * 0.20  # Less than 20% = orphan

	return 0 < last_line_len < orphan_threshold


def score_bullet(text: str) -> BulletScore:
	"""Score a single resume bullet point for quality.

	Evaluates:
	- Starts with strong action verb
	- Contains quantifiable metric/result
	- Has technical detail
	- Follows XYZ impact structure (did X, with Y, for Z)
	- No orphaned words on last line
	- Appropriate length (15-150 chars)

	Args:
		text: The bullet point text to score.

	Returns:
		BulletScore with detailed breakdown and suggestions.
	"""
	text = text.strip()
	suggestions: list[str] = []

	# Check for action verb at start
	first_word = text.split()[0].rstrip(".,;:") if text else ""
	has_action_verb = first_word.lower() in ALL_ACTION_VERBS

	if not has_action_verb:
		suggestions.append("Start with a strong action verb (e.g., 'Developed', 'Built', 'Led')")

	# Check for metrics/quantifiable results
	has_metric = any(re.search(pattern, text) for pattern in METRIC_PATTERNS)

	if not has_metric:
		suggestions.append("Add quantifiable results (e.g., 'reduced latency by 40%')")

	# Check for technical detail (simple heuristic: capital letters or tech-looking words)
	tech_indicators = [
		r"[A-Z][A-Za-z]+\s+(API|SDK|CLI|DB)",
		r"[A-Z]{2,}",  # Acronyms like AWS, API, SQL
		r"[a-z]+\.[a-z]+",  # Module paths like sklearn.model
		r"[A-Za-z]+\d+",  # Versioned names like Python3
	]
	has_technical_detail = any(re.search(p, text) for p in tech_indicators)

	# Check XYZ impact structure
	has_xyz_structure = _check_xyz_structure(text)
	if not has_xyz_structure:
		suggestions.append(
			"Use XYZ format: '[Action] [task] using [tool], [achieving] [impact]'"
		)

	# Check for line orphans
	has_line_orphan = _check_line_orphan(text)
	if has_line_orphan:
		suggestions.append(
			"Adjust length to fill line (add detail or trim to avoid orphaned words)"
		)

	# Check length
	length = len(text)
	appropriate_length = 15 <= length <= 150

	if length < 15:
		suggestions.append("Bullet is too short; add more context")
	elif length > 150:
		suggestions.append("Bullet is too long; consider splitting or condensing")

	# Calculate overall score (0-1)
	# Weights: action verb 20%, metric 25%, technical 15%, XYZ 25%, length 10%, no orphan 5%
	score_components = [
		(has_action_verb, 0.20),
		(has_metric, 0.25),
		(has_technical_detail, 0.15),
		(has_xyz_structure, 0.25),
		(appropriate_length, 0.10),
		(not has_line_orphan, 0.05),
	]
	score = sum(weight for present, weight in score_components if present)

	return BulletScore(
		text=text,
		has_action_verb=has_action_verb,
		has_metric=has_metric,
		has_technical_detail=has_technical_detail,
		has_xyz_structure=has_xyz_structure,
		has_line_orphan=has_line_orphan,
		appropriate_length=appropriate_length,
		score=round(score, 2),
		suggestions=suggestions,
	)


def _score_section(
	section_name: str,
	bullets: list[str],
	target_range: tuple[int, int],
) -> SectionScore:
	"""Score a resume section based on bullet quality and count."""
	bullet_scores = [score_bullet(b) for b in bullets]
	avg_score = (
		sum(bs.score for bs in bullet_scores) / len(bullet_scores)
		if bullet_scores
		else 0.0
	)

	suggestions: list[str] = []
	min_bullets, max_bullets = target_range
	bullet_count = len(bullets)

	if bullet_count < min_bullets:
		suggestions.append(f"Add more bullets (target: {min_bullets}-{max_bullets})")
	elif bullet_count > max_bullets:
		suggestions.append(f"Consider reducing bullets (target: {min_bullets}-{max_bullets})")

	# Collect top suggestions from low-scoring bullets
	low_bullets = sorted(bullet_scores, key=lambda bs: bs.score)[:3]
	for bs in low_bullets:
		if bs.suggestions and bs.score < 0.7:
			suggestions.extend(bs.suggestions[:1])

	return SectionScore(
		section=section_name,
		bullet_count=bullet_count,
		avg_bullet_score=round(avg_score, 2),
		bullet_scores=bullet_scores,
		suggestions=suggestions[:5],  # Limit suggestions
	)


def check_ats(data: ResumeData) -> ATSReport:
	"""Check resume data for ATS compatibility.

	Args:
		data: The resume data to check.

	Returns:
		ATSReport with compatibility status, issues, and warnings.
	"""
	issues: list[str] = []
	warnings: list[str] = []

	# Check for standard section headings (we use them, so this is usually fine)
	# This check is more relevant when analyzing raw LaTeX

	# Check skills section structure
	if not data.skills:
		issues.append("Missing skills section - ATS may fail to extract skill keywords")
	elif len(data.skills) < 2:
		warnings.append("Consider organizing skills into more categories for better parsing")

	# Check for mixed acronym/full terms in bullets
	all_bullets: list[str] = []
	for exp in data.experience:
		all_bullets.extend(exp.bullets)
	for proj in data.projects:
		all_bullets.extend(proj.bullets)

	# Look for common acronyms without expansion
	acronyms_without_expansion = [
		("AWS", "Amazon Web Services"),
		("GCP", "Google Cloud Platform"),
		("CI/CD", "Continuous Integration"),
		("ML", "Machine Learning"),
		("AI", "Artificial Intelligence"),
	]

	full_text = " ".join(all_bullets)
	for acronym, full_term in acronyms_without_expansion:
		if acronym in full_text and full_term not in full_text:
			warnings.append(
				f"Consider including '{full_term}' alongside '{acronym}' for ATS parsing"
			)

	# Check education section
	if not data.education:
		warnings.append("Missing education section - some ATS systems require this")

	# Check contact info
	if not data.contact.email:
		issues.append("Missing email address - critical for ATS and recruiters")
	if not data.contact.phone:
		warnings.append("Consider adding phone number for recruiter contact")

	return ATSReport(
		is_compatible=len(issues) == 0,
		issues=issues,
		warnings=warnings,
	)


def match_keywords(
	data: ResumeData,
	keywords: list[str],
) -> KeywordMatch:
	"""Match resume content against a list of keywords.

	Args:
		data: The resume data to search.
		keywords: Keywords to look for (typically from a job description).

	Returns:
		KeywordMatch with matched/missing keywords and percentage.
	"""
	# Build searchable text from resume
	text_parts = []

	# Add skills
	for cat in data.skills:
		text_parts.extend(cat.skills)

	# Add experience content
	for exp in data.experience:
		text_parts.append(exp.title)
		text_parts.extend(exp.bullets)

	# Add project content
	for proj in data.projects:
		text_parts.append(proj.name)
		text_parts.append(proj.technologies)
		text_parts.extend(proj.bullets)

	# Add education bullets
	for edu in data.education:
		text_parts.extend(edu.bullets)

	full_text = " ".join(text_parts).lower()

	matched: list[str] = []
	missing: list[str] = []

	for keyword in keywords:
		# Check for keyword presence (case-insensitive, word boundary)
		pattern = rf"\b{re.escape(keyword.lower())}\b"
		if re.search(pattern, full_text):
			matched.append(keyword)
		else:
			missing.append(keyword)

	match_pct = (len(matched) / len(keywords) * 100) if keywords else 0.0

	return KeywordMatch(
		matched=matched,
		missing=missing,
		match_percentage=round(match_pct, 1),
	)


def estimate_page_fullness(data: ResumeData) -> PageAnalysis:
	"""Estimate how full the resume page is.

	This is a heuristic based on content counts, not actual rendering.

	Args:
		data: The resume data to analyze.

	Returns:
		PageAnalysis with estimated fullness and overflow/underflow flags.
	"""
	# Count content elements
	total_bullets = 0
	for exp in data.experience:
		total_bullets += len(exp.bullets)
	for proj in data.projects:
		total_bullets += len(proj.bullets)
	for edu in data.education:
		total_bullets += len(edu.bullets)
	for pub in data.publications:
		total_bullets += len(pub.bullets)

	entry_count = (
		len(data.experience)
		+ len(data.projects)
		+ len(data.education)
		+ len(data.publications)
	)

	# Heuristic: estimate line usage
	# - Each entry heading: ~2 lines
	# - Each bullet: ~1-2 lines
	# - Skills section: ~3-5 lines
	# - Contact/header: ~3 lines
	# One page ≈ 50-55 lines of content

	estimated_lines = (
		3  # Header
		+ entry_count * 2  # Entry headings
		+ total_bullets * 1.5  # Bullets (some wrap)
		+ (4 if data.skills else 0)  # Skills section
	)

	target_lines = 52  # Single page target
	fullness = min(1.0, estimated_lines / target_lines)

	return PageAnalysis(
		page_count=1 if fullness <= 1.0 else 2,
		estimated_fullness=round(fullness, 2),
		overflow=fullness > 1.0,
		underflow=fullness < 0.7,
	)


def score_resume(
	data: ResumeData,
	keywords: list[str] | None = None,
) -> ResumeScore:
	"""Generate a comprehensive quality score for a resume.

	Args:
		data: The resume data to score.
		keywords: Optional list of keywords to match (from job description).

	Returns:
		ResumeScore with section scores, ATS report, and suggestions.
	"""
	section_scores: list[SectionScore] = []

	# Score experience section
	guidelines = SECTION_GUIDELINES["experience"]
	exp_bullets: list[str] = []
	for exp in data.experience:
		exp_bullets.extend(exp.bullets)
	bullet_range = guidelines.get("bullets_per_role", (3, 5))
	if isinstance(bullet_range, tuple):
		section_scores.append(_score_section("experience", exp_bullets, bullet_range))

	# Score projects section
	guidelines = SECTION_GUIDELINES["projects"]
	proj_bullets: list[str] = []
	for proj in data.projects:
		proj_bullets.extend(proj.bullets)
	bullet_range = guidelines.get("bullets_per_project", (2, 4))
	if isinstance(bullet_range, tuple):
		section_scores.append(_score_section("projects", proj_bullets, bullet_range))

	# Score education section
	edu_bullets: list[str] = []
	for edu in data.education:
		edu_bullets.extend(edu.bullets)
	section_scores.append(_score_section("education", edu_bullets, (0, 5)))

	# ATS check
	ats_report = check_ats(data)

	# Keyword match if provided
	keyword_match = match_keywords(data, keywords) if keywords else None

	# Page analysis
	page_analysis = estimate_page_fullness(data)

	# Calculate overall score
	section_avg = (
		sum(ss.avg_bullet_score for ss in section_scores) / len(section_scores)
		if section_scores
		else 0.0
	)

	# Weight components
	ats_factor = 1.0 if ats_report.is_compatible else 0.9
	page_factor = 1.0 if not page_analysis.overflow else 0.85
	keyword_factor = (
		(keyword_match.match_percentage / 100) * 0.2 + 0.8
		if keyword_match
		else 1.0
	)

	overall = section_avg * ats_factor * page_factor * keyword_factor

	# Collect top suggestions
	top_suggestions: list[str] = []

	if page_analysis.overflow:
		top_suggestions.append("Resume exceeds one page - consider condensing content")
	if page_analysis.underflow:
		top_suggestions.append("Resume appears sparse - consider adding more content")

	if not ats_report.is_compatible:
		top_suggestions.extend(ats_report.issues[:2])

	for ss in sorted(section_scores, key=lambda s: s.avg_bullet_score)[:2]:
		top_suggestions.extend(ss.suggestions[:1])

	if keyword_match and keyword_match.match_percentage < 50:
		missing_str = ", ".join(keyword_match.missing[:5])
		top_suggestions.append(f"Add missing keywords: {missing_str}")

	return ResumeScore(
		overall_score=round(overall, 2),
		section_scores=section_scores,
		ats_report=ats_report,
		keyword_match=keyword_match,
		page_analysis=page_analysis,
		top_suggestions=top_suggestions[:5],
	)
