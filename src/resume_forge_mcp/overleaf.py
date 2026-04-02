"""Overleaf gallery browser and template fetcher."""

from __future__ import annotations

import html as html_mod
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
GALLERY_BASE = "https://www.overleaf.com/latex/templates/tagged"
TEMPLATE_BASE = "https://www.overleaf.com/latex/templates"


def _fetch_page(url: str) -> str:
    """Fetch a URL and return the HTML content."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=15).read().decode("utf-8")


def browse_gallery(tag: str = "cv", page: int = 1) -> list[dict[str, str]]:
    """Browse Overleaf template gallery and return template listings.

    Args:
        tag: Gallery tag to browse (cv, cover-letter, report, etc.)
        page: Page number (1-indexed). Each page has ~10 templates.

    Returns:
        List of dicts with name, id, url for each template.
    """
    url = f"{GALLERY_BASE}/{tag}" if page == 1 else f"{GALLERY_BASE}/{tag}/page/{page}"
    html_content = _fetch_page(url)

    # Extract template links: /latex/templates/{slug}/{12-char-id}
    pattern = r"/latex/templates/([a-z0-9-]+)/([a-z]{12})"
    matches = re.findall(pattern, html_content)

    seen: set[str] = set()
    templates: list[dict[str, str]] = []
    for slug, tid in matches:
        if tid not in seen and slug != "tagged":
            seen.add(tid)
            name = slug.replace("-", " ").title()
            templates.append({
                "name": name,
                "id": tid,
                "slug": slug,
                "url": f"{TEMPLATE_BASE}/{slug}/{tid}",
            })

    # Try to extract total page count
    page_matches = re.findall(r"/page/(\d+)", html_content)
    max_page = max((int(p) for p in page_matches), default=1)

    return templates


def get_gallery_page_count(tag: str = "cv") -> int:
    """Get total number of pages in a gallery tag."""
    html_content = _fetch_page(f"{GALLERY_BASE}/{tag}")
    page_matches = re.findall(r"/page/(\d+)", html_content)
    return max((int(p) for p in page_matches), default=1)


def fetch_template_source(template_url: str) -> dict[str, Any]:
    """Fetch LaTeX source code from an Overleaf template page.

    Args:
        template_url: Full URL like https://www.overleaf.com/latex/templates/slug/id

    Returns:
        Dict with name, source (LaTeX code), url, and success status.
    """
    html_content = _fetch_page(template_url)

    # Extract template name from <title> or <h1>
    title_match = re.search(r"<title>([^<]+)</title>", html_content)
    name = title_match.group(1).strip() if title_match else "Unknown Template"
    # Clean up title
    name = name.replace(" - Overleaf, Online LaTeX Editor", "").strip()
    name = name.replace("LaTeX Template on Overleaf", "").strip()
    if not name:
        # Fallback: extract from URL
        slug_match = re.search(r"/templates/([^/]+)/", template_url)
        name = slug_match.group(1).replace("-", " ").title() if slug_match else "Unknown"

    # Extract LaTeX source - it's embedded in the page HTML
    source_match = re.search(
        r"\\documentclass.*?\\end\{document\}", html_content, re.DOTALL
    )

    if not source_match:
        return {
            "success": False,
            "name": name,
            "url": template_url,
            "error": "Could not extract LaTeX source from page",
        }

    # Decode the source: unescape HTML entities and fix backslashes
    raw = source_match.group()
    source = raw.replace("\\\\", chr(92))
    source = html_mod.unescape(source)

    return {
        "success": True,
        "name": name,
        "url": template_url,
        "source": source,
        "source_length": len(source),
    }


def save_template_locally(
    template_url: str, templates_dir: Path, filename: str | None = None
) -> dict[str, Any]:
    """Fetch a template from Overleaf and save it locally.

    Args:
        template_url: Overleaf template URL.
        templates_dir: Directory to save the template.
        filename: Optional filename (without extension). Auto-generated from URL if None.

    Returns:
        Dict with save status and file path.
    """
    result = fetch_template_source(template_url)

    if not result["success"]:
        return result

    if filename is None:
        # Extract slug from URL
        slug_match = re.search(r"/templates/([^/]+)/", template_url)
        filename = slug_match.group(1) if slug_match else "overleaf_template"

    try:
        templates_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    filepath = templates_dir / f"{filename}.tex"
    filepath.write_text(result["source"], encoding="utf-8")

    return {
        "success": True,
        "name": result["name"],
        "saved_to": str(filepath),
        "source_length": result["source_length"],
    }
