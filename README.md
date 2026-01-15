# LaTeX Resume MCP

An MCP (Model Context Protocol) server that lets you create, edit, and compile LaTeX resumes directly from Claude.

## Features

- **Create resumes** from built-in templates (modern, classic, minimal)
- **Edit resumes** with full replacement or targeted find/replace
- **Compile to PDF** using pdflatex (requires LaTeX installation)
- **Add experience/education** entries with structured commands
- **List and manage** multiple resume files
- **Observability tools** - Analyze LaTeX for errors, inspect PDFs, verify formatting

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
        "LATEX_RESUME_DIR": "/path/to/your/resumes",
        "LATEX_TEMPLATES_DIR": "/path/to/your/templates"
      }
    }
  }
}
```

## Prerequisites for PDF Compilation

To compile resumes to PDF, you need LaTeX installed:

**macOS:**
```bash
brew install --cask mactex
# or for a smaller installation:
brew install --cask basictex
```

**Ubuntu/Debian:**
```bash
sudo apt install texlive-latex-base texlive-latex-extra
```

**Fedora:**
```bash
sudo dnf install texlive-scheme-basic
```

**Windows:**
Download and install [MiKTeX](https://miktex.org/)

## Available Tools

### Resume Management
| Tool | Description |
|------|-------------|
| `list_resumes` | List all resume files |
| `read_resume` | Read a resume's content |
| `create_resume` | Create a new resume |
| `edit_resume` | Edit an existing resume |
| `delete_resume` | Delete a resume |
| `compile_resume` | Compile to PDF |

### Templates
| Tool | Description |
|------|-------------|
| `list_templates` | Show available templates |
| `get_template` | Get template content |
| `add_experience` | Add work experience |
| `add_education` | Add education entry |

### Observability & Verification
| Tool | Description |
|------|-------------|
| `analyze_latex` | Check LaTeX for syntax errors, placeholder text, long lines |
| `inspect_pdf` | Extract text from PDF, check page count, verify content |
| `check_compilation_log` | Parse log for overfull boxes, warnings, errors |
| `compile_and_verify` | Compile + run all checks in one step |
| `get_config` | Show current configuration |

## Usage Examples

Once configured, you can use natural language in Claude:

- "Create a new resume called software_engineer using the modern template"
- "Add my experience at Google as a Senior Engineer from 2020 to present"
- "Update my resume to change the email to newemail@example.com"
- "Compile my resume and check for any issues"
- "Analyze my resume for formatting problems"
- "List all my resumes"

### Observability Example

The `compile_and_verify` tool runs a complete check:

```
> Compile and verify my resume

✓ LaTeX Analysis: 2 warnings (placeholder text found)
✓ Compilation: Success
✓ PDF Inspection: 1 page, 2847 characters extracted
✓ Log Check: No overfull boxes

Status: success_with_warnings
PDF: ~/.latex-resumes/resumes/my_resume.pdf
```

## Templates

### Modern
Clean, professional design with color accents and structured formatting. Best for tech roles.

### Classic
Traditional resume format with clear sections and horizontal rules. Good for conservative industries.

### Minimal
Simple, no-frills layout focusing purely on content. Great for academic or research positions.

## Default Directories

Resumes are stored in `~/.latex-resumes/resumes/` by default. You can customize this with the `LATEX_RESUME_DIR` environment variable.

## Optional: PDF Text Extraction

For full PDF inspection (text extraction, page count), install poppler:

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt install poppler-utils
```

This enables the `inspect_pdf` tool to extract and verify text content from compiled PDFs.

## License

MIT
