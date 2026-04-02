# Deployment — MCPX Docker Setup

## Architecture

MCPX is an MCP gateway/proxy from Lunar.dev that runs in Docker. It is **middleware** between AI clients (Kiro, Claude, Cursor) and MCP servers.

### How it works
1. MCPX runs in Docker as a privileged container
2. MCP servers are launched as subprocesses INSIDE Docker via `stdio` transport
3. When `mcp.json` says `"command": "uvx"`, MCPX runs `uvx <package>` inside the Docker container
4. MCPX exposes a single HTTP endpoint (port 9000) that AI clients connect to via `mcp-remote`

### Key implication
- MCPs run INSIDE Docker — they can only access **volume-mounted** paths
- Environment variables in `mcp.json` refer to paths inside Docker

---

## Docker Container

### Volume Mounts
```
/Users/JSR34/mcpx-config     → /lunar/packages/mcpx-server/config
/Users/JSR34/resumes          → /Users/JSR34/resumes
/Users/JSR34/resume-templates → /Users/JSR34/resume-templates
```

### Docker Run Command
```bash
docker run -d --pull always --privileged \
  -v /Users/JSR34/mcpx-config:/lunar/packages/mcpx-server/config \
  -v /Users/JSR34/resumes:/Users/JSR34/resumes \
  -v /Users/JSR34/resume-templates:/Users/JSR34/resume-templates \
  -p 9000:9000 -p 5173:5173 -p 3000:3000 \
  --name mcpx \
  us-central1-docker.pkg.dev/prj-common-442813/mcpx/mcpx:latest
```

---

## mcp.json — resume-forge entry

```json
"resume-forge": {
  "type": "stdio",
  "command": "uvx",
  "args": ["resume-forge-mcp==0.4.0"],
  "env": {
    "RESUME_DATA_DIR": "/Users/JSR34/resumes/data",
    "RESUME_TEMPLATE_DIR": "/Users/JSR34/resumes/templates",
    "RESUME_OUTPUT_DIR": "/Users/JSR34/resumes/output"
  }
}
```

### Environment Variables

| Env Var | Path (inside Docker) | Purpose |
|---------|---------------------|---------|
| `RESUME_DATA_DIR` | `/Users/JSR34/resumes/data` | Resume data JSON |
| `RESUME_TEMPLATE_DIR` | `/Users/JSR34/resumes/templates` | Fetched Overleaf templates |
| `RESUME_OUTPUT_DIR` | `/Users/JSR34/resumes/output` | Generated .tex and .pdf |

---

## Connecting Clients

```json
{
  "mcpServers": {
    "mcpx": {
      "command": "npx",
      "args": ["mcp-remote@0.1.21", "http://localhost:9000/mcp", "--header", "x-lunar-consumer-tag: Kiro"]
    }
  }
}
```

**IMPORTANT**: Restarting MCPX breaks client connections. Restart Kiro after any Docker restart.

---

## Known Limitations

- `pdflatex` is NOT available inside the MCPX Docker container
- `compile_and_preview` will fail — compile locally on host or install texlive in Docker
