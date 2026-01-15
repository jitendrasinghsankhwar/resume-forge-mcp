#!/usr/bin/env python3
"""
LaTeX Resume MCP Server
Create, edit, and compile LaTeX resumes directly from Claude.
"""

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("latex-resume")

# Configurable directories via environment variables
def get_resumes_dir() -> Path:
    """Get the resumes directory from env or default."""
    default = Path.home() / ".latex-resumes" / "resumes"
    return Path(os.environ.get("LATEX_RESUME_DIR", default))

def get_templates_dir() -> Path:
    """Get the templates directory from env or default."""
    default = Path.home() / ".latex-resumes" / "templates"
    return Path(os.environ.get("LATEX_TEMPLATES_DIR", default))

# LaTeX Resume Templates
LATEX_TEMPLATES = {
    "modern": r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{hyperref}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{xcolor}

\geometry{left=0.75in, right=0.75in, top=0.5in, bottom=0.5in}
\pagestyle{empty}

% Colors
\definecolor{primary}{RGB}{0, 79, 144}
\definecolor{secondary}{RGB}{89, 89, 89}

% Section formatting
\titleformat{\section}{\large\bfseries\color{primary}}{}{0em}{}[\titlerule]
\titlespacing{\section}{0pt}{12pt}{6pt}

% Custom commands
\newcommand{\resumeItem}[1]{\item\small{#1}}
\newcommand{\resumeSubheading}[4]{
  \item
    \begin{tabular*}{\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small#4} \\
    \end{tabular*}\vspace{-5pt}
}

\begin{document}

% Header
\begin{center}
    {\LARGE\bfseries YOUR NAME}\\[4pt]
    \href{mailto:email@example.com}{email@example.com} $|$
    (123) 456-7890 $|$
    \href{https://linkedin.com/in/yourprofile}{LinkedIn} $|$
    \href{https://github.com/yourusername}{GitHub}
\end{center}

\section{Experience}
\begin{itemize}[leftmargin=0.15in, label={}]
\resumeSubheading
    {Company Name}{City, State}
    {Job Title}{Start Date -- End Date}
    \begin{itemize}[leftmargin=0.2in]
        \resumeItem{Accomplishment or responsibility}
        \resumeItem{Another accomplishment}
    \end{itemize}
\end{itemize}

\section{Education}
\begin{itemize}[leftmargin=0.15in, label={}]
\resumeSubheading
    {University Name}{City, State}
    {Degree, Major}{Graduation Date}
\end{itemize}

\section{Skills}
\begin{itemize}[leftmargin=0.15in, label={}]
    \item \textbf{Programming:} Python, JavaScript, Java, C++
    \item \textbf{Tools:} Git, Docker, AWS, Linux
\end{itemize}

\end{document}
""",
    "classic": r"""\documentclass[11pt,letterpaper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{hyperref}
\usepackage{enumitem}

\geometry{margin=1in}
\pagestyle{empty}

\begin{document}

\begin{center}
    {\Large\textbf{YOUR NAME}}\\[6pt]
    Address Line $\bullet$ City, State ZIP\\
    Phone: (123) 456-7890 $\bullet$ Email: email@example.com
\end{center}

\vspace{12pt}

\noindent\textbf{\large OBJECTIVE}\\
\rule{\textwidth}{0.4pt}\\[3pt]
A brief statement about your career objectives.

\vspace{12pt}

\noindent\textbf{\large EDUCATION}\\
\rule{\textwidth}{0.4pt}\\[3pt]
\textbf{University Name} \hfill City, State\\
Degree, Major \hfill Graduation Date\\
GPA: X.XX

\vspace{12pt}

\noindent\textbf{\large EXPERIENCE}\\
\rule{\textwidth}{0.4pt}\\[3pt]
\textbf{Company Name} \hfill City, State\\
\textit{Job Title} \hfill Start Date -- End Date
\begin{itemize}[leftmargin=0.2in, topsep=0pt]
    \item Accomplishment or responsibility
    \item Another accomplishment
\end{itemize}

\vspace{12pt}

\noindent\textbf{\large SKILLS}\\
\rule{\textwidth}{0.4pt}\\[3pt]
\textbf{Technical:} List of technical skills\\
\textbf{Languages:} Languages you speak

\end{document}
""",
    "minimal": r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=0.75in]{geometry}
\usepackage{hyperref}
\usepackage{enumitem}

\pagestyle{empty}
\setlength{\parindent}{0pt}

\begin{document}

\textbf{\Large YOUR NAME}\\[4pt]
email@example.com $|$ (123) 456-7890 $|$ City, State

\vspace{12pt}
\textbf{Experience}\hrulefill\\[6pt]
\textbf{Job Title}, Company Name \hfill Dates\\
\begin{itemize}[leftmargin=0.15in, topsep=0pt, parsep=0pt]
\item Accomplishment
\end{itemize}

\vspace{8pt}
\textbf{Education}\hrulefill\\[6pt]
\textbf{Degree}, University Name \hfill Graduation Date

\vspace{8pt}
\textbf{Skills}\hrulefill\\[6pt]
Skill 1, Skill 2, Skill 3

\end{document}
""",
}


def ensure_dirs():
    """Ensure resume and template directories exist."""
    get_resumes_dir().mkdir(parents=True, exist_ok=True)
    get_templates_dir().mkdir(parents=True, exist_ok=True)


def ensure_tex_extension(filename: str) -> str:
    """Ensure filename has .tex extension."""
    return filename if filename.endswith(".tex") else f"{filename}.tex"


def find_pdflatex() -> str | None:
    """Find pdflatex executable."""
    # Check PATH first
    pdflatex = shutil.which("pdflatex")
    if pdflatex:
        return pdflatex

    # Check common installation locations
    common_paths = [
        "/Library/TeX/texbin/pdflatex",  # MacTeX
        "/usr/local/texlive/2024/bin/x86_64-linux/pdflatex",  # TeX Live Linux
        "/usr/local/texlive/2024/bin/universal-darwin/pdflatex",  # TeX Live macOS
        "/usr/bin/pdflatex",  # System install
    ]

    for path in common_paths:
        if Path(path).exists():
            return path

    return None


@mcp.tool()
def list_resumes() -> str:
    """
    List all LaTeX resume files in the resumes directory.
    Returns filename, last modified date, and file size for each resume.
    """
    ensure_dirs()
    resumes_dir = get_resumes_dir()

    resumes = []
    for file in resumes_dir.glob("*.tex"):
        stats = file.stat()
        resumes.append({
            "filename": file.name,
            "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            "size": stats.st_size
        })

    if not resumes:
        return json.dumps({
            "message": "No resume files found. Use create_resume to create one.",
            "resumes": [],
            "directory": str(resumes_dir)
        })

    return json.dumps({"count": len(resumes), "resumes": resumes, "directory": str(resumes_dir)}, indent=2)


@mcp.tool()
def read_resume(filename: str) -> str:
    """
    Read the contents of a LaTeX resume file.

    Args:
        filename: Name of the resume file (with or without .tex extension)

    Returns the full LaTeX content of the resume.
    """
    ensure_dirs()
    filepath = get_resumes_dir() / ensure_tex_extension(filename)

    if not filepath.exists():
        return json.dumps({"error": f"Resume '{filename}' not found"})

    try:
        content = filepath.read_text(encoding="utf-8")
        return content
    except Exception as e:
        return json.dumps({"error": f"Error reading file: {str(e)}"})


@mcp.tool()
def create_resume(filename: str, content: str = None, template: str = "modern") -> str:
    """
    Create a new LaTeX resume file.

    Args:
        filename: Name for the new resume file (with or without .tex extension)
        content: Full LaTeX content for the resume. If not provided, uses a template.
        template: Template to use if content not provided. Options: 'modern', 'classic', 'minimal'

    Returns confirmation of file creation.
    """
    ensure_dirs()
    filepath = get_resumes_dir() / ensure_tex_extension(filename)

    if filepath.exists():
        return json.dumps({"error": f"Resume '{filename}' already exists. Use edit_resume to modify it."})

    if content:
        resume_content = content
    elif template in LATEX_TEMPLATES:
        resume_content = LATEX_TEMPLATES[template]
    else:
        return json.dumps({"error": f"Unknown template '{template}'. Available: modern, classic, minimal"})

    try:
        filepath.write_text(resume_content, encoding="utf-8")
        return json.dumps({"success": True, "path": str(filepath), "template_used": template if not content else "custom"})
    except Exception as e:
        return json.dumps({"error": f"Error creating file: {str(e)}"})


@mcp.tool()
def edit_resume(filename: str, content: str = None, find: str = None, replace: str = None) -> str:
    """
    Edit an existing LaTeX resume file.

    Args:
        filename: Name of the resume file to edit
        content: New complete content for the resume (replaces everything)
        find: Text to find for targeted replacement (use with 'replace')
        replace: Text to replace the found text with

    Either provide 'content' for full replacement, or 'find' and 'replace' for targeted edit.
    """
    ensure_dirs()
    filepath = get_resumes_dir() / ensure_tex_extension(filename)

    if not filepath.exists():
        return json.dumps({"error": f"Resume '{filename}' not found"})

    try:
        if content:
            filepath.write_text(content, encoding="utf-8")
            return json.dumps({"success": True, "path": str(filepath), "edit_type": "full_replacement"})
        elif find is not None and replace is not None:
            current_content = filepath.read_text(encoding="utf-8")
            if find not in current_content:
                return json.dumps({"error": f"Could not find the specified text in {filename}"})
            new_content = current_content.replace(find, replace)
            filepath.write_text(new_content, encoding="utf-8")
            return json.dumps({"success": True, "path": str(filepath), "edit_type": "find_replace"})
        else:
            return json.dumps({"error": "Must provide either 'content' for full replacement or 'find' and 'replace' for targeted edit."})
    except Exception as e:
        return json.dumps({"error": f"Error editing file: {str(e)}"})


@mcp.tool()
def delete_resume(filename: str) -> str:
    """
    Delete a LaTeX resume file.

    Args:
        filename: Name of the resume file to delete
    """
    ensure_dirs()
    filepath = get_resumes_dir() / ensure_tex_extension(filename)

    if not filepath.exists():
        return json.dumps({"error": f"Resume '{filename}' not found"})

    try:
        filepath.unlink()
        return json.dumps({"success": True, "deleted": str(filepath)})
    except Exception as e:
        return json.dumps({"error": f"Error deleting file: {str(e)}"})


@mcp.tool()
def compile_resume(filename: str, output_dir: str = None) -> str:
    """
    Compile a LaTeX resume to PDF using pdflatex.

    Args:
        filename: Name of the resume file to compile
        output_dir: Output directory for the PDF (default: same as resumes directory)

    Returns the path to the generated PDF or compilation errors.
    """
    ensure_dirs()
    resumes_dir = get_resumes_dir()
    filepath = resumes_dir / ensure_tex_extension(filename)

    if not filepath.exists():
        return json.dumps({"error": f"Resume '{filename}' not found"})

    pdflatex_cmd = find_pdflatex()
    if not pdflatex_cmd:
        return json.dumps({
            "error": "pdflatex not found. Please install LaTeX:",
            "install_instructions": {
                "macOS": "brew install --cask mactex  # or: brew install --cask basictex",
                "Ubuntu/Debian": "sudo apt install texlive-latex-base texlive-latex-extra",
                "Fedora": "sudo dnf install texlive-scheme-basic",
                "Windows": "Download from https://miktex.org/"
            }
        })

    out_dir = Path(output_dir) if output_dir else resumes_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Run pdflatex twice for proper reference resolution
        for _ in range(2):
            result = subprocess.run(
                [pdflatex_cmd, "-interaction=nonstopmode", f"-output-directory={out_dir}", filepath.name],
                cwd=resumes_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

        pdf_name = filepath.stem + ".pdf"
        pdf_path = out_dir / pdf_name

        if pdf_path.exists():
            # Clean up auxiliary files
            for ext in [".aux", ".log", ".out"]:
                aux_file = out_dir / (filepath.stem + ext)
                if aux_file.exists():
                    aux_file.unlink()

            return json.dumps({
                "success": True,
                "pdf_path": str(pdf_path),
                "message": f"Successfully compiled {filename} to PDF"
            })
        else:
            return json.dumps({
                "error": "Compilation failed",
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-2000:] if result.stderr else ""
            })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Compilation timed out after 60 seconds"})
    except Exception as e:
        return json.dumps({"error": f"Compilation error: {str(e)}"})


@mcp.tool()
def list_templates() -> str:
    """
    List available resume templates.
    Returns the names and descriptions of built-in LaTeX resume templates.
    """
    templates = {
        "modern": "Clean, professional design with color accents and structured formatting",
        "classic": "Traditional resume format with clear sections and horizontal rules",
        "minimal": "Simple, no-frills layout focusing on content"
    }
    return json.dumps(templates, indent=2)


@mcp.tool()
def get_template(template_name: str) -> str:
    """
    Get the content of a resume template.

    Args:
        template_name: Name of the template (modern, classic, minimal)

    Returns the full LaTeX template content.
    """
    if template_name not in LATEX_TEMPLATES:
        return json.dumps({"error": f"Template '{template_name}' not found. Available: modern, classic, minimal"})

    return LATEX_TEMPLATES[template_name]


@mcp.tool()
def add_experience(
    filename: str,
    company: str,
    title: str,
    dates: str,
    bullets: list[str],
    location: str = ""
) -> str:
    """
    Add a new work experience entry to a resume (works with modern template).

    Args:
        filename: Name of the resume file
        company: Company name
        title: Job title
        dates: Employment dates (e.g., 'Jan 2020 -- Present')
        bullets: List of bullet points describing responsibilities/achievements
        location: Location (city, state/country) - optional
    """
    ensure_dirs()
    filepath = get_resumes_dir() / ensure_tex_extension(filename)

    if not filepath.exists():
        return json.dumps({"error": f"Resume '{filename}' not found"})

    try:
        content = filepath.read_text(encoding="utf-8")

        bullet_items = "\n".join([f"        \\resumeItem{{{b}}}" for b in bullets])
        experience_entry = f"""\\resumeSubheading
    {{{company}}}{{{location}}}
    {{{title}}}{{{dates}}}
    \\begin{{itemize}}[leftmargin=0.2in]
{bullet_items}
    \\end{{itemize}}"""

        import re
        pattern = r"(\\section\{Experience\}[\s\S]*?\\begin\{itemize\}\[leftmargin=0\.15in, label=\{\}\])"
        match = re.search(pattern, content, re.IGNORECASE)

        if match:
            insert_pos = match.end()
            new_content = content[:insert_pos] + "\n" + experience_entry + content[insert_pos:]
            filepath.write_text(new_content, encoding="utf-8")
            return json.dumps({"success": True, "message": f"Added experience entry for {company}"})
        else:
            return json.dumps({"error": "Could not find Experience section. Make sure the resume uses the modern template format."})
    except Exception as e:
        return json.dumps({"error": f"Error adding experience: {str(e)}"})


@mcp.tool()
def add_education(
    filename: str,
    institution: str,
    degree: str,
    dates: str,
    location: str = "",
    details: list[str] = None
) -> str:
    """
    Add a new education entry to a resume (works with modern template).

    Args:
        filename: Name of the resume file
        institution: School/University name
        degree: Degree and major
        dates: Dates attended (e.g., 'Sep 2016 -- May 2020')
        location: Location - optional
        details: Additional details (GPA, honors, coursework) - optional
    """
    ensure_dirs()
    filepath = get_resumes_dir() / ensure_tex_extension(filename)

    if not filepath.exists():
        return json.dumps({"error": f"Resume '{filename}' not found"})

    try:
        content = filepath.read_text(encoding="utf-8")

        education_entry = f"""\\resumeSubheading
    {{{institution}}}{{{location}}}
    {{{degree}}}{{{dates}}}"""

        if details:
            detail_items = "\n".join([f"        \\resumeItem{{{d}}}" for d in details])
            education_entry += f"""
    \\begin{{itemize}}[leftmargin=0.2in]
{detail_items}
    \\end{{itemize}}"""

        import re
        pattern = r"(\\section\{Education\}[\s\S]*?\\begin\{itemize\}\[leftmargin=0\.15in, label=\{\}\])"
        match = re.search(pattern, content, re.IGNORECASE)

        if match:
            insert_pos = match.end()
            new_content = content[:insert_pos] + "\n" + education_entry + content[insert_pos:]
            filepath.write_text(new_content, encoding="utf-8")
            return json.dumps({"success": True, "message": f"Added education entry for {institution}"})
        else:
            return json.dumps({"error": "Could not find Education section. Make sure the resume uses the modern template format."})
    except Exception as e:
        return json.dumps({"error": f"Error adding education: {str(e)}"})


@mcp.tool()
def get_config() -> str:
    """
    Get current configuration including directories and pdflatex status.
    """
    pdflatex = find_pdflatex()
    return json.dumps({
        "resumes_directory": str(get_resumes_dir()),
        "templates_directory": str(get_templates_dir()),
        "pdflatex_installed": pdflatex is not None,
        "pdflatex_path": pdflatex,
        "env_vars": {
            "LATEX_RESUME_DIR": "Set to customize resumes directory",
            "LATEX_TEMPLATES_DIR": "Set to customize templates directory"
        }
    }, indent=2)


# =============================================================================
# Observability Tools - Analyze LaTeX and PDF for issues
# =============================================================================

@mcp.tool()
def analyze_latex(filename: str) -> str:
    """
    Analyze a LaTeX resume file for common issues and potential problems.

    Checks for:
    - Syntax errors (unmatched braces, environments)
    - Missing required packages
    - Overly long lines that may cause overflow
    - Common formatting issues
    - Placeholder text that wasn't replaced
    - Special characters that need escaping

    Args:
        filename: Name of the resume file to analyze

    Returns detailed analysis with warnings and suggestions.
    """
    ensure_dirs()
    filepath = get_resumes_dir() / ensure_tex_extension(filename)

    if not filepath.exists():
        return json.dumps({"error": f"Resume '{filename}' not found"})

    try:
        content = filepath.read_text(encoding="utf-8")
        lines = content.split('\n')

        issues = []
        warnings = []
        info = []

        # Track brace balance
        brace_count = 0
        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('%'):
                continue
            brace_count += line.count('{') - line.count('}')

        if brace_count != 0:
            issues.append({
                "type": "syntax_error",
                "message": f"Unbalanced braces: {'+' if brace_count > 0 else ''}{brace_count} unclosed",
                "severity": "error"
            })

        # Check for unmatched begin/end environments
        import re
        begins = re.findall(r'\\begin\{(\w+)\}', content)
        ends = re.findall(r'\\end\{(\w+)\}', content)

        begin_counts = {}
        end_counts = {}
        for env in begins:
            begin_counts[env] = begin_counts.get(env, 0) + 1
        for env in ends:
            end_counts[env] = end_counts.get(env, 0) + 1

        for env in set(list(begin_counts.keys()) + list(end_counts.keys())):
            b = begin_counts.get(env, 0)
            e = end_counts.get(env, 0)
            if b != e:
                issues.append({
                    "type": "environment_mismatch",
                    "message": f"Environment '{env}': {b} \\begin vs {e} \\end",
                    "severity": "error"
                })

        # Check for placeholder text
        placeholders = [
            "YOUR NAME", "email@example.com", "Company Name", "Job Title",
            "University Name", "City, State", "Start Date", "End Date",
            "Graduation Date", "Accomplishment or responsibility",
            "yourprofile", "yourusername", "(123) 456-7890"
        ]

        for placeholder in placeholders:
            if placeholder in content:
                warnings.append({
                    "type": "placeholder_text",
                    "message": f"Placeholder text found: '{placeholder}'",
                    "severity": "warning"
                })

        # Check for long lines (potential overflow)
        for i, line in enumerate(lines, 1):
            # Skip comments and empty lines
            stripped = line.strip()
            if stripped.startswith('%') or not stripped:
                continue

            # Check visible text length (rough estimate)
            # Remove LaTeX commands for length check
            visible_text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', line)
            visible_text = re.sub(r'\\[a-zA-Z]+', '', visible_text)

            if len(visible_text) > 100:
                warnings.append({
                    "type": "long_line",
                    "message": f"Line {i} may be too long ({len(visible_text)} chars visible) - could cause overflow",
                    "line_number": i,
                    "severity": "warning"
                })

        # Check for special characters that need escaping
        special_chars = ['&', '%', '$', '#', '_']
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('%'):
                continue
            for char in special_chars:
                # Find unescaped special characters
                pattern = rf'(?<!\\){re.escape(char)}'
                if char == '%':
                    # % starts a comment, so only issue if it's clearly meant as literal
                    continue
                matches = list(re.finditer(pattern, line))
                for match in matches:
                    # Check if it's in a safe context (like $...$ for math)
                    if char == '$':
                        continue  # $ is for math mode
                    if char == '&' and '\\begin{tabular' in content:
                        continue  # & is for table columns
                    warnings.append({
                        "type": "unescaped_char",
                        "message": f"Line {i}: Unescaped '{char}' - use '\\{char}' if literal",
                        "line_number": i,
                        "severity": "warning"
                    })

        # Check for common package requirements
        required_packages = {
            r'\\href': 'hyperref',
            r'\\textcolor': 'xcolor',
            r'\\definecolor': 'xcolor',
            r'\\geometry': 'geometry',
            r'\\begin\{itemize\}': 'enumitem (for options)',
        }

        for pattern, package in required_packages.items():
            if re.search(pattern, content):
                if f'\\usepackage{{{package.split()[0]}}}' not in content and f'\\usepackage[' not in content:
                    # More lenient check
                    pkg_name = package.split()[0]
                    if pkg_name not in content:
                        info.append({
                            "type": "package_info",
                            "message": f"Uses {pattern.replace(chr(92), '')} - ensure '{package}' is loaded",
                            "severity": "info"
                        })

        # Count sections and items for structure overview
        sections = re.findall(r'\\section\{([^}]+)\}', content)
        experience_count = len(re.findall(r'\\resumeSubheading', content))
        bullet_count = len(re.findall(r'\\resumeItem|\\item', content))

        # Estimate page length (rough heuristic)
        content_lines = len([l for l in lines if l.strip() and not l.strip().startswith('%')])
        estimated_fullness = min(100, int((content_lines / 60) * 100))

        if estimated_fullness > 95:
            warnings.append({
                "type": "page_overflow",
                "message": f"Content may exceed one page (~{estimated_fullness}% full)",
                "severity": "warning"
            })
        elif estimated_fullness < 40:
            info.append({
                "type": "sparse_content",
                "message": f"Resume appears sparse (~{estimated_fullness}% full) - consider adding more content",
                "severity": "info"
            })

        return json.dumps({
            "filename": filename,
            "analysis": {
                "errors": [i for i in issues if i.get("severity") == "error"],
                "warnings": warnings,
                "info": info,
                "structure": {
                    "sections": sections,
                    "experience_entries": experience_count,
                    "bullet_points": bullet_count,
                    "estimated_page_fullness": f"{estimated_fullness}%"
                }
            },
            "summary": {
                "error_count": len([i for i in issues if i.get("severity") == "error"]),
                "warning_count": len(warnings),
                "info_count": len(info),
                "status": "errors_found" if issues else ("warnings_found" if warnings else "ok")
            }
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Analysis failed: {str(e)}"})


@mcp.tool()
def inspect_pdf(filename: str) -> str:
    """
    Inspect a compiled PDF resume for metadata, page info, and extract text content.

    This allows the LLM to verify:
    - PDF was generated successfully
    - Number of pages (should be 1 for most resumes)
    - Text content is correct and complete
    - No content was cut off

    Args:
        filename: Name of the resume (with or without extension)

    Returns PDF metadata and extracted text content.
    """
    ensure_dirs()
    resumes_dir = get_resumes_dir()

    # Handle both .tex and .pdf extensions
    if filename.endswith('.tex'):
        pdf_filename = filename.replace('.tex', '.pdf')
    elif filename.endswith('.pdf'):
        pdf_filename = filename
    else:
        pdf_filename = f"{filename}.pdf"

    pdf_path = resumes_dir / pdf_filename

    if not pdf_path.exists():
        return json.dumps({
            "error": f"PDF '{pdf_filename}' not found. Run compile_resume first.",
            "hint": "Use compile_resume to generate the PDF from the .tex file"
        })

    result = {
        "filename": pdf_filename,
        "path": str(pdf_path),
        "file_size_bytes": pdf_path.stat().st_size,
        "file_size_kb": round(pdf_path.stat().st_size / 1024, 2),
        "modified": datetime.fromtimestamp(pdf_path.stat().st_mtime).isoformat()
    }

    # Try to extract text using pdftotext if available
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        # Check common locations
        for path in ["/opt/homebrew/bin/pdftotext", "/usr/local/bin/pdftotext", "/usr/bin/pdftotext"]:
            if Path(path).exists():
                pdftotext = path
                break

    if pdftotext:
        try:
            # Extract text with layout preservation
            text_result = subprocess.run(
                [pdftotext, "-layout", str(pdf_path), "-"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if text_result.returncode == 0:
                extracted_text = text_result.stdout
                lines = extracted_text.strip().split('\n')

                result["text_extraction"] = {
                    "success": True,
                    "total_characters": len(extracted_text),
                    "total_lines": len(lines),
                    "content": extracted_text[:5000] if len(extracted_text) > 5000 else extracted_text,
                    "truncated": len(extracted_text) > 5000
                }

                # Analyze extracted text for issues
                text_issues = []

                # Check for common problems
                if len(lines) < 10:
                    text_issues.append("Very few lines extracted - possible compilation issue")

                if "?" in extracted_text and extracted_text.count("?") > 5:
                    text_issues.append("Multiple '?' characters - possible font/encoding issue")

                # Check if content seems cut off (ends mid-sentence)
                if extracted_text.strip() and not extracted_text.strip()[-1] in '.!?)':
                    text_issues.append("Content may be cut off (doesn't end with punctuation)")

                # Look for overflow indicators
                if "Overfull" in extracted_text or "Underfull" in extracted_text:
                    text_issues.append("LaTeX overflow/underflow warnings present")

                result["text_issues"] = text_issues
            else:
                result["text_extraction"] = {
                    "success": False,
                    "error": text_result.stderr
                }
        except Exception as e:
            result["text_extraction"] = {
                "success": False,
                "error": str(e)
            }
    else:
        result["text_extraction"] = {
            "success": False,
            "error": "pdftotext not installed. Install poppler: brew install poppler (macOS) or apt install poppler-utils (Linux)"
        }

    # Try to get page count using pdfinfo
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        for path in ["/opt/homebrew/bin/pdfinfo", "/usr/local/bin/pdfinfo", "/usr/bin/pdfinfo"]:
            if Path(path).exists():
                pdfinfo = path
                break

    if pdfinfo:
        try:
            info_result = subprocess.run(
                [pdfinfo, str(pdf_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if info_result.returncode == 0:
                info_lines = info_result.stdout.strip().split('\n')
                pdf_metadata = {}

                for line in info_lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        pdf_metadata[key.strip().lower().replace(' ', '_')] = value.strip()

                result["pdf_metadata"] = pdf_metadata

                # Check page count
                pages = int(pdf_metadata.get('pages', 1))
                if pages > 1:
                    result["page_warning"] = f"Resume is {pages} pages - consider condensing to 1 page"
                elif pages == 1:
                    result["page_status"] = "Good - resume fits on 1 page"

        except Exception as e:
            result["pdf_metadata"] = {"error": str(e)}

    return json.dumps(result, indent=2)


@mcp.tool()
def check_compilation_log(filename: str) -> str:
    """
    Check the LaTeX compilation log for warnings and errors.

    This provides detailed information about:
    - Overfull/underfull boxes (text overflow issues)
    - Missing fonts or packages
    - Undefined references
    - Any LaTeX warnings

    Args:
        filename: Name of the resume file

    Returns parsed compilation warnings and errors.
    """
    ensure_dirs()
    resumes_dir = get_resumes_dir()

    # Get the .log file
    base_name = filename.replace('.tex', '').replace('.pdf', '')
    log_path = resumes_dir / f"{base_name}.log"

    if not log_path.exists():
        return json.dumps({
            "error": f"Log file not found for '{filename}'",
            "hint": "Run compile_resume first (log file is created during compilation)"
        })

    try:
        log_content = log_path.read_text(encoding="utf-8", errors="replace")

        # Parse the log for issues
        issues = {
            "errors": [],
            "warnings": [],
            "overfull_boxes": [],
            "underfull_boxes": [],
            "missing_items": []
        }

        lines = log_content.split('\n')

        for i, line in enumerate(lines):
            # Errors
            if line.startswith('!') or 'Error:' in line:
                # Get context
                context = lines[i:i+3] if i+3 < len(lines) else lines[i:]
                issues["errors"].append({
                    "message": line,
                    "context": '\n'.join(context)
                })

            # Overfull boxes (content too wide)
            if 'Overfull' in line:
                issues["overfull_boxes"].append(line.strip())

            # Underfull boxes (content too sparse)
            if 'Underfull' in line:
                issues["underfull_boxes"].append(line.strip())

            # Warnings
            if 'Warning:' in line or 'warning' in line.lower():
                if 'Overfull' not in line and 'Underfull' not in line:
                    issues["warnings"].append(line.strip())

            # Missing items
            if 'Missing' in line or 'not found' in line.lower():
                issues["missing_items"].append(line.strip())

        # Summarize
        summary = {
            "error_count": len(issues["errors"]),
            "warning_count": len(issues["warnings"]),
            "overfull_count": len(issues["overfull_boxes"]),
            "underfull_count": len(issues["underfull_boxes"]),
            "status": "success" if not issues["errors"] else "errors"
        }

        # Add recommendations
        recommendations = []

        if issues["overfull_boxes"]:
            recommendations.append("Overfull boxes detected - some text may extend past margins. Consider shorter text or adjusting margins.")

        if issues["underfull_boxes"]:
            recommendations.append("Underfull boxes detected - some areas have awkward spacing. Usually cosmetic but may indicate layout issues.")

        if not issues["errors"] and not issues["overfull_boxes"]:
            recommendations.append("Compilation looks clean - no major issues detected.")

        return json.dumps({
            "filename": filename,
            "issues": issues,
            "summary": summary,
            "recommendations": recommendations
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to parse log: {str(e)}"})


@mcp.tool()
def compile_and_verify(filename: str) -> str:
    """
    Compile a resume and automatically run all verification checks.

    This is a convenience tool that:
    1. Analyzes the LaTeX source for issues
    2. Compiles to PDF
    3. Inspects the generated PDF
    4. Checks the compilation log

    Returns a comprehensive report of the resume's status.

    Args:
        filename: Name of the resume file to compile and verify
    """
    ensure_dirs()
    results = {
        "filename": filename,
        "steps": {}
    }

    # Step 1: Analyze LaTeX
    latex_analysis = json.loads(analyze_latex(filename))
    results["steps"]["latex_analysis"] = latex_analysis

    # Check for blocking errors
    if "error" in latex_analysis:
        return json.dumps({
            "error": latex_analysis["error"],
            "step": "latex_analysis"
        })

    has_errors = latex_analysis.get("summary", {}).get("error_count", 0) > 0

    if has_errors:
        results["status"] = "blocked"
        results["message"] = "LaTeX errors found - fix before compiling"
        return json.dumps(results, indent=2)

    # Step 2: Compile
    compile_result = json.loads(compile_resume(filename))
    results["steps"]["compilation"] = compile_result

    if "error" in compile_result:
        results["status"] = "compilation_failed"
        results["message"] = compile_result["error"]
        return json.dumps(results, indent=2)

    # Step 3: Check log (don't fail on this)
    try:
        log_check = json.loads(check_compilation_log(filename))
        results["steps"]["log_analysis"] = log_check
    except:
        results["steps"]["log_analysis"] = {"note": "Log analysis skipped"}

    # Step 4: Inspect PDF
    pdf_inspection = json.loads(inspect_pdf(filename))
    results["steps"]["pdf_inspection"] = pdf_inspection

    # Generate overall summary
    warnings = []

    if latex_analysis.get("summary", {}).get("warning_count", 0) > 0:
        warnings.append(f"{latex_analysis['summary']['warning_count']} LaTeX warnings")

    if "page_warning" in pdf_inspection:
        warnings.append(pdf_inspection["page_warning"])

    log_issues = results["steps"].get("log_analysis", {}).get("summary", {})
    if log_issues.get("overfull_count", 0) > 0:
        warnings.append(f"{log_issues['overfull_count']} overfull boxes (text may overflow)")

    results["status"] = "success" if not warnings else "success_with_warnings"
    results["warnings"] = warnings
    results["pdf_path"] = compile_result.get("pdf_path")
    results["message"] = "Resume compiled successfully" + (f" with {len(warnings)} warning(s)" if warnings else "")

    return json.dumps(results, indent=2)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
