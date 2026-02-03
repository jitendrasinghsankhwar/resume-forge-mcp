"""JSON file I/O for ResumeData and ResumeVariant."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from latex_resume_mcp.models.resume import ResumeData, ResumeVariant

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path.home() / ".latex-resume-mcp"
DATA_FILENAME = "resume_data.json"
VARIANTS_DIR = "variants"


class ResumeStore:
	"""Manages resume data and variants on disk as JSON files."""

	def __init__(self, data_dir: Path | None = None) -> None:
		self._data_dir = data_dir or DEFAULT_DATA_DIR
		self._data_dir.mkdir(parents=True, exist_ok=True)
		self._variants_dir = self._data_dir / VARIANTS_DIR
		self._variants_dir.mkdir(parents=True, exist_ok=True)

	@property
	def data_path(self) -> Path:
		return self._data_dir / DATA_FILENAME

	def load_data(self) -> ResumeData | None:
		"""Load master resume data from disk."""
		if not self.data_path.exists():
			return None
		try:
			text = self.data_path.read_text(encoding="utf-8")
			return ResumeData.model_validate_json(text)
		except (json.JSONDecodeError, ValueError):
			logger.exception("Failed to load resume data from %s", self.data_path)
			return None

	def save_data(self, data: ResumeData) -> None:
		"""Save master resume data to disk."""
		self.data_path.write_text(
			data.model_dump_json(indent=2),
			encoding="utf-8",
		)

	def list_variants(self) -> list[str]:
		"""List available variant names."""
		return sorted(
			p.stem for p in self._variants_dir.glob("*.json")
		)

	def load_variant(self, name: str) -> ResumeVariant | None:
		"""Load a variant by name."""
		path = self._variants_dir / f"{name}.json"
		if not path.exists():
			return None
		try:
			text = path.read_text(encoding="utf-8")
			return ResumeVariant.model_validate_json(text)
		except (json.JSONDecodeError, ValueError):
			logger.exception("Failed to load variant %s", name)
			return None

	def save_variant(self, variant: ResumeVariant) -> None:
		"""Save a variant to disk."""
		path = self._variants_dir / f"{variant.name}.json"
		path.write_text(
			variant.model_dump_json(indent=2),
			encoding="utf-8",
		)

	def delete_variant(self, name: str) -> bool:
		"""Delete a variant. Returns True if it existed."""
		path = self._variants_dir / f"{name}.json"
		if path.exists():
			path.unlink()
			return True
		return False
