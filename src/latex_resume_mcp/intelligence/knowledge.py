"""Resume intelligence constants: action verbs, rubrics, ATS rules, and guidelines."""

from __future__ import annotations

# Strong action verbs categorized by type
ACTION_VERBS: dict[str, list[str]] = {
	"technical": [
		"Architected", "Automated", "Built", "Configured", "Debugged",
		"Deployed", "Designed", "Developed", "Engineered", "Implemented",
		"Integrated", "Migrated", "Optimized", "Programmed", "Refactored",
		"Scaled", "Shipped", "Streamlined", "Upgraded",
	],
	"leadership": [
		"Championed", "Coached", "Coordinated", "Directed", "Drove",
		"Established", "Founded", "Guided", "Led", "Managed", "Mentored",
		"Orchestrated", "Oversaw", "Spearheaded", "Supervised",
	],
	"analytical": [
		"Analyzed", "Assessed", "Audited", "Benchmarked", "Calculated",
		"Diagnosed", "Evaluated", "Identified", "Investigated", "Measured",
		"Modeled", "Profiled", "Quantified", "Researched", "Tested",
	],
	"impact": [
		"Accelerated", "Achieved", "Boosted", "Cut", "Decreased", "Delivered",
		"Doubled", "Eliminated", "Enhanced", "Exceeded", "Expanded",
		"Generated", "Improved", "Increased", "Maximized", "Minimized",
		"Outperformed", "Produced", "Raised", "Reduced", "Saved", "Tripled",
	],
	"communication": [
		"Authored", "Collaborated", "Communicated", "Documented", "Drafted",
		"Facilitated", "Negotiated", "Partnered", "Presented", "Published",
		"Reported", "Trained", "Translated", "Wrote",
	],
}

# Flattened set of all action verbs for quick lookup
ALL_ACTION_VERBS: set[str] = set()
for category_verbs in ACTION_VERBS.values():
	ALL_ACTION_VERBS.update(v.lower() for v in category_verbs)

# Bullet point quality rubric - XYZ Impact Framework
# X = What you did (action verb + task)
# Y = How you did it (method, tool, technology)
# Z = The impact (quantified result, business outcome)
BULLET_RUBRIC: dict[str, str | list[str]] = {
	"structure": "Action Verb + Task + Method/Tool + Quantified Impact (XYZ format)",
	"xyz_format": "[Did X] using/with [Y method/tool], achieving/resulting in [Z impact]",
	"example_good": (
		"Optimized PostgreSQL queries using index tuning and query caching, "
		"reducing API latency by 40% for 10K daily active users"
	),
	"example_weak": "Worked on database optimization",
	"examples_xyz": [
		"Built inference pipeline using PyTorch and CUDA, achieving 14x throughput at batch 16",
		"Designed RAG workflow with AWS Bedrock, automating KPI extraction and saving 10 hrs/week",
		"Profiled GPU bottlenecks using NSight on H100s, identifying 3x speedup for SGLang",
	],
	"method_indicators": [
		"using", "with", "via", "leveraging", "utilizing", "through", "in [tool]"
	],
	"impact_indicators": [
		"achieving", "resulting in", "reducing", "improving", "increasing",
		"saving", "enabling", "delivering", "driving"
	],
	"min_length": "15 characters",
	"max_length": "150 characters",
	"ideal_length": "90-120 characters (fills line without orphan)",
	"avoid_orphans": "Adjust length to fill lines; avoid orphaned words on new line",
}

