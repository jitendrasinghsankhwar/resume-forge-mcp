# Resume Forge MCP

An MCP (Model Context Protocol) server for intelligent LaTeX resume generation with multiple template styles, quality scoring, and job description tailoring. Works with any MCP-compatible AI assistant — Claude Desktop, Kiro, Cursor, Windsurf, etc.

## Features

- **3 built-in templates**: Modern (color accents), Classic (traditional), Minimal (no-frills)
- **Overleaf integration**: Browse and fetch 350+ templates dynamically
- **Multi-format import**: Import resume data from `.tex`, `.pdf`, or `.docx` files
- **Quality scoring**: Bullet analysis, ATS compatibility, keyword matching
- **Job tailoring**: Auto-select and rank content based on job descriptions
- **Visual preview**: Compile to PDF and preview as images directly in your AI assistant

## Quick Start

```
1. Import my resume from resume.pdf
2. List available templates
3. Generate my resume using the modern template
4. Score my resume against keywords: Python, AWS, Kubernetes
```

That's it — 4 prompts to go from a PDF to a scored, template-styled resume.

## Installation

```bash
uvx resume-forge-mcp
```

With PDF and DOCX import support:

```bash
uvx --with pymupdf --with python-docx resume-forge-mcp
```

### Prerequisites

For PDF compilation (`compile_and_preview`), you need LaTeX installed:

- **macOS**: `brew install --cask mactex`
- **Ubuntu**: `sudo apt install texlive-latex-base texlive-latex-extra texlive-fonts-extra`
- **Windows**: Install [MiKTeX](https://miktex.org/)

> LaTeX is only needed for compiling to PDF. All other tools (import, generate .tex, score, tailor) work without it.

## Configuration

Add to your AI assistant's MCP config:

### Claude Desktop

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "resume-forge": {
      "command": "uvx",
      "args": ["resume-forge-mcp"]
    }
  }
}
```

### Kiro

Add to `~/.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "resume-forge": {
      "command": "uvx",
      "args": ["resume-forge-mcp"]
    }
  }
}
```

### Custom directories (optional)

```json
{
  "mcpServers": {
    "resume-forge": {
      "command": "uvx",
      "args": ["resume-forge-mcp"],
      "env": {
        "RESUME_DATA_DIR": "/path/to/data",
        "RESUME_TEMPLATE_DIR": "/path/to/templates",
        "RESUME_OUTPUT_DIR": "/path/to/output"
      }
    }
  }
}
```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `RESUME_DATA_DIR` | `~/.resume-forge/data` | Imported resume data (JSON) |
| `RESUME_TEMPLATE_DIR` | `~/.resume-forge/templates` | Fetched Overleaf templates |
| `RESUME_OUTPUT_DIR` | `~/.resume-forge/output` | Generated `.tex` and `.pdf` files |

All env vars are optional — defaults to `~/.resume-forge/` subdirectories on any OS.

## Tools (11)

### Templates — Pick a style or browse Overleaf

| Tool | What it does |
|------|-------------|
| `list_templates` | Shows 3 built-in templates (modern, classic, minimal) and tells you Overleaf is available for 350+ more |
| `browse_overleaf_templates` | Browse Overleaf's gallery by category (cv, cover-letter, etc.) — returns names and URLs |
| `fetch_overleaf_template` | Download a specific Overleaf template by URL, optionally save it locally |

### Data — Get your resume in and edit it

| Tool | What it does |
|------|-------------|
| `import_resume` | Feed it a `.tex`, `.pdf`, or `.docx` file — extracts contact, experience, education, skills, publications into structured JSON |
| `get_resume_data` | View everything that was imported — all sections, all entries, all bullets |
| `update_resume_data` | Fix a company name, add a bullet, delete an old job, update your phone number — works on any section |

### Generate — Create your resume

| Tool | What it does |
|------|-------------|
| `generate_resume` | Takes your data + a template (modern/classic/minimal) → renders a complete `.tex` file |
| `compile_and_preview` | Compiles `.tex` to PDF using pdflatex and returns a preview image you can see in chat |
| `generate_tailored_resume` | Paste a job description → it parses requirements, picks your most relevant experience, generates a tailored resume |

### Analyze — Improve your resume

| Tool | What it does |
|------|-------------|
| `score_resume_quality` | Scores every bullet (action verb? metrics? right length?), checks ATS compatibility, matches keywords you provide |
| `get_config` | Shows your directories, pdflatex status, and all available tools |

## Usage Examples

### Import and generate
```
> Import my resume from /path/to/resume.pdf
> Generate my resume using the classic template
```

### Score and improve
```
> Score my resume quality against keywords: Java, AWS, Kafka, microservices
> Update experience index 0 bullet 2 to add a metric
```

### Tailor for a job
```
> Generate a tailored resume for this job description:
> Senior Backend Engineer - 5+ years Java, AWS, event-driven architecture...
```

### Browse Overleaf templates
```
> Browse Overleaf templates for CVs
> Fetch the template at https://www.overleaf.com/latex/templates/...
```

## How It Works

1. **Import** — Your resume file is parsed into structured JSON (contact, experience, education, skills, publications)
2. **Edit** — Fix any parsing issues or add new content via `update_resume_data`
3. **Template** — Pick a built-in style or fetch one from Overleaf
4. **Generate** — Your data is rendered through a Jinja2 template into a `.tex` file
5. **Compile** — pdflatex compiles the `.tex` to a PDF (optional — requires LaTeX installed)
6. **Tailor** — Paste a job description and get a resume with auto-selected relevant content

## License

MIT
