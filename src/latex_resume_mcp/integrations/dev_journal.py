"""Integration with dev-journal-mcp for work history queries."""

from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class WorkSession:
	"""A summarized work session from dev-journal."""

	session_id: str
	project: str
	started_at: datetime
	ended_at: datetime
	duration_hours: float
	goal: str
	outcome: str
	tools_used: list[str]
	files_touched: list[str]


@dataclass
class ProjectSummary:
	"""Aggregated summary of work on a project."""

	project: str
	total_sessions: int
	total_hours: float
	date_range: tuple[str, str]  # (earliest, latest)
	top_tools: list[tuple[str, int]]  # (tool_name, count)
	key_accomplishments: list[str]  # Extracted from outcomes


@dataclass
class WorkHistoryReport:
	"""Complete work history report for resume generation."""

	total_sessions: int
	total_hours: float
	date_range: tuple[str, str]
	projects: list[ProjectSummary]
	all_tools: list[tuple[str, int]]  # Aggregated tool usage


def _get_journal_db_path() -> Path:
	"""Get path to dev-journal SQLite database."""
	default = Path.home() / ".local" / "share" / "dev-journal" / "journal.db"
	return Path(os.environ.get("DEV_JOURNAL_DB_PATH", default))


def _parse_json_field(value: str) -> list[str]:
	"""Parse a JSON array field from the database."""
	if not value:
		return []
	try:
		parsed = json.loads(value)
		if isinstance(parsed, list):
			# Handle list of dicts (tools_used format) or list of strings
			result = []
			for item in parsed:
				if isinstance(item, dict) and "name" in item:
					result.append(item["name"])
				elif isinstance(item, str):
					result.append(item)
			return result
		return []
	except json.JSONDecodeError:
		return []


def _extract_accomplishment(outcome: str) -> str | None:
	"""Extract a concise accomplishment from session outcome.

	Looks for concrete results, not status updates.
	"""
	if not outcome or len(outcome) < 20:
		return None

	# Skip non-accomplishment outcomes
	skip_phrases = [
		"session with no",
		"hit your limit",
		"invalid api key",
		"error",
		"failed",
		"couldn't",
	]
	outcome_lower = outcome.lower()
	if any(phrase in outcome_lower for phrase in skip_phrases):
		return None

	# Take first sentence/line that looks like an accomplishment
	lines = outcome.split("\n")
	for line in lines[:3]:
		line = line.strip()
		if len(line) > 30 and not line.startswith(("-", "*", "#", "```")):
			# Truncate to reasonable length
			if len(line) > 150:
				line = line[:147] + "..."
			return line

	return None


def query_work_history(
	project: str | None = None,
	date_from: str | None = None,
	date_to: str | None = None,
	tools_filter: list[str] | None = None,
	limit: int = 100,
) -> list[WorkSession]:
	"""Query work sessions from dev-journal.

	Args:
		project: Filter to specific project name.
		date_from: Start date (YYYY-MM-DD).
		date_to: End date (YYYY-MM-DD).
		tools_filter: Only include sessions using these tools.
		limit: Maximum sessions to return.

	Returns:
		List of WorkSession objects.
	"""
	db_path = _get_journal_db_path()
	if not db_path.exists():
		return []

	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row

	query = """
		SELECT session_id, project, started_at, ended_at, duration_seconds,
		       goal, outcome, tools_used, files_touched
		FROM sessions
		WHERE 1=1
	"""
	params: list[str | int] = []

	if project:
		query += " AND project = ?"
		params.append(project)

	if date_from:
		query += " AND date(started_at) >= ?"
		params.append(date_from)

	if date_to:
		query += " AND date(started_at) <= ?"
		params.append(date_to)

	# Filter for meaningful sessions
	query += " AND length(outcome) > 30"
	query += " ORDER BY started_at DESC LIMIT ?"
	params.append(limit)

	cursor = conn.execute(query, params)
	rows = cursor.fetchall()
	conn.close()

	sessions = []
	for row in rows:
		tools = _parse_json_field(row["tools_used"])

		# Apply tools filter if specified
		if tools_filter and not any(t in tools for t in tools_filter):
			continue

		sessions.append(
			WorkSession(
				session_id=row["session_id"],
				project=row["project"],
				started_at=datetime.fromisoformat(row["started_at"]),
				ended_at=datetime.fromisoformat(row["ended_at"]),
				duration_hours=row["duration_seconds"] / 3600,
				goal=row["goal"][:500] if row["goal"] else "",
				outcome=row["outcome"][:500] if row["outcome"] else "",
				tools_used=tools,
				files_touched=_parse_json_field(row["files_touched"]),
			)
		)

	return sessions


