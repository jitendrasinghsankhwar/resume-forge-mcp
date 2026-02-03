# LaTeX Resume MCP

An MCP (Model Context Protocol) server for intelligent LaTeX resume generation with visual verification, quality scoring, and job description tailoring.

## Features

- **Data-driven resumes**: Store resume content in JSON, generate LaTeX on demand
- **Visual verification**: Preview rendered PDFs as images directly in Claude
- **Quality scoring**: Bullet analysis, ATS compatibility checks, keyword matching
- **Job tailoring**: Auto-select and prioritize content based on job descriptions
- **Variant management**: Create multiple resume versions for different roles
- **LaTeX compilation**: Generate publication-quality PDFs using pdflatex

## Installation

### Using uvx (recommended)

```bash
uvx latex-resume-mcp
```

### Using pip

```bash
pip install latex-resume-mcp
```

## Configuration

Add to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### Using uvx

```json
{
  "mcpServers": {
    "latex-resume": {
      "command": "uvx",
      "args": ["latex-resume-mcp"]
    }
  }
}
```

### Using pip installation

```json
{
  "mcpServers": {
    "latex-resume": {
      "command": "latex-resume-mcp"
    }
  }
}
```

### Custom directories (optional)

```json
{
  "mcpServers": {
    "latex-resume": {
      "command": "uvx",
      "args": ["latex-resume-mcp"],
      "env": {
        "LATEX_RESUME_DATA_DIR": "/path/to/data",
        "LATEX_RESUME_OUTPUT_DIR": "/path/to/output"
      }
    }
  }
}
```

## Prerequisites

### LaTeX Installation

To compile resumes to PDF, you need LaTeX installed:

**macOS:**
```bash
brew install --cask mactex
# or for a smaller installation:
brew install --cask basictex
```

**Ubuntu/Debian:**
```bash
sudo apt install texlive-latex-base texlive-latex-extra texlive-fonts-extra
```

**Windows:**
Download and install [MiKTeX](https://miktex.org/)

## Available Tools (15)

### Data Management

| Tool | Description |
|------|-------------|
| `import_from_latex_file` | Parse existing .tex file into structured JSON data |
| `get_resume_data` | Get the master resume data pool |
| `update_resume_data` | Add, edit, or remove entries (experience, projects, etc.) |
| `list_variants` | List all saved resume variants |
| `get_variant` | Get details of a specific variant |
| `save_variant` | Create or update a variant configuration |

### Generation & Compilation

| Tool | Description |
|------|-------------|
| `generate_resume` | Generate .tex file from data (optionally using a variant) |
| `compile_resume_tex` | Compile .tex to PDF using pdflatex |
| `compile_and_preview` | Compile and return preview images |
| `preview_resume` | Preview an existing PDF as images |

### Intelligence

| Tool | Description |
|------|-------------|
| `score_resume_quality` | Score bullets, check ATS compatibility, match keywords |
| `parse_job_description_text` | Extract keywords and requirements from job description |
| `generate_tailored_resume` | Auto-select content based on JD, compile, and preview |

### Utility

| Tool | Description |
|------|-------------|
| `assess_quality` | Run programmatic checks (page count, encoding, overflow) |
| `get_config` | Show current configuration and available tools |

## Usage Examples

### Basic Workflow

```
> Get my resume data
Shows all stored experience, projects, education, skills

> Generate my resume and compile it
Creates .tex file and compiles to PDF

> Preview my resume
Returns rendered images of each page
```

### Quality Improvement

```
> Score my resume quality
Returns bullet scores, ATS report, improvement suggestions

> Score my resume against keywords: Python, AWS, Kubernetes
Shows keyword match percentage and missing terms
```

### Job Tailoring

```
> Parse this job description: [paste JD text]
Extracts title, required skills, preferred skills, keywords

> Generate a tailored resume for this job description
Auto-selects most relevant experience/projects, reorders skills, compiles
```

### Variant Management

```
> List my resume variants
Shows: swe, ml_engineer, backend, etc.

> Save a new variant called "startup" with experiences 0,1,3
Creates variant configuration

> Generate my resume using the startup variant
Uses variant's content selection and ordering
```

## Data Model

Resume data is stored as JSON with these sections:

- **contact**: Name, email, phone, LinkedIn, GitHub
- **education**: Degrees with GPA, dates, coursework
- **publications**: Academic publications
- **experience**: Work history with bullets and tags
- **projects**: Personal/open-source projects with tags
- **skills**: Categorized skill lists

Each experience and project can have **tags** (e.g., `["swe", "ml", "cloud"]`) for intelligent content selection.

## Default Directories

- **Data**: `~/.latex-resumes/data/` (resume JSON and variants)
- **Output**: `~/.latex-resumes/output/` (generated .tex and .pdf files)

## License

MIT
