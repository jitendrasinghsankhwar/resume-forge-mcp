# Troubleshooting

## Issue: MCPX keeps launching old version after PyPI update

### Symptoms
- You published a new version (e.g., 0.3.7) and updated `mcp.json`
- MCPX logs show it still launching the old version (e.g., 0.3.5)
- Or logs show: `Because there is no version of resume-forge-mcp==0.3.7`
- Or logs show: `Permission denied (os error 13) at path "/lunar/.cache/uv/wheels-v5/pypi/resume-forge-mcp/..."`

### Root Cause
MCPX uses a uv cache at `/lunar/.cache/uv/` (NOT `/root/.cache/uv/`). Two locations cache the old version:
- `/lunar/.cache/uv/wheels-v5/pypi/resume-forge-mcp` — cached wheel
- `/lunar/.cache/uv/tools/resume-forge-mcp*` — cached tool environment

Even after updating `mcp.json`, uvx resolves from cache and never checks PyPI for the new version. Additionally, clearing the cache can break directory permissions, causing `Permission denied` on subsequent installs.

### Fix
```bash
# 1. Clear BOTH cache locations
docker exec mcpx sh -c 'rm -rf /lunar/.cache/uv/wheels-v5/pypi/resume-forge-mcp && rm -rf /lunar/.cache/uv/tools/resume-forge-mcp*'

# 2. Fix permissions (clearing cache can break them)
docker exec mcpx sh -c 'chmod -R 777 /lunar/.cache/uv/'

# 3. Verify uvx can install the new version
docker exec mcpx sh -c 'uvx resume-forge-mcp==0.3.7 --help 2>&1'
# Should install without errors. "realpath: --: No such file or directory" is harmless.

# 4. Restart MCPX
docker restart mcpx

# 5. Wait ~10s, then check logs
docker logs mcpx 2>&1 | grep -i "resume-forge" | tail -5
# Look for: "STDIO client connected" with correct version and tools list
# Bad: "connection-failed" or "Permission denied"

# 6. Restart Kiro (Docker restart breaks MCP connections)
```

### Important
- The cache path is `/lunar/.cache/uv/`, NOT `/root/.cache/uv/`
- `uv cache clean resume-forge-mcp` clears `/root/.cache/uv/` which is the WRONG location
- You must use `rm -rf` on the `/lunar/` paths directly

---

## Issue: Permission denied on file operations

### Symptoms
- MCP tools fail with `Permission denied: '/Users/JSR34/resumes/...'`
- `docker exec mcpx ls /Users/JSR34/resumes/` also fails

### Root Cause
The Docker container doesn't have the host directory volume-mounted.

### Fix
Recreate the container with volume mounts:
```bash
docker stop mcpx && docker rm mcpx
docker run -d --pull always --privileged \
  -v /Users/JSR34/mcpx-config:/lunar/packages/mcpx-server/config \
  -v /Users/JSR34/resumes:/Users/JSR34/resumes \
  -v /Users/JSR34/resume-templates:/Users/JSR34/resume-templates \
  -p 9000:9000 -p 5173:5173 -p 3000:3000 \
  --name mcpx \
  us-central1-docker.pkg.dev/prj-common-442813/mcpx/mcpx:latest
```

### Verify
```bash
docker exec mcpx ls /Users/JSR34/resumes/
# Should list files
```

---

## Issue: `uv publish` fails with 403 Forbidden

### Symptoms
```
error: Failed to publish ... 403 Invalid or non-existent authentication information
```

### Root Cause
`$PYPI_TOKEN` is defined in `~/.bash_profile` but Kiro's shell doesn't auto-source it.

### Fix
```bash
source ~/.bash_profile
uv publish --token "$PYPI_TOKEN"
```

---

## Issue: Import parser doesn't extract contact/skills

### Symptoms
- `import_from_latex_file` returns `"name": "Unknown"`, empty phone/linkedin/github
- `"skill_categories": 0`

### Root Cause (fixed in v0.3.7)
The parser only handled Jake's Resume template format:
- Name: expected `\scshape` — your resume uses `\LARGE\bfseries`
- LinkedIn/GitHub: expected `\underline{linkedin.com...}` — your resume uses `\href{https://...}{Label}`
- Skills: expected `\textbf{Cat}{: skills}` — your resume uses `\textbf{Cat:} skills`
- Section name: expected `"Technical Skills"` — your resume uses `"Skills"`

### Fix
Upgrade to v0.3.7 which handles all these formats. Then re-import:
```
resumeforge__import_from_latex_file with path=/Users/JSR34/resumes/jitendra_sankhwar_resume.tex
```

---

## Issue: Company name truncated in import

### Symptoms
Company shows as `Medidata Solutions (Dassault Syst\`{e` instead of `Medidata Solutions (Dassault Systèmes)`

### Root Cause
The `_extract_subheadings` regex `\{([^}]*)\}` breaks on nested braces like `\`{e}mes)`. The `[^}]*` stops at the inner `}` of `\`{e}`.

### Status
NOT fixed — requires a brace-aware parser. Low priority.

### Workaround
Manually fix via `update_resume_data`:
```
section="experience", action="update", index=0, data='{"company":"Medidata Solutions (Dassault Systèmes)", ...}'
```

---

## Issue: MCPX Control Plane UI changes version back

### Symptoms
You set 0.3.7 in `mcp.json`, but logs show MCPX switching to a different version.

### Root Cause
The Control Plane UI at http://localhost:5173 allows editing server configs. If someone edits the resume-forge config there, it overrides `mcp.json` at runtime. On restart, `mcp.json` is re-read.

### Fix
After editing via UI, always restart: `docker restart mcpx`
Or just edit `mcp.json` directly and restart — don't use the UI for version changes.

---

## Issue: "Cannot connect to Hub: setupOwnerId is not provided"

### Symptoms
```
ERROR: Cannot connect to Hub: setupOwnerId is not provided component="HubService"
```

### Root Cause
This is the Lunar.dev cloud hub connection. It's NOT needed for local-only usage.

### Fix
Ignore it. All local MCP functionality works without the hub connection.
