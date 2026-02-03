"""Tests for intelligence/analyzer.py."""

from __future__ import annotations

from latex_resume_mcp.intelligence.analyzer import (
	check_ats,
	estimate_page_fullness,
	match_keywords,
	score_bullet,
	score_resume,
)
from latex_resume_mcp.models.resume import (
	ContactInfo,
	Experience,
	ResumeData,
	SkillCategory,
)


class TestScoreBullet:
	"""Tests for score_bullet function."""

	def test_perfect_bullet(self) -> None:
		"""Bullet with verb, metric, and tech scores high."""
		bullet = "Optimized PostgreSQL queries reducing API latency by 40%"
		score = score_bullet(bullet)

		assert score.has_action_verb is True
		assert score.has_metric is True
		assert score.appropriate_length is True
		assert score.score >= 0.7

	def test_weak_bullet_no_verb(self) -> None:
		"""Bullet without action verb scores lower."""
		bullet = "Worked on improving database performance"
		score = score_bullet(bullet)

		assert score.has_action_verb is False
		assert "action verb" in score.suggestions[0].lower()

	def test_weak_bullet_no_metric(self) -> None:
		"""Bullet without metric gets suggestion."""
		bullet = "Developed REST API endpoints"
		score = score_bullet(bullet)

		assert score.has_metric is False
		assert any("quantifiable" in s.lower() for s in score.suggestions)

	def test_bullet_with_percentage(self) -> None:
		"""Percentage is detected as metric."""
		bullet = "Reduced load time by 50%"
		score = score_bullet(bullet)

		assert score.has_metric is True

	def test_bullet_with_dollar(self) -> None:
		"""Dollar amount is detected as metric."""
		bullet = "Generated $1M in new revenue"
		score = score_bullet(bullet)

		assert score.has_metric is True

	def test_bullet_with_multiplier(self) -> None:
		"""Multiplier (2x, 10x) is detected as metric."""
		bullet = "Improved throughput 10x"
		score = score_bullet(bullet)

		assert score.has_metric is True

	def test_too_short_bullet(self) -> None:
		"""Very short bullet gets flagged."""
		bullet = "Fixed bugs"
		score = score_bullet(bullet)

		assert score.appropriate_length is False
		assert any("too short" in s.lower() for s in score.suggestions)

	def test_too_long_bullet(self) -> None:
		"""Very long bullet gets flagged."""
		bullet = "x" * 200
		score = score_bullet(bullet)

		assert score.appropriate_length is False
		assert any("too long" in s.lower() for s in score.suggestions)

	def test_empty_bullet(self) -> None:
		"""Empty bullet doesn't crash."""
		score = score_bullet("")

		assert score.score == 0.0
		assert score.appropriate_length is False

	def test_technical_detail_acronym(self) -> None:
		"""Acronyms are detected as technical detail."""
		bullet = "Deployed services on AWS EC2 instances"
		score = score_bullet(bullet)

		assert score.has_technical_detail is True


