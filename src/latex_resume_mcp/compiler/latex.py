"""LaTeX compilation using pdflatex."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CompilationResult:
	"""Result of a LaTeX compilation."""

	success: bool
	pdf_path: Path | None = None
	log_output: str = ""
	errors: list[str] = field(default_factory=list)
	warnings: list[str] = field(default_factory=list)


def _find_pdflatex() -> str | None:
	"""Find pdflatex binary on the system."""
	candidates = [
		"/Library/TeX/texbin/pdflatex",
		"/usr/local/texlive/2024/bin/universal-darwin/pdflatex",
		"/usr/bin/pdflatex",
	]
	for path in candidates:
		if Path(path).exists():
			return path
	# Try PATH
	try:
		result = subprocess.run(  # nosec B603 B607
			["which", "pdflatex"],
			capture_output=True,
			text=True,
			timeout=5,
		)
		if result.returncode == 0:
			return result.stdout.strip()
	except (subprocess.TimeoutExpired, FileNotFoundError):
		pass
	return None


def _parse_log(log_text: str) -> tuple[list[str], list[str]]:
	"""Parse pdflatex log output for errors and warnings."""
	errors: list[str] = []
	warnings: list[str] = []
	for line in log_text.splitlines():
		if line.startswith("!"):
			errors.append(line.strip())
		elif "Warning" in line and not line.startswith("("):
			warnings.append(line.strip())
	return errors, warnings


def compile_latex(
	tex_source: str,
	output_dir: Path | None = None,
	filename: str = "resume",
) -> CompilationResult:
	"""Compile LaTeX source to PDF using pdflatex.

	Args:
		tex_source: Complete LaTeX source string.
		output_dir: Directory for output files. Uses temp dir if None.
		filename: Base filename (without extension).

	Returns:
		CompilationResult with success status, PDF path, and any errors.
	"""
	pdflatex = _find_pdflatex()
	if not pdflatex:
		return CompilationResult(
			success=False,
			errors=["pdflatex not found. Install a TeX distribution (e.g., MacTeX)."],
		)

	if output_dir is None:
		output_dir = Path(tempfile.mkdtemp(prefix="resume_"))
	output_dir.mkdir(parents=True, exist_ok=True)

	tex_path = output_dir / f"{filename}.tex"
	tex_path.write_text(tex_source, encoding="utf-8")

	try:
		result = subprocess.run(  # nosec B603
			[
				pdflatex,
				"-interaction=nonstopmode",
				"-halt-on-error",
				f"-output-directory={output_dir}",
				str(tex_path),
			],
			capture_output=True,
			text=True,
			timeout=30,
			cwd=str(output_dir),
		)
	except subprocess.TimeoutExpired:
		return CompilationResult(
			success=False,
			errors=["pdflatex compilation timed out after 30 seconds"],
		)
	except FileNotFoundError:
		return CompilationResult(
			success=False,
			errors=["pdflatex binary not found at expected path"],
		)

	log_output = result.stdout + result.stderr
	errors, warnings = _parse_log(log_output)

	pdf_path = output_dir / f"{filename}.pdf"
	success = pdf_path.exists() and result.returncode == 0

	if not success and not errors:
		errors.append(f"Compilation failed with return code {result.returncode}")

	return CompilationResult(
		success=success,
		pdf_path=pdf_path if success else None,
		log_output=log_output,
		errors=errors,
		warnings=warnings,
	)