# ATS (Applicant Tracking System) compatibility rules
ATS_RULES: dict[str, list[str]] = {
	"do": [
		"Use standard section headings (Education, Experience, Skills)",
		"Include both acronyms and full terms (e.g., 'AWS (Amazon Web Services)')",
		"Use simple bullet points (no nested lists)",
		"Keep formatting minimal and consistent",
		"Use common fonts that embed well (avoid decorative fonts)",
		"Include keywords from the job description verbatim",
	],
	"avoid": [
		"Tables for layout (content may not parse correctly)",
		"Headers and footers (often ignored by parsers)",
		"Images, logos, or graphics (invisible to ATS)",
		"Text boxes or columns (parsing issues)",
		"Custom fonts that don't embed (shows as boxes)",
		"Colors for important information (may not print/parse)",
		"Special characters or symbols (inconsistent support)",
	],
	"formatting": [
		"Single column layout preferred",
		"Clear section breaks with horizontal rules",
		"Consistent date formatting (Month Year -- Month Year)",
		"Standard file format (.pdf or .docx)",
		"One page for early career, two pages max for senior roles",
	],
}

# Section guidelines for resume quality
SECTION_GUIDELINES: dict[str, dict[str, object]] = {
	"experience": {
		"bullets_per_role": (3, 5),
		"recent_roles_more_detail": True,
		"order": "reverse_chronological",
		"include_metrics": True,
		"date_format": "Month Year -- Month Year",
	},
	"education": {
		"bullets_per_entry": (0, 3),
		"include_gpa_if": "above 3.5 or relevant to role",
		"include_coursework_if": "recent graduate or relevant to role",
		"order": "reverse_chronological",
	},
	"skills": {
		"categories": (3, 5),
		"skills_per_category": (4, 8),
		"total_skills": (8, 15),
		"organize_by": "category (Languages, Frameworks, Tools)",
		"relevance": "prioritize skills mentioned in job description",
	},
	"projects": {
		"bullets_per_project": (2, 4),
		"include_technologies": True,
		"include_links_if": "public and professional",
		"order": "by_relevance_or_recency",
	},
	"publications": {
		"bullets_per_entry": (1, 2),
		"include_links": True,
		"format": "title, venue/link, date",
	},
	"page_layout": {
		"target_pages": 1,
		"max_pages": 2,
		"margins": "0.5-0.75 inches",
		"font_size": "10-12pt body, 14-16pt name",
		"target_fullness": (0.85, 0.95),
	},
}

# Metric patterns for detecting quantified results
METRIC_PATTERNS: list[str] = [
	r"\d+%",  # percentages
	r"\$[\d,]+[KMB]?",  # dollar amounts
	r"\d+[xX]",  # multipliers
	r"\d+\+",  # counts with plus
	r"\d+K\+?",  # thousands
	r"\d+M\+?",  # millions
	r"\d+-\d+",  # ranges
	r"\d+\s*(users|customers|clients|members|projects|orders|requests)",  # counts
	r"\d+\s*(hrs?|hours?|min(utes?)?|days?|weeks?)",  # time savings
	r"\d+\s*(LOC|lines)",  # code metrics
]

# Common tech keywords for matching
TECH_KEYWORDS: dict[str, list[str]] = {
	"languages": [
		"Python", "JavaScript", "TypeScript", "Java", "C", "C++", "Go", "Rust",
		"Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "SQL", "Bash", "Shell",
	],
	"frameworks": [
		"React", "Angular", "Vue", "Next.js", "Django", "Flask", "FastAPI",
		"Express", "Spring", "Rails", "Node.js", "PyTorch", "TensorFlow",
		"scikit-learn", "Pandas", "NumPy",
	],
	"databases": [
		"PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
		"DynamoDB", "SQLite", "Cassandra", "Neo4j", "Firebase",
	],
	"cloud": [
		"AWS", "GCP", "Azure", "Kubernetes", "Docker", "Terraform",
		"Lambda", "S3", "EC2", "CloudFormation", "Heroku", "Vercel",
	],
	"tools": [
		"Git", "GitHub", "GitLab", "Jenkins", "CircleCI", "GitHub Actions",
		"Jira", "Confluence", "Slack", "Linux", "Unix", "CI/CD",
	],
	"concepts": [
		"REST", "GraphQL", "Microservices", "API", "Agile", "Scrum",
		"TDD", "DevOps", "MLOps", "Machine Learning", "Deep Learning",
		"Distributed Systems", "Concurrency", "Parallelism",
	],
}
