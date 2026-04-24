# Envel MCP

> AI-powered envelope budgeting — every rupiah has a job.

An MCP (Model Context Protocol) server that brings personal finance management into any MCP-compatible AI client (Claude, Cursor, etc.). Built on [FastMCP](https://github.com/jlowin/fastmcp) with per-user SQLite isolation and OAuth 2.1 authentication.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#license)

---

## Features

- **Envelope budgeting** — assign every rupiah to a category before you spend it
- **Multi-account tracking** — bank accounts, e-wallets, and cash in one place
- **Scheduled transactions** — recurring income and expenses handled automatically
- **Budget analytics** — ready-to-assign balance, age of money, monthly summaries
- **Wishlist** — track items you're saving toward
- **Platform dashboard** — React web UI for visual budget management
- **Per-user isolation** — each user gets their own SQLite database
- **Any MCP client** — works with Claude, Cursor, or any MCP-compatible client

---

## Repository Structure

```
apps/
├── mcp-server/       FastMCP server — tools & prompts (port 8001)
├── auth-server/      OAuth 2.1 authentication server (port 9004)
├── platform/
│   ├── server/       FastAPI REST API backend (port 8002)
│   └── web/          React + TypeScript frontend (Vite, Shadcn/ui)
└── marketing/        Marketing site (React + Vite)
scripts/
└── add_user.py       User management CLI
```

---

## Architecture

```
MCP Client (Claude, Cursor, etc.)
   │
   ▼ HTTPS
Nginx (reverse proxy)
   ├── /mcp/    → MCP Server   (port 8001)
   └── /auth/   → Auth Server  (port 9004)

Browser
   ├── envel.dev           → Marketing site (static)
   └── platform.envel.dev  → Platform dashboard (port 8002)
```

**Request flow:**
1. MCP client sends a request with a bearer token.
2. MCP server calls the auth server's `/introspect` endpoint to resolve the token → user DB path.
3. All tools read/write to that user's isolated SQLite file.

---

## Getting Started (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 18+ (for the platform frontend)

### 1. Clone and install

```bash
git clone https://github.com/maulairfani/envel-mcp.git
cd envel-mcp
pip install -e apps/mcp-server
pip install -e apps/auth-server
pip install -e apps/platform/server
```

### 2. Configure environment

Create a `.env` file in the project root. For local development, two variables are enough — no auth server required:

```env
TEST_TOKEN=any-secret-token
TEST_DB=./users/test.db
```

### 3. Start the servers

```bash
# MCP server — http://localhost:8001
envel

# Auth server — http://localhost:9004 (optional for dev)
envel-auth

# Platform API — http://localhost:8002
envel-platform
```

Verify the MCP server is up:

```bash
curl http://localhost:8001/health
```

### 4. Connect to your MCP client

Add to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "envel": {
      "url": "http://localhost:8001/mcp/",
      "headers": {
        "Authorization": "Bearer any-secret-token"
      }
    }
  }
}
```

Or use [MCP Inspector](https://github.com/modelcontextprotocol/inspector) for quick testing.

### 5. Platform frontend (optional)

```bash
cd apps/platform/web
npm install
npm run dev   # http://localhost:5173 — proxies /api to port 8002
```

---

## Production Deployment (VPS)

### Prerequisites

- Ubuntu 22.04+
- Python 3.11+
- Nginx + Certbot (TLS)
- Domain with DNS pointed to your VPS

### 1. Clone and install

```bash
cd /opt
git clone https://github.com/maulairfani/envel-mcp.git
cd envel-mcp
pip install -e apps/mcp-server
pip install -e apps/auth-server
pip install -e apps/platform/server
```

### 2. Create users

```bash
mkdir -p users
python scripts/add_user.py alice strongpassword --db-path /opt/envel-mcp/users/alice.db
```

This creates `users.db` with a bcrypt-hashed password entry.

### 3. Configure environment

```env
MCP_BASE_URL=https://your-domain.com/mcp
AS_BASE_URL=https://your-domain.com/auth
INTROSPECT_URL=http://127.0.0.1:9004/introspect
USERS_DB=/opt/envel-mcp/users.db
PORT=8001
AUTH_PORT=9004
```

> `USERS_DB` has no default — it must be set explicitly.

### 4. Create systemd services

**`/etc/systemd/system/envel-auth.service`**

```ini
[Unit]
Description=Envel Auth Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/envel-mcp
EnvironmentFile=/opt/envel-mcp/.env
ExecStart=envel-auth
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/envel-mcp.service`**

```ini
[Unit]
Description=Envel MCP Server
After=network.target envel-auth.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/envel-mcp
EnvironmentFile=/opt/envel-mcp/.env
ExecStart=envel
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable envel-auth envel-mcp
systemctl start envel-auth envel-mcp
systemctl status envel-auth envel-mcp
```

### 5. Configure Nginx

Inside your `server { ... }` block:

```nginx
# MCP Server
location /mcp/ {
    proxy_pass http://127.0.0.1:8001/mcp/;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Authorization $http_authorization;
    proxy_set_header Mcp-Session-Id $http_mcp_session_id;
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 600s;
    add_header Access-Control-Expose-Headers "Mcp-Session-Id";
}

# Auth Server
location /auth/ {
    proxy_pass http://127.0.0.1:9004/;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# OAuth discovery (required by some MCP clients)
location /.well-known/oauth-protected-resource {
    proxy_pass http://127.0.0.1:8001/mcp/.well-known/oauth-protected-resource;
    proxy_set_header Host $http_host;
}
```

```bash
nginx -t && systemctl reload nginx
```

### 6. Add to MCP client

1. Open your MCP client settings (e.g. **Claude → Settings → Integrations → Add**)
2. Server URL: `https://your-domain.com/mcp/`
3. Log in with the username and password you created in step 2.

---

## Configuration Reference

| Variable | Required | Description |
|---|---|---|
| `TEST_TOKEN` | Dev only | Accepts any request with this token; bypasses auth server |
| `TEST_DB` | Dev only | SQLite DB path used with `TEST_TOKEN` |
| `MCP_BASE_URL` | Production | Public URL of the MCP server |
| `AS_BASE_URL` | Production | Public URL of the auth server |
| `INTROSPECT_URL` | Production | Internal introspect endpoint, e.g. `http://127.0.0.1:9004/introspect` |
| `USERS_DB` | Production | Absolute path to `users.db` |
| `PORT` | Optional | MCP server port (default: `8001`) |
| `AUTH_PORT` | Optional | Auth server port (default: `9004`) |

---

## User Management

```bash
# Add a user (default db path: ./users/<username>.db)
python scripts/add_user.py <username> <password>

# Add a user with a custom db path
python scripts/add_user.py <username> <password> --db-path /path/to/<username>.db
```

Changes take effect immediately — no service restart needed.

---

## Updating

```bash
cd /opt/envel-mcp
git pull
pip install -e apps/mcp-server
pip install -e apps/auth-server
systemctl restart envel-auth envel-mcp
```

---

## Troubleshooting

```bash
# Live logs
journalctl -u envel-mcp -f
journalctl -u envel-auth -f

# Service status
systemctl status envel-mcp envel-auth

# Direct endpoint checks (bypasses Nginx)
curl http://localhost:8001/health
curl -X POST http://localhost:9004/introspect -d "token=<your-token>"
```

---

## License

MIT
