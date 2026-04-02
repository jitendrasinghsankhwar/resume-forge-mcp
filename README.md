# Resume Forge MCP

An MCP (Model Context Protocol) server for intelligent LaTeX resume generation with multiple template styles, quality scoring, and job description tailoring.

## Features

- **3 built-in templates**: Modern (color accents), Classic (traditional), Minimal (no-frills)
- **Overleaf integration**: Browse and fetch 350+ templates dynamically
- **Multi-format import**: Import resume data from .tex, .pdf, or .docx files
- **Quality scoring**: Bullet analysis, ATS compatibility, keyword matching
- **Job tailoring**: Auto-select and rank content based on job descriptions
- **Visual preview**: Compile to PDF and preview as images directly in your AI assistant

## Installation

```bash
uvx resume-forge-mcp
```

With PDF and DOCX import support:

```bash
uvx --with pymupdf --with python-docx resume-forge-mcp
```

## Configuration

Add to your AI assistant's MCP config:

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
| `RESUME_DATA_DIR` | `~/.resume-forge/data` | Resume data JSON |
| `RESUME_TEMPLATE_DIR` | `~/.resume-forge/templates` | Fetched Overleaf templates |
| `RESUME_OUTPUT_DIR` | `~/.resume-forge/output` | Generated .tex and .pdf files |

All env vars are optional — defaults to `~/.resume-forge/` subdirectories.

## Prerequisites

For PDF compilation, install LaTeX:

- **macOS**: `brew install --cask mactex`
- **Ubuntu**: `sudo apt install texlive-latex-base texlive-latex-extra texlive-fonts-extra`
- **Windows**: Install [MiKTeX](https://miktex.org/)

## Tools (11)

### Templates
| Tool | Description |
|------|-------------|
| `list_templates` | List built-in templates (modern/classic/minimal) + Overleaf info |
| `browse_overleaf_templates` | Browse 350+ Overleaf templates by category |
| `fetch_overleaf_template` | Download an Overleaf template source |

### Data Management
| Tool | Description |
|------|-------------|
| `import_resume` | Import from .tex, .pdf, or .docx into structured data |
| `get_resume_data` | Get the master resume data pool |
| `update_resume_data` | Add, edit, or remove entries in any section |

### Generation & Compilation
| Tool | Description |
|------|-------------|
| `generate_resume` | Render data to .tex using selected template |
| `compile_and_preview` | Compile to PDF and return preview image |
| `generate_tailored_resume` | Parse JD, select content, generate tailored resume |

### Analysis & Config
| Tool | Description |
|------|-------------|
| `score_resume_quality` | Score bullets, ATS compatibility, keyword matching |
| `get_config` | Show configuration and tool availability |

## Usage

```
> List available templates
→ modern, classic, minimal + Overleaf gallery

> Import my resume from resume.tex
→ Extracts contact, education, experience, skills into structured data

> Generate my resume using the classic template
→ Creates .tex file using classic layout

> Score my resume against keywords: Python, AWS, Kubernetes
→ Returns quality scores, ATS report, keyword match percentage

> Generate a tailored resume for this job description: [paste JD]
→ Auto-selects relevant experience, generates and compiles
```

## License

MIT
