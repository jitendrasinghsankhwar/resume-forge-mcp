# latex-resume-mcp

MCP server for intelligent LaTeX resume generation with visual verification and job description tailoring.

## Quick Reference

- **Language**: Python 3.12 (requires >=3.11)
- **Entry point**: `src/latex_resume_mcp/server.py`
- **Package manager**: pip with hatchling build backend
- **Test framework**: pytest with pytest-asyncio (asyncio_mode = auto)

## Verification Commands

Run before every commit:

```bash
pytest -v
ruff check src/ tests/
mypy src/
bandit -r src/
```

## Code Style

- Indentation: tabs
- Quotes: double quotes
- Line length: 100
- Type hints: used throughout, mypy strict mode
- Comments: minimal, only for complex logic

## Architecture

```
src/latex_resume_mcp/
├── server.py                    # FastMCP server + 15 tool registrations
├── models/
│   ├── resume.py                # Pydantic: ResumeData, Experience, Project, etc.
│   └── analysis.py              # Pydantic: BulletScore, ResumeScore, ATSReport
├── templates/
│   ├── engine.py                # Jinja2 renderer (<< >> delimiters)
│   └── jake_resume.tex.j2       # LaTeX template with Jinja2 loops
├── compiler/
│   ├── latex.py                 # pdflatex compilation + log parsing
│   └── preview.py               # PyMuPDF PDF→PNG rendering
├── intelligence/
│   ├── knowledge.py             # Action verbs, bullet rubric, ATS rules
│   ├── analyzer.py              # score_bullet(), score_resume(), check_ats()
│   └── tailoring.py             # JD parsing, content selection/ranking
└── storage/
    └── resume_store.py          # JSON file I/O for ResumeData + variants
```

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Jinja2 with `<< >>` delimiters | LaTeX uses `{}` everywhere; custom delimiters avoid escaping |
| Preamble static in template | Danny's exact format preserved; only body content generated |
| PyMuPDF for PDF→image | Fast, no external deps, returns Image to Claude |
| Pydantic data models | Validation, JSON serialization, matches conventions |
| JSON storage (not SQLite) | Resume data <100KB, human-readable, git-trackable |
| Tags on entries | LLM-friendly content selection by role type |

## MCP Tools (15 total)

**Data Management:**
- `import_from_latex_file` - Parse existing .tex into JSON data model
- `get_resume_data` - Read master resume pool
- `update_resume_data` - Add/edit/remove entries
- `list_variants` / `get_variant` / `save_variant` - Variant CRUD

**Generation & Compilation:**
- `generate_resume` - Render variant to .tex via Jinja2
- `compile_resume_tex` - .tex → .pdf via pdflatex
- `compile_and_preview` - Compile + render PNG (returns Image)
- `preview_resume` - Render existing PDF to PNG

**Intelligence:**
- `score_resume_quality` - Bullet quality, ATS compat, keyword match
- `parse_job_description_text` - Extract skills/requirements from JD
- `generate_tailored_resume` - Auto-select content, compile, return preview

**Utility:**
- `assess_quality` - Programmatic checks (page count, overflow)
- `get_config` - Show configuration and tool availability

## Gotchas

- **FastMCP Image type**: Cannot use `list[Image]` in return type annotations; use `Any`
- **LaTeX escaping**: Use `escape_latex()` helper for user text with special chars
- **Model validation**: Use explicit if/elif chains instead of dynamic model_map for mypy
- **Template delimiters**: `<<` and `>>` in Jinja2, not `{{` and `}}`

## Implementation Status

- [x] Phase 1: Project scaffold + data models
- [x] Phase 2: Template engine (Jinja2 + LaTeX)
- [x] Phase 3: Compilation + PDF preview
- [x] Phase 4: Storage + LaTeX import
- [x] Phase 5: Resume intelligence (scoring, ATS)
- [x] Phase 6: Job tailoring (JD parsing, content selection)
- [x] Phase 7: Server integration (15 tools)
- [x] Phase 8: Polish + documentation

## Decisions Log

- 2025-01: Used `Any` return type for preview tools due to FastMCP Image schema generation issues
- 2025-01: Explicit if/elif for model validation instead of dynamic dict lookup for mypy compatibility
