"""LaTeX compilation with pdflatex/xelatex/lualatex fallback."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

LATEX_ENGINES = ["pdflatex", "xelatex", "lualatex"]
SEARCH_PATHS = [
	"/Library/TeX/texbin",
	"/usr/local/texlive/2026/bin/universal-darwin",
	"/usr/local/texlive/2025/bin/universal-darwin",
	"/usr/local/texlive/2024/bin/universal-darwin",
	"/usr/bin",
]


@dataclass
class CompilationResult:
	"""Result of a LaTeX compilation."""

	success: bool
	pdf_path: Path | None = None
	log_output: str = ""
	errors: list[str] = field(default_factory=list)
	warnings: list[str] = field(default_factory=list)
	engine_used: str | None = None


def _find_engine(engine: str) -> str | None:
	"""Find a LaTeX engine binary on the system."""
	for base in SEARCH_PATHS:
		path = Path(base) / engine
		if path.exists():
			return str(path)
	try:
		result = subprocess.run(
			["which", engine], capture_output=True, text=True, timeout=5
		)
		if result.returncode == 0:
			return result.stdout.strip()
	except (subprocess.TimeoutExpired, FileNotFoundError):
		pass
	return None


def _find_pdflatex() -> str | None:
	"""Find pdflatex binary (backward compat)."""
	return _find_engine("pdflatex")


def find_available_engines() -> dict[str, str | None]:
	"""Return dict of engine_name -> path for all available engines."""
	return {e: _find_engine(e) for e in LATEX_ENGINES}


def _detect_required_engine(tex_source: str) -> str | None:
	"""Detect if the source requires a specific engine."""
	if "\\usepackage{fontspec}" in tex_source or "\\setmainfont" in tex_source:
		return "xelatex"
	if "\\usepackage{luacode}" in tex_source or "\\directlua" in tex_source:
		return "lualatex"
	return None


def _parse_log(log_text: str) -> tuple[list[str], list[str]]:
	"""Parse LaTeX log output for errors and warnings."""
	errors: list[str] = []
	warnings: list[str] = []
	for line in log_text.splitlines():
		if line.startswith("!"):
			errors.append(line.strip())
		elif "Warning" in line and not line.startswith("("):
			warnings.append(line.strip())
	return errors, warnings


def _run_engine(
	engine_path: str, tex_path: Path, output_dir: Path
) -> subprocess.CompletedProcess[str]:
	"""Run a single compilation pass."""
	return subprocess.run(
		[
			engine_path,
			"-interaction=nonstopmode",
			"-halt-on-error",
			f"-output-directory={output_dir}",
			str(tex_path),
		],
		capture_output=True,
		text=True,
		timeout=60,
		cwd=str(output_dir),
	)


def compile_latex(
	tex_source: str,
	output_dir: Path | None = None,
	filename: str = "resume",
	engine: str | None = None,
	passes: int = 2,
) -> CompilationResult:
	"""Compile LaTeX source to PDF with automatic engine detection and fallback.

	Tries engines in order: detected from source → specified → pdflatex → xelatex → lualatex.

	Args:
		tex_source: Complete LaTeX source string.
		output_dir: Directory for output files. Uses temp dir if None.
		filename: Base filename (without extension).
		engine: Force a specific engine (pdflatex, xelatex, lualatex). Auto-detects if None.
		passes: Number of compilation passes (default 2 for references).

	Returns:
		CompilationResult with success status, PDF path, engine used, and any errors.
	"""
	if output_dir is None:
		output_dir = Path(tempfile.mkdtemp(prefix="resume_"))
	output_dir.mkdir(parents=True, exist_ok=True)

	tex_path = output_dir / f"{filename}.tex"
	tex_path.write_text(tex_source, encoding="utf-8")

	# Build engine priority list
	detected = _detect_required_engine(tex_source)
	if engine:
		engines_to_try = [engine]
	elif detected:
		engines_to_try = [detected, "pdflatex", "xelatex", "lualatex"]
	else:
		engines_to_try = ["pdflatex", "xelatex", "lualatex"]
	# Deduplicate while preserving order
	seen: set[str] = set()
	engines_to_try = [e for e in engines_to_try if not (e in seen or seen.add(e))]  # type: ignore[func-returns-value]

	last_errors: list[str] = []

	for eng in engines_to_try:
		eng_path = _find_engine(eng)
		if not eng_path:
			continue

		try:
			# Run multiple passes
			result = None
			for _ in range(passes):
				result = _run_engine(eng_path, tex_path, output_dir)

			if result is None:
				continue

			log_output = result.stdout + result.stderr
			errors, warnings = _parse_log(log_output)
			pdf_path = output_dir / f"{filename}.pdf"
			success = pdf_path.exists()

			if success:
				# Clean aux files
				for ext in [".aux", ".log", ".out", ".fls", ".fdb_latexmk", ".synctex.gz"]:
					aux = output_dir / f"{filename}{ext}"
					if aux.exists():
						aux.unlink()

				return CompilationResult(
					success=True,
					pdf_path=pdf_path,
					log_output=log_output,
					errors=[],
					warnings=warnings,
					engine_used=eng,
				)

			last_errors = errors or [f"{eng} failed with return code {result.returncode}"]

		except subprocess.TimeoutExpired:
			last_errors = [f"{eng} timed out after 60 seconds"]
		except FileNotFoundError:
			last_errors = [f"{eng} binary not found"]

	# All engines failed
	if not any(_find_engine(e) for e in LATEX_ENGINES):
		last_errors = ["No LaTeX engine found. Install MacTeX: brew install --cask mactex-no-gui"]

	return CompilationResult(
		success=False,
		errors=last_errors,
	)