def get_project_summary(project: str) -> ProjectSummary | None:
	"""Get aggregated summary for a specific project.

	Args:
		project: Project name to summarize.

	Returns:
		ProjectSummary or None if no sessions found.
	"""
	sessions = query_work_history(project=project, limit=500)
	if not sessions:
		return None

	total_hours = sum(s.duration_hours for s in sessions)
	dates = [s.started_at.date().isoformat() for s in sessions]

	# Aggregate tool usage
	tool_counts: Counter[str] = Counter()
	for s in sessions:
		tool_counts.update(s.tools_used)

	# Extract accomplishments from outcomes
	accomplishments = []
	for s in sessions:
		acc = _extract_accomplishment(s.outcome)
		if acc and acc not in accomplishments:
			accomplishments.append(acc)
			if len(accomplishments) >= 10:
				break

	return ProjectSummary(
		project=project,
		total_sessions=len(sessions),
		total_hours=round(total_hours, 1),
		date_range=(min(dates), max(dates)),
		top_tools=tool_counts.most_common(10),
		key_accomplishments=accomplishments,
	)


def get_work_history_report(
	date_from: str | None = None,
	date_to: str | None = None,
) -> WorkHistoryReport:
	"""Generate comprehensive work history report.

	Args:
		date_from: Start date filter (YYYY-MM-DD).
		date_to: End date filter (YYYY-MM-DD).

	Returns:
		WorkHistoryReport with project summaries and aggregated stats.
	"""
	db_path = _get_journal_db_path()
	if not db_path.exists():
		return WorkHistoryReport(
			total_sessions=0,
			total_hours=0,
			date_range=("", ""),
			projects=[],
			all_tools=[],
		)

	conn = sqlite3.connect(db_path)

	# Get distinct projects
	query = "SELECT DISTINCT project FROM sessions WHERE length(outcome) > 30"
	params: list[str] = []

	if date_from:
		query += " AND date(started_at) >= ?"
		params.append(date_from)
	if date_to:
		query += " AND date(started_at) <= ?"
		params.append(date_to)

	cursor = conn.execute(query, params)
	projects = [row[0] for row in cursor.fetchall()]
	conn.close()

	# Get summaries for each project
	project_summaries = []
	total_hours = 0.0
	total_sessions = 0
	all_tool_counts: Counter[str] = Counter()
	all_dates: list[str] = []

	for proj in projects:
		summary = get_project_summary(proj)
		if summary and summary.total_sessions > 0:
			project_summaries.append(summary)
			total_hours += summary.total_hours
			total_sessions += summary.total_sessions
			all_dates.extend(summary.date_range)
			for tool, count in summary.top_tools:
				all_tool_counts[tool] += count

	# Sort projects by total hours
	project_summaries.sort(key=lambda p: p.total_hours, reverse=True)

	return WorkHistoryReport(
		total_sessions=total_sessions,
		total_hours=round(total_hours, 1),
		date_range=(min(all_dates) if all_dates else "", max(all_dates) if all_dates else ""),
		projects=project_summaries,
		all_tools=all_tool_counts.most_common(20),
	)


def search_accomplishments(
	keywords: list[str],
	limit: int = 20,
) -> list[tuple[str, str, str]]:
	"""Search for accomplishments matching keywords.

	Useful for finding relevant work when tailoring to a job description.

	Args:
		keywords: Keywords to search for in goals/outcomes.
		limit: Maximum results.

	Returns:
		List of (project, date, accomplishment) tuples.
	"""
	db_path = _get_journal_db_path()
	if not db_path.exists():
		return []

	conn = sqlite3.connect(db_path)

	# Build search query
	conditions = []
	params: list[str] = []
	for kw in keywords:
		conditions.append("(goal LIKE ? OR outcome LIKE ? OR tools_used LIKE ?)")
		pattern = f"%{kw}%"
		params.extend([pattern, pattern, pattern])

	if not conditions:
		conn.close()
		return []

	query = f"""
		SELECT project, date(started_at) as date, outcome
		FROM sessions
		WHERE ({" OR ".join(conditions)})
		AND length(outcome) > 50
		ORDER BY started_at DESC
		LIMIT ?
	"""
	params.append(str(limit))

	cursor = conn.execute(query, params)
	rows = cursor.fetchall()
	conn.close()

	results = []
	for row in rows:
		accomplishment = _extract_accomplishment(row[2])
		if accomplishment:
			results.append((row[0], row[1], accomplishment))

	return results
