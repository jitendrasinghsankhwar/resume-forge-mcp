# Project Overview

## What is Resume Forge MCP?

An MCP (Model Context Protocol) server for intelligent LaTeX resume management. It lets AI assistants (Kiro, Claude, Cursor) import, edit, tailor, generate, and compile resumes with multiple template styles.

- **PyPI**: https://pypi.org/project/resume-forge-mcp/
- **GitHub**: https://github.com/jitendrasinghsankhwar/resume-forge-mcp
- **Current Version**: v0.4.0

## Source Layout

```
src/resume_forge_mcp/
├── server.py              ← MCP tool definitions (11 tools)
├── models/
│   └── resume.py          ← Pydantic models (ContactInfo, Experience, Education, etc.)
├── storage/
│   ├── tex_import.py      ← LaTeX parser (import from .tex)
│   ├── pdf_import.py      ← PDF parser (import from .pdf) — TODO
│   ├── docx_import.py     ← DOCX parser (import from .docx) — TODO
│   └── resume_store.py    ← JSON data store
├── templates/
│   ├── engine.py          ← Jinja2 template renderer (supports template selection)
│   ├── modern.tex.j2      ← Modern template — color accents, professional
│   ├── classic.tex.j2     ← Classic template — traditional with horizontal rules
│   ├── minimal.tex.j2     ← Minimal template — simple, no-frills
│   └── jake_resume.tex.j2 ← Jake's Resume template (legacy)
├── intelligence/
│   ├── analyzer.py        ← Resume scoring/quality analysis
│   └── tailoring.py       ← JD parsing + content selection
├── compiler/
│   ├── latex.py           ← pdflatex compilation
│   └── preview.py         ← PDF to PNG rendering
└── overleaf.py            ← Overleaf gallery browser + template fetcher
```

## Environment Variables

| Env Var | Default | Purpose |
|---------|---------|---------|
| `RESUME_DATA_DIR` | `~/.resume-forge/data` | Resume data JSON + imported data |
| `RESUME_TEMPLATE_DIR` | `~/.resume-forge/templates` | Fetched Overleaf templates |
| `RESUME_OUTPUT_DIR` | `~/.resume-forge/output` | Generated .tex and final .pdf |

## All 11 Tools

| # | Tool | Category | Description |
|---|------|----------|-------------|
| 1 | `get_config` | Config | Show config, paths, pdflatex status, tool list |
| 2 | `list_templates` | Templates | List built-in templates (modern/classic/minimal) + Overleaf info |
| 3 | `browse_overleaf_templates` | Templates | Browse 350+ Overleaf templates by category |
| 4 | `fetch_overleaf_template` | Templates | Download an Overleaf template source |
| 5 | `import_resume` | Import | Import from .tex, .pdf, or .docx into structured data |
| 6 | `get_resume_data` | Read | Get all imported resume data |
| 7 | `update_resume_data` | Write | Add/update/delete entries in any section |
| 8 | `generate_resume` | Generate | Render data to .tex using selected template |
| 9 | `compile_and_preview` | Compile | Compile .tex to PDF and return preview image |
| 10 | `score_resume_quality` | Analysis | Score bullets, ATS compatibility, keyword matching |
| 11 | `generate_tailored_resume` | Generate | Parse JD + select content + generate tailored resume |

## Known Bugs

1. **Company name truncation on import** — `_extract_subheadings` regex breaks on nested LaTeX braces like `\`{e}mes)`. Workaround: fix via `update_resume_data` after import.
2. **Skills `\item` artifact on import** — Pattern 2 in `_parse_skills` can leak `\item` into last skill. Fixed in v0.4.0 but only for Pattern 2 lookahead.
3. **"About Me" section not imported** — no parser for freeform summary sections.
4. **PDF/DOCX import not implemented** — `import_resume` supports .tex only until `pdf_import.py` and `docx_import.py` are created.

## Git Setup

- **Personal GitHub**: `github.com/jitendrasinghsankhwar/resume-forge-mcp`
- **Auth token**: `$PERSONAL_GIT_TOKEN` (from `~/.bash_profile`)
- **PyPI token**: `$PYPI_TOKEN` (from `~/.bash_profile`)
- **Always** `source ~/.bash_profile` before git push or PyPI publish
- **Never** use company git (`jsankhwar@mdsol.com`) for this repo
