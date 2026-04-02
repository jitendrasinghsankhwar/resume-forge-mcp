# Publish & Version History

## Publish Cycle

```bash
# 1. Bump version in pyproject.toml

# 2. Build and publish
source ~/.bash_profile   # ⚠️ REQUIRED — loads $PYPI_TOKEN
cd ~/resume-forge-mcp && rm -rf dist/ && uv build && uv publish --token "$PYPI_TOKEN"

# 3. Wait for PyPI to propagate
sleep 30

# 4. Update version pin in mcp.json
#    Edit /Users/JSR34/mcpx-config/mcp.json — change resume-forge-mcp==X.Y.Z

# 5. Clear Docker uv cache
docker exec mcpx sh -c 'rm -rf /lunar/.cache/uv/wheels-v5/pypi/resume-forge-mcp && rm -rf /lunar/.cache/uv/tools/resume-forge-mcp*'

# 6. Fix cache permissions
docker exec mcpx sh -c 'chmod -R 777 /lunar/.cache/uv/'

# 7. Restart MCPX
docker restart mcpx

# 8. Restart Kiro (Docker restart breaks MCP connections)
```

### ⚠️ Gotchas
- `$PYPI_TOKEN` is in `~/.bash_profile`, NOT `~/.zshrc` — always `source ~/.bash_profile` first
- Docker uv cache is at `/lunar/.cache/uv/`, NOT `/root/.cache/uv/` — must use `rm -rf` on `/lunar/` paths
- See TROUBLESHOOTING.md for details

---

## Version History

### v0.4.0 (Apr 1 2026) — In Development

**Major refactor: 22 tools → 11 tools**

**New features:**
- 3 built-in Jinja2 templates: `modern`, `classic`, `minimal`
- `list_templates` tool — shows built-in templates + Overleaf integration
- `import_resume` tool — unified import from .tex, .pdf, .docx (PDF/DOCX parsers TODO)
- `generate_resume` and `generate_tailored_resume` accept `template_name` parameter
- `compile_and_preview` can compile from .tex file or generate+compile from data
- 3 separate env vars: `RESUME_DATA_DIR`, `RESUME_TEMPLATE_DIR`, `RESUME_OUTPUT_DIR`

**Bug fixes:**
- Skills `\item` artifact: Pattern 2 lookahead now includes `\\item` to stop before it
- Pattern 3 cleanup: `$` → `\Z` for absolute end-of-string matching

**Dropped tools:**
- `import_from_latex_file` → merged into `import_resume`
- `compile_resume_tex` / `preview_resume` → merged into `compile_and_preview`
- `assess_quality` → merged into `score_resume_quality`
- `parse_job_description_text` / `preview_content_selection` → internal to `generate_tailored_resume`
- `save_variant` / `get_variant` / `list_variants` → removed
- `get_work_history` / `get_work_history_report` / `search_accomplishments_for_resume` → removed

**Files changed:**
- `src/resume_forge_mcp/server.py` — full rewrite
- `src/resume_forge_mcp/templates/engine.py` — `BUILTIN_TEMPLATES` dict, template selection
- `src/resume_forge_mcp/templates/modern.tex.j2` — new
- `src/resume_forge_mcp/templates/classic.tex.j2` — new
- `src/resume_forge_mcp/templates/minimal.tex.j2` — new
- `src/resume_forge_mcp/storage/tex_import.py` — skills `\item` bug fix

### v0.3.8 (Apr 1 2026)

**Fixes:**
1. `update_resume_data` — accepts `str | dict` for `data` param (MCP SDK auto-deserializes)
2. Skills `\item` artifact — added `re.sub` to strip trailing `\item` (incomplete fix, fully fixed in v0.4.0)

### v0.3.7 (Apr 1 2026)

**Fixes:**
1. Contact info parsing — handles `\LARGE\bfseries`, `\href{...}{Label}` formats
2. Skills parsing — 3 patterns: Jake's template, colon-inside-bold, list-item format
3. Skills section name — matches both `"Technical Skills"` and `"Skills"`
4. `update_resume_data` — added `section="contact"` support with partial updates

### v0.3.5 (Mar 31 2026)
- First working version deployed via MCPX
- 21 tools available