class TestCheckATS:
	"""Tests for check_ats function."""

	def test_complete_resume_is_compatible(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Resume with all sections passes ATS check."""
		report = check_ats(sample_resume_data)

		assert report.is_compatible is True
		assert len(report.issues) == 0

	def test_missing_skills_fails(self, sample_contact: ContactInfo) -> None:
		"""Resume without skills section fails ATS."""
		data = ResumeData(
			contact=sample_contact,
			skills=[],  # Empty skills
			experience=[],
			projects=[],
			education=[],
		)

		report = check_ats(data)

		assert report.is_compatible is False
		assert any("skills" in issue.lower() for issue in report.issues)

	def test_missing_email_fails(self) -> None:
		"""Resume without email fails ATS."""
		contact = ContactInfo(name="Test User", email="")  # No email
		data = ResumeData(
			contact=contact,
			skills=[SkillCategory(category="Languages", skills=["Python"])],
		)

		report = check_ats(data)

		assert report.is_compatible is False
		assert any("email" in issue.lower() for issue in report.issues)

	def test_acronym_warning(self) -> None:
		"""Acronym without expansion generates warning."""
		contact = ContactInfo(name="Test", email="test@test.com")
		data = ResumeData(
			contact=contact,
			skills=[SkillCategory(category="Cloud", skills=["AWS"])],
			experience=[
				Experience(
					company="Test",
					title="Engineer",
					bullets=["Deployed on AWS using Lambda"],
				)
			],
		)

		report = check_ats(data)

		assert any("Amazon Web Services" in w for w in report.warnings)


class TestMatchKeywords:
	"""Tests for match_keywords function."""

	def test_matches_skills(self, sample_resume_data: ResumeData) -> None:
		"""Keywords in skills are matched."""
		keywords = ["Python", "Git"]
		result = match_keywords(sample_resume_data, keywords)

		assert "Python" in result.matched
		assert result.match_percentage > 0

	def test_missing_keywords(self, sample_resume_data: ResumeData) -> None:
		"""Missing keywords are reported."""
		keywords = ["Haskell", "Erlang"]
		result = match_keywords(sample_resume_data, keywords)

		assert "Haskell" in result.missing
		assert "Erlang" in result.missing
		assert result.match_percentage == 0.0

	def test_empty_keywords(self, sample_resume_data: ResumeData) -> None:
		"""Empty keyword list returns 0%."""
		result = match_keywords(sample_resume_data, [])

		assert result.match_percentage == 0.0
		assert len(result.matched) == 0

	def test_case_insensitive_match(self, sample_resume_data: ResumeData) -> None:
		"""Keyword matching is case-insensitive."""
		keywords = ["python", "FLASK"]
		result = match_keywords(sample_resume_data, keywords)

		# Should match even with different case
		assert len(result.matched) >= 1


class TestEstimatePageFullness:
	"""Tests for estimate_page_fullness function."""

	def test_normal_resume_under_one_page(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Normal resume estimates under one page."""
		analysis = estimate_page_fullness(sample_resume_data)

		assert analysis.page_count == 1
		assert 0 < analysis.estimated_fullness <= 1.0
		assert analysis.overflow is False

	def test_sparse_resume_underflow(self, sample_contact: ContactInfo) -> None:
		"""Sparse resume shows underflow."""
		data = ResumeData(
			contact=sample_contact,
			skills=[SkillCategory(category="Languages", skills=["Python"])],
		)

		analysis = estimate_page_fullness(data)

		assert analysis.underflow is True


class TestScoreResume:
	"""Tests for score_resume function."""

	def test_overall_score_range(self, sample_resume_data: ResumeData) -> None:
		"""Overall score is between 0 and 1."""
		score = score_resume(sample_resume_data)

		assert 0.0 <= score.overall_score <= 1.0

	def test_has_section_scores(self, sample_resume_data: ResumeData) -> None:
		"""Score includes section breakdowns."""
		score = score_resume(sample_resume_data)

		assert len(score.section_scores) > 0
		sections = [ss.section for ss in score.section_scores]
		assert "experience" in sections

	def test_has_ats_report(self, sample_resume_data: ResumeData) -> None:
		"""Score includes ATS report."""
		score = score_resume(sample_resume_data)

		assert score.ats_report is not None

	def test_has_page_analysis(self, sample_resume_data: ResumeData) -> None:
		"""Score includes page analysis."""
		score = score_resume(sample_resume_data)

		assert score.page_analysis is not None

	def test_keywords_included_in_match(
		self, sample_resume_data: ResumeData
	) -> None:
		"""Keywords are matched when provided."""
		score = score_resume(sample_resume_data, keywords=["Python", "Flask"])

		assert score.keyword_match is not None
		assert len(score.keyword_match.matched) > 0

	def test_suggestions_provided(self, sample_resume_data: ResumeData) -> None:
		"""Top suggestions are provided."""
		score = score_resume(sample_resume_data)

		# May or may not have suggestions depending on quality
		assert isinstance(score.top_suggestions, list)
