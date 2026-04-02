# Resume Forge MCP — Development Guide

> This document is written for AI agents and human contributors. It contains everything needed to understand, modify, and extend this project.

## What This Project Is

**resume-forge-mcp** is an MCP (Model Context Protocol) server that provides end-to-end LaTeX resume generation. It is an enhanced fork of [dannywillowliu-uchi/resume_mcp](https://github.com/dannywillowliu-uchi/resume_mcp) (MIT License).

**PyPI**: https://pypi.org/project/resume-forge-mcp/
**GitHub**: https://github.com/jitendrasinghsankhwar/resume-forge-mcp
**Original**: https://github.com/dannywillowliu-uchi/resume_mcp

### What It Does (Current Capabilities)

| Capability | Status | Module |
|-----------|--------|--------|
| Browse Overleaf template gallery (350+ CV templates, 36 pages) | ✅ Done | `overleaf.py` |
| Fetch LaTeX source from any Overleaf template URL | ✅ Done | `overleaf.py` |
| Save fetched templates locally | ✅ Done | `overleaf.py` |
| Store resume data as structured JSON (Pydantic models) | ✅ Done | `models/resume.py` |
| Import existing .tex files into JSON data model | ✅ Done | `storage/tex_import.py` |
| Render resume from JSON data using Jinja2 templates | ✅ Done | `templates/engine.py` |
| Compile .tex → PDF with pdflatex/xelatex/lualatex auto-detection | ✅ Done | `compiler/latex.py` |
| Preview compiled PDF as PNG image | ✅ Done | `compiler/preview.py` |
| Score resume quality (ATS compatibility, bullet analysis) | ✅ Done | `intelligence/analyzer.py` |
| Parse job descriptions and extract keywords | ✅ Done | `intelligence/tailoring.py` |
| Auto-tailor resume to job description | ✅ Done | `intelligence/tailoring.py` |
| Manage multiple resume variants | ✅ Done | `storage/resume_store.py` |
| Compile + preview in one step | ✅ Done | `server.py` |

### What's Planned (Not Yet Built)

| Feature | Priority | Details |
|---------|----------|---------|
| Bundle 15+ popular templates (Jake's, AltaCV, Awesome-CV, Deedy, etc.) | HIGH | Download from GitHub repos, convert to Jinja2 `.j2` templates with placeholder markers |
| Template-aware formatters | HIGH | Each template needs a `formatter.py` that maps generic content → template-specific LaTeX macros |
| Cover letter generation | MEDIUM | Similar to resume but with letter-specific templates |
| `open_pdf()` tool | LOW | Open compiled PDF in system viewer |
| Docker TeX Live fallback | LOW | Compile without local LaTeX install |

---

## Architecture

```
resume-forge-mcp/
├── src/resume_forge_mcp/          # Main Python package
│   ├── __init__.py                # Exports main() and mcp
│   ├── __main__.py                # Entry point: python -m resume_forge_mcp
│   ├── server.py                  # MCP server — ALL tools registered here (FastMCP)
│   ├── overleaf.py                # NEW: Overleaf gallery browser + template fetcher
│   ├── compiler/
│   │   ├── latex.py               # ENHANCED: Multi-engine compiler (pdflatex/xelatex/lualatex)
│   │   └── preview.py             # PDF → PNG renderer using PyMuPDF
│   ├── models/
│   │   ├── resume.py              # Pydantic models: ResumeData, Experience, Education, etc.
│   │   └── analysis.py            # Pydantic models: ResumeScore, BulletScore, etc.
│   ├── templates/
│   │   ├── engine.py              # Jinja2 template renderer with LaTeX-safe delimiters
│   │   ├── jake_resume.tex.j2     # Jake's Resume template (Jinja2)
│   │   └── overleaf/              # Fetched Overleaf templates stored here
│   ├── intelligence/
│   │   ├── analyzer.py            # Resume quality scoring
│   │   ├── tailoring.py           # JD parsing + content selection + variant generation
│   │   └── knowledge.py           # Action verbs, skill taxonomies, keyword lists
│   ├── storage/
│   │   ├── resume_store.py        # JSON file storage for resume data + variants
│   │   └── tex_import.py          # Parse .tex files into Pydantic models
│   └── integrations/
│       └── dev_journal.py         # Optional: dev-journal MCP integration
├── tests/
│   ├── unit/                      # Unit tests for each module
│   └── integration/               # Integration tests for MCP tools
├── pyproject.toml                 # Package config, dependencies, entry points
├── CLAUDE.md                      # AI assistant instructions (original)
├── CONTRIBUTING.md                # Development guide (this file)
└── README.md                      # User-facing documentation
```

---

## Key Design Decisions

### 1. Jinja2 with Custom Delimiters
LaTeX uses `{}` and `%` which conflict with Jinja2 defaults. The engine uses:
- `<< >>` for variables (instead of `{{ }}`)
- `<% %>` for blocks (instead of `{% %}`)
- `<# #>` for comments (instead of `{# #}`)

See `templates/engine.py` → `create_jinja_env()`.

### 2. LaTeX Escaping
User text must be escaped before rendering. The `escape_latex()` function in `engine.py` handles `& % $ # _ ~ ^` while preserving intentional LaTeX commands like `\textbf{}`, `\href{}`, and math mode `$...$`.

### 3. Multi-Engine Compiler
`compiler/latex.py` auto-detects which engine a template needs:
- `\usepackage{fontspec}` or `\setmainfont` → **xelatex**
- `\usepackage{luacode}` or `\directlua` → **lualatex**
- Everything else → **pdflatex** (default)

If the detected engine fails, it falls back to the others. Search paths for MacTeX, TeX Live, and system installs are hardcoded in `SEARCH_PATHS`.

### 4. Overleaf Integration
`overleaf.py` scrapes Overleaf's public gallery HTML. No API exists.
- Gallery listing: `https://www.overleaf.com/latex/templates/tagged/{tag}/page/{n}`
- Template source is embedded in the HTML of individual template pages
- Source extraction uses regex: `\\documentclass.*?\\end{document}`
- HTML entities and double backslashes are unescaped after extraction

### 5. Data Model
Resume data is stored as JSON using Pydantic models (`models/resume.py`):
- `ResumeData`: top-level container
- `Contact`: name, email, phone, linkedin, github, website
- `Experience`: company, title, location, date, bullets, tags
- `Education`: institution, degree, location, date, bullets
- `Project`: name, technologies, date, bullets, tags
- `Publication`: title, date, link, link_text, bullets
- `SkillCategory`: category name + list of skills
- `ResumeVariant`: named selection of indices into the master data pool

Tags on Experience/Project enable intelligent content selection when tailoring to job descriptions.

### 6. MCP Server
Uses `FastMCP` from the `mcp` package. All tools are registered in `server.py` using `@mcp.tool()` decorators. The server communicates via stdio (JSON-RPC).

---

## How to Set Up for Development

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- LaTeX distribution (MacTeX, TeX Live, or MiKTeX) for compilation

### Setup
```bash
git clone https://github.com/jitendrasinghsankhwar/resume-forge-mcp.git
cd resume-forge-mcp
uv venv
uv pip install -e ".[dev]"  # or: uv pip install -e "."
```

### Run Tests
```bash
uv run pytest tests/unit/
uv run pytest tests/integration/
```

### Run the MCP Server Locally
```bash
# Direct
.venv/bin/python -m resume_forge_mcp

# Or via installed tool
uv tool install -e .
resume-forge-mcp
```

### Test MCP Protocol Manually
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | resume-forge-mcp
```

---

## How to Add a New Template

### Step 1: Get the Template Source
Either from GitHub or Overleaf:
```python
from resume_forge_mcp.overleaf import fetch_template_source
result = fetch_template_source("https://www.overleaf.com/latex/templates/some-template/abcdefghijkl")
print(result["source"])
```

### Step 2: Convert to Jinja2 Template
1. Copy the `.tex` source to `src/resume_forge_mcp/templates/`
2. Rename to `{name}.tex.j2`
3. Replace hardcoded content with Jinja2 variables using custom delimiters:

**Before** (raw LaTeX):
```latex
\textbf{\Huge John Doe} \\
\href{mailto:john@example.com}{john@example.com}
```

**After** (Jinja2):
```latex
\textbf{\Huge << contact.name >>} \\
<% if contact.email %>\href{mailto:<< contact.email >>}{<< contact.email >>}<% endif %>
```

4. Use `|latex` filter for user-provided text:
```latex
\resumeSubheading{<< exp.company|latex >>}{<< exp.location|latex >>}
```

### Step 3: Register the Template
Update `templates/engine.py` to support template selection (currently hardcoded to `jake_resume.tex.j2`). The `TEMPLATE_NAME` constant needs to become configurable.

### Step 4: Test Compilation
```python
from resume_forge_mcp.compiler.latex import compile_latex
from pathlib import Path

source = Path("src/resume_forge_mcp/templates/new_template.tex.j2").read_text()
result = compile_latex(source, Path("output"), "test")
print(f"Success: {result.success}, Engine: {result.engine_used}")
```

---

## How to Add a New MCP Tool

### Step 1: Add the Tool Function in `server.py`

```python
@mcp.tool()
def my_new_tool(param1: str, param2: int = 10) -> str:
    """Description shown to the AI agent.

    Args:
        param1: What this parameter does.
        param2: Optional parameter with default.

    Returns:
        JSON string with results.
    """
    try:
        # Your logic here
        result = {"success": True, "data": "..."}
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed: {str(e)}"})
```

### Step 2: Add to `get_config()` Tool List
Find the `tools_available` list in the `get_config()` function and add your tool name.

### Step 3: Write Tests
Add tests in `tests/unit/` or `tests/integration/test_tools.py`.

---

## How to Publish a New Version

### Step 1: Bump Version
Edit `pyproject.toml`:
```toml
version = "0.3.1"  # was 0.3.0
```

### Step 2: Build and Publish
```bash
cd ~/resume-forge-mcp
uv build
uv publish --token "$PYPI_TOKEN"
```

### Step 3: Push to GitHub
Commit the version bump and push to `main`.

### Step 4: Update Local Install
```bash
uv tool install --force resume-forge-mcp
```

---

## MCP Tools Reference (Current: 17 Tools)

### Data Management (6)
| Tool | Description |
|------|-------------|
| `import_from_latex_file(tex_path)` | Parse .tex file into JSON data model |
| `get_resume_data()` | Get master resume data pool |
| `update_resume_data(section, action, index, data)` | Add/edit/delete entries |
| `list_variants()` | List all saved resume variants |
| `get_variant(name)` | Get specific variant config |
| `save_variant(variant_json)` | Create/update variant |

### Generation & Compilation (4)
| Tool | Description |
|------|-------------|
| `generate_resume(variant_name, output_filename)` | Render .tex from data |
| `compile_resume_tex(tex_path)` | Compile .tex → PDF |
| `compile_and_preview(variant_name, output_filename, dpi)` | Generate + compile + PNG preview |
| `preview_resume(pdf_path, dpi)` | Preview existing PDF as image |

### Intelligence (3)
| Tool | Description |
|------|-------------|
| `score_resume_quality(keywords)` | ATS scoring + bullet analysis |
| `parse_job_description_text(jd_text)` | Extract skills/keywords from JD |
| `generate_tailored_resume(jd_text, ...)` | Full auto: parse JD → select content → compile → preview |

### Overleaf (2) — NEW
| Tool | Description |
|------|-------------|
| `browse_overleaf_templates(tag, page)` | Browse Overleaf gallery (cv, cover-letter, etc.) |
| `fetch_overleaf_template(template_url, save_as)` | Download template source from Overleaf URL |

### Utility (2)
| Tool | Description |
|------|-------------|
| `assess_quality(pdf_path)` | Page count, file size, dimension checks |
| `get_config()` | Show config, available tools, pdflatex status |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LATEX_RESUME_DATA_DIR` | `~/.latex-resume-mcp` | Where JSON data and variants are stored |
| `LATEX_RESUME_OUTPUT_DIR` | `~/.latex-resume-mcp/output` | Where .tex and .pdf files are generated |

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `mcp` | >=1.0.0 | MCP server framework (FastMCP) |
| `pydantic` | >=2.0.0 | Data models and validation |
| `jinja2` | >=3.1.0 | Template rendering |
| `pymupdf` | >=1.24.0 | PDF → PNG preview rendering |

---

## Known Limitations

1. **Overleaf scraping is fragile** — if Overleaf changes their HTML structure, `overleaf.py` regex patterns will break
2. **Only Jake's Resume template** has a Jinja2 `.j2` version — other templates can only be fetched as raw `.tex` (not data-driven)
3. **Some Overleaf templates need custom `.cls` files** — the fetcher only extracts the main `.tex`, not supporting class files
4. **Template engine is hardcoded** to `jake_resume.tex.j2` — needs refactoring to support template selection
5. **No cover letter support** yet

---

## Contributing Workflow

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make changes
4. Run tests: `uv run pytest`
5. Bump version in `pyproject.toml` if publishing
6. Submit PR to `main`

---

## License

MIT License — see LICENSE file. Original work by Danny Liu. Enhanced by Jitendra Singh Sankhwar.

---

*Last updated: 2026-04-01*
*Package version: 0.3.0*
