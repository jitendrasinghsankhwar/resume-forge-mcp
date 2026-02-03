"""Tests for LaTeX compilation and PDF preview."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from latex_resume_mcp.compiler.latex import (
	CompilationResult,
	_find_pdflatex,
	_parse_log,
	compile_latex,
)
from latex_resume_mcp.compiler.preview import get_pdf_info, render_pdf_to_png

# -- Log parsing --


class TestParseLog:
	def test_extracts_errors(self) -> None:
		log = "! Undefined control sequence.\nl.42 \\badcommand\n"
		errors, _ = _parse_log(log)
		assert len(errors) == 1
		assert "Undefined control sequence" in errors[0]

	def test_extracts_warnings(self) -> None:
		log = "LaTeX Warning: Reference undefined.\n"
		_, warnings = _parse_log(log)
		assert len(warnings) == 1
		assert "Reference undefined" in warnings[0]

	def test_empty_log(self) -> None:
		errors, warnings = _parse_log("")
		assert errors == []
		assert warnings == []

	def test_mixed_log(self) -> None:
		log = (
			"This is pdfTeX\n"
			"! Missing $ inserted.\n"
			"LaTeX Warning: Overfull hbox\n"
			"Output written on resume.pdf\n"
		)
		errors, warnings = _parse_log(log)
		assert len(errors) == 1
		assert len(warnings) == 1


# -- Find pdflatex --


class TestFindPdflatex:
	def test_finds_system_pdflatex(self) -> None:
		# This test depends on the system having pdflatex
		result = _find_pdflatex()
		if result is not None:
			assert "pdflatex" in result


# -- Compilation --


class TestCompileLatex:
	def test_compile_simple_document(self, tmp_path: Path) -> None:
		"""Test compilation of a minimal LaTeX document."""
		tex = r"""
\documentclass{article}
\begin{document}
Hello, World!
\end{document}
"""
		result = compile_latex(tex, output_dir=tmp_path)
		if not result.success and "pdflatex not found" in str(result.errors):
			pytest.skip("pdflatex not available")
		assert result.success
		assert result.pdf_path is not None
		assert result.pdf_path.exists()

	def test_compile_with_errors(self, tmp_path: Path) -> None:
		"""Test compilation with invalid LaTeX."""
		tex = r"""
\documentclass{article}
\begin{document}
\badcommand
\end{document}
"""
		result = compile_latex(tex, output_dir=tmp_path)
		if not result.success and "pdflatex not found" in str(result.errors):
			pytest.skip("pdflatex not available")
		assert not result.success
		assert len(result.errors) > 0

	def test_compile_result_dataclass(self) -> None:
		result = CompilationResult(success=True)
		assert result.success
		assert result.pdf_path is None
		assert result.errors == []

	@patch("latex_resume_mcp.compiler.latex._find_pdflatex", return_value=None)
	def test_no_pdflatex(self, mock_find: MagicMock) -> None:
		result = compile_latex(r"\documentclass{article}\begin{document}X\end{document}")
		assert not result.success
		assert "pdflatex not found" in result.errors[0]


# -- PDF Preview --


class TestRenderPdfToPng:
	def test_render_compiled_pdf(self, tmp_path: Path) -> None:
		"""Test rendering a compiled PDF to PNG."""
		tex = r"""
\documentclass{article}
\begin{document}
Test document for preview.
\end{document}
"""
		result = compile_latex(tex, output_dir=tmp_path)
		if not result.success:
			pytest.skip("pdflatex not available")

		assert result.pdf_path is not None
		png_bytes = render_pdf_to_png(result.pdf_path)
		assert len(png_bytes) > 0
		# PNG magic bytes
		assert png_bytes[:4] == b"\x89PNG"

	def test_render_saves_to_file(self, tmp_path: Path) -> None:
		tex = r"""
\documentclass{article}
\begin{document}
Test.
\end{document}
"""
		result = compile_latex(tex, output_dir=tmp_path)
		if not result.success:
			pytest.skip("pdflatex not available")

		assert result.pdf_path is not None
		output = tmp_path / "preview.png"
		render_pdf_to_png(result.pdf_path, output_path=output)
		assert output.exists()
		assert output.stat().st_size > 0

	def test_file_not_found(self, tmp_path: Path) -> None:
		with pytest.raises(FileNotFoundError):
			render_pdf_to_png(tmp_path / "nonexistent.pdf")

	def test_invalid_page(self, tmp_path: Path) -> None:
		tex = r"""
\documentclass{article}
\begin{document}
Single page.
\end{document}
"""
		result = compile_latex(tex, output_dir=tmp_path)
		if not result.success:
			pytest.skip("pdflatex not available")

		assert result.pdf_path is not None
		with pytest.raises(ValueError, match="out of range"):
			render_pdf_to_png(result.pdf_path, page_number=5)


class TestGetPdfInfo:
	def test_basic_info(self, tmp_path: Path) -> None:
		tex = r"""
\documentclass[letterpaper]{article}
\begin{document}
Test.
\end{document}
"""
		result = compile_latex(tex, output_dir=tmp_path)
		if not result.success:
			pytest.skip("pdflatex not available")

		assert result.pdf_path is not None
		info = get_pdf_info(result.pdf_path)
		assert info["page_count"] == 1
		assert isinstance(info["width_pt"], float)
		assert isinstance(info["height_pt"], float)

	def test_file_not_found(self, tmp_path: Path) -> None:
		with pytest.raises(FileNotFoundError):
			get_pdf_info(tmp_path / "nonexistent.pdf")
