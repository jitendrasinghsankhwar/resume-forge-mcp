"""Tests for resume storage and LaTeX import."""

from __future__ import annotations

from pathlib import Path

import pytest

from resume_forge_mcp.models.resume import (
	ResumeData,
	ResumeVariant,
)
from resume_forge_mcp.storage.resume_store import ResumeStore
from resume_forge_mcp.storage.tex_import import (
	_extract_items,
	_parse_heading,
	_parse_skills,
	_split_sections,
	import_from_latex,
)

# -- ResumeStore --


class TestResumeStore:
	def test_save_and_load_data(
		self, tmp_path: Path, sample_resume_data: ResumeData
	) -> None:
		store = ResumeStore(data_dir=tmp_path)
		store.save_data(sample_resume_data)
		loaded = store.load_data()
		assert loaded is not None
		assert loaded.contact.name == sample_resume_data.contact.name
		assert len(loaded.experience) == len(sample_resume_data.experience)

	def test_load_nonexistent(self, tmp_path: Path) -> None:
		store = ResumeStore(data_dir=tmp_path)
		assert store.load_data() is None

	def test_save_and_load_variant(self, tmp_path: Path) -> None:
		store = ResumeStore(data_dir=tmp_path)
		variant = ResumeVariant(
			name="swe",
			experience_indices=[0, 1],
			project_indices=[0],
		)
		store.save_variant(variant)
		loaded = store.load_variant("swe")
		assert loaded is not None
		assert loaded.name == "swe"
		assert loaded.experience_indices == [0, 1]

	def test_list_variants(self, tmp_path: Path) -> None:
		store = ResumeStore(data_dir=tmp_path)
		store.save_variant(ResumeVariant(name="swe"))
		store.save_variant(ResumeVariant(name="ml"))
		names = store.list_variants()
		assert "ml" in names
		assert "swe" in names

	def test_delete_variant(self, tmp_path: Path) -> None:
		store = ResumeStore(data_dir=tmp_path)
		store.save_variant(ResumeVariant(name="temp"))
		assert store.delete_variant("temp") is True
		assert store.load_variant("temp") is None
		assert store.delete_variant("temp") is False

	def test_load_corrupted_data(self, tmp_path: Path) -> None:
		store = ResumeStore(data_dir=tmp_path)
		store.data_path.write_text("not valid json", encoding="utf-8")
		assert store.load_data() is None


# -- LaTeX Import Helpers --


class TestExtractItems:
	def test_single_item(self) -> None:
		block = r"    \resumeItem{Built a system}" + "\n"
		items = _extract_items(block)
		assert len(items) == 1
		assert items[0] == "Built a system"

	def test_multiple_items(self) -> None:
		block = (
			r"    \resumeItem{First bullet}" + "\n"
			r"    \resumeItem{Second bullet}" + "\n"
		)
		items = _extract_items(block)
		assert len(items) == 2

	def test_no_items(self) -> None:
		assert _extract_items("no items here") == []


class TestParseHeading:
	def test_full_heading(self) -> None:
		tex = r"""
\begin{center}
    \textbf{\Huge \scshape Danny Willow Liu} \\ \vspace{1pt}
    \small 510-876-2949 $|$ \href{mailto:dan@test.edu}{\underline{dan@test.edu}} $|$
    \href{https://www.linkedin.com/in/dwliu2}{\underline{linkedin.com/in/dwliu2}} $|$
    \href{https://github.com/dannywillowliu-uchi}{\underline{github.com/dannywillowliu-uchi}}
\end{center}
"""
		contact = _parse_heading(tex)
		assert contact.name == "Danny Willow Liu"
		assert contact.phone == "510-876-2949"
		assert contact.email == "dan@test.edu"
		assert "dwliu2" in contact.linkedin
		assert "dannywillowliu-uchi" in contact.github


class TestSplitSections:
	def test_splits_correctly(self) -> None:
		tex = r"""
\begin{center}
    Heading content
\end{center}

\section{Education}
Education content

\section{Experience}
Experience content
"""
		sections = _split_sections(tex)
		assert "_heading" in sections
		assert "Education" in sections
		assert "Experience" in sections
		assert "Education content" in sections["Education"]


class TestParseSkills:
	def test_parses_categories(self) -> None:
		tex = r"""
\begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{
     \textbf{Languages}{: Python, C, SQL, JavaScript} \\
     \textbf{Frameworks}{: Flask, PostgreSQL, PyTorch}
    }}
\end{itemize}
"""
		skills = _parse_skills(tex)
		assert len(skills) == 2
		assert skills[0].category == "Languages"
		assert "Python" in skills[0].skills
		assert skills[1].category == "Frameworks"


# -- Full Import --


class TestImportFromLatex:
	def test_import_swe_resume(self) -> None:
		"""Test importing Danny's actual SWE resume."""
		tex_path = Path(
			"/Users/dannyliu/personal_projects/resumes/latex-resume-mcp/resumes/resume_swe.tex"
		)
		if not tex_path.exists():
			pytest.skip("Danny's resume file not available")

		data = import_from_latex(tex_path)
		assert data.contact.name == "Danny Willow Liu"
		assert data.contact.phone == "510-876-2949"
		assert data.contact.email == "dannywillowliu@uchicago.edu"
		assert len(data.education) >= 1
		assert len(data.experience) >= 3
		assert len(data.projects) >= 3
		assert len(data.skills) >= 3
		assert len(data.publications) >= 1

	def test_import_nonexistent(self, tmp_path: Path) -> None:
		with pytest.raises(FileNotFoundError):
			import_from_latex(tmp_path / "nonexistent.tex")

	def test_import_minimal_tex(self, tmp_path: Path) -> None:
		"""Test importing a minimal resume."""
		tex = r"""
\documentclass[letterpaper,11pt]{article}
\begin{document}
\begin{center}
    \textbf{\Huge \scshape Test Person} \\ \vspace{1pt}
    \small 555-0100 $|$ \href{mailto:test@example.com}{\underline{test@example.com}}
\end{center}

\section{Education}
  \resumeSubHeadingListStart
    \resumeSubheading
      {MIT}{Cambridge, MA}
      {BS Computer Science}{May 2025}
  \resumeSubHeadingListEnd

\section{Experience}
  \resumeSubHeadingListStart
    \resumeSubheading
      {Google}{Mountain View, CA}
      {Software Engineer}{2024 -- 2025}
      \resumeItemListStart
        \resumeItem{Built distributed systems}
        \resumeItem{Improved latency by 40\%}
      \resumeItemListEnd
  \resumeSubHeadingListEnd

\section{Technical Skills}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{
     \textbf{Languages}{: Python, Go, Java}
    }}
 \end{itemize}

\end{document}
"""
		tex_path = tmp_path / "test.tex"
		tex_path.write_text(tex, encoding="utf-8")

		data = import_from_latex(tex_path)
		assert data.contact.name == "Test Person"
		assert data.contact.phone == "555-0100"
		assert len(data.education) == 1
		assert data.education[0].institution == "MIT"
		assert len(data.experience) == 1
		assert data.experience[0].company == "Google"
		assert len(data.experience[0].bullets) == 2
		assert len(data.skills) == 1
		assert "Python" in data.skills[0].skills
