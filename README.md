# Finance MCP Server

AI-powered personal finance agent built with the MCP SDK and SQLite. Implements envelope budgeting — every rupiah has a job.

Designed to be used with **any MCP client** (Claude, Cursor, etc.) as an MCP integration.

---

## Architecture

```
MCP Client (Claude, Cursor, etc.)
   │
   ▼ HTTPS
Nginx (reverse proxy)
   ├── /envel/mcp/   → MCP Server  (port 8001)
   └── /envel/auth/  → Auth Server (port 9004)
```

Monorepo with three apps in the `apps/` folder:

- **`apps/mcp-server/`** — FastMCP server; tools for transactions, envelopes, accounts
- **`apps/auth-server/`** — OAuth 2.1 with login form backed by `users.json`
- **`apps/platform/`** — Financial data visualization dashboard (port 8002)

---

## Local Setup (Development)

### 1. Clone & install dependencies

```bash
git clone https://github.com/maulairfani/envel-mcp-server.git
cd envel-mcp-server
pip install -e apps/mcp-server
pip install -e apps/auth-server
pip install -e apps/platform
```

### 2. Create `.env` file

```bash
cp .env.example .env
```

For local development, just set these two variables in `.env`:

```env
TEST_TOKEN=any-secret-token
TEST_DB=./users/test.db
```

### 3. Run servers

```bash
# MCP server (port 8001)
envel

# Auth server (port 9004) — optional for dev, just use TEST_TOKEN
envel-auth

# Platform dashboard (port 8002)
envel-platform
```

MCP server health check:

```bash
curl http://localhost:8001/health
```

Platform dashboard: open `http://localhost:8002` in your browser, log in with credentials from `users.db`.

### 4. Connect to MCP client (local)

Use MCP Inspector or add to your MCP client config with `TEST_TOKEN`.

---

## VPS Setup

### Prerequisites

- Ubuntu 22.04+
- Python 3.11+
- Nginx + Certbot (TLS)
- Domain with DNS pointing to VPS

### 1. Clone repo & install

```bash
cd /root
git clone https://github.com/maulairfani/envel-mcp-server.git
cd envel-mcp-server
pip install -e apps/mcp-server
pip install -e apps/auth-server
```

### 2. Create users

```bash
mkdir -p users
python scripts/add_user.py irfani your-password --db-path /root/envel-mcp-server/users/irfani.db
```

This creates `users.db` with bcrypt-hashed credentials.

### 3. Create `.env` file

```bash
cp .env.example .env
```

Fill `.env` with your domain:

```env
MCP_BASE_URL=https://your-domain.com/envel/mcp
AS_BASE_URL=https://your-domain.com/envel/auth
INTROSPECT_URL=http://127.0.0.1:9004/introspect
USERS_DB=/root/envel-mcp-server/users.db
PORT=8001
AUTH_PORT=9004
```

> `USERS_DB` must be set explicitly — there is no default fallback.

### 4. Create systemd service for Auth Server

```bash
nano /etc/systemd/system/envel-auth.service
```

```ini
[Unit]
Description=Envel Auth Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/envel-mcp-server
EnvironmentFile=/root/envel-mcp-server/.env
ExecStart=envel-auth
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 5. Create systemd service for MCP Server

```bash
nano /etc/systemd/system/envel-mcp.service
```

```ini
[Unit]
Description=Envel MCP Server
After=network.target envel-auth.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/envel-mcp-server
EnvironmentFile=/root/envel-mcp-server/.env
ExecStart=envel
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6. Enable & start services

```bash
systemctl daemon-reload
systemctl enable envel-auth envel-mcp
systemctl start envel-auth envel-mcp

# Check status
systemctl status envel-auth
systemctl status envel-mcp
```

### 7. Configure Nginx

Add the following block inside your `server { ... }` in Nginx config (usually `/etc/nginx/sites-enabled/default`):

```nginx
# MCP Server
location /envel/mcp/ {
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
location /envel/auth/ {
    proxy_pass http://127.0.0.1:9004/;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# OAuth discovery (required by MCP clients)
location /.well-known/oauth-protected-resource/envel {
    proxy_pass http://127.0.0.1:8001/mcp/.well-known/oauth-protected-resource;
    proxy_set_header Host $http_host;
}
```

Test and reload Nginx:

```bash
nginx -t && systemctl reload nginx
```

### 8. Add to MCP client

1. Open your MCP client settings (e.g., **claude.ai → Settings → Integrations → Add**)
2. Enter URL: `https://your-domain.com/envel/mcp/`
3. Log in with username & password from `users.json`

---

## User Management

### Add a new user

```bash
python scripts/add_user.py new_username their-password
```

This hashes the password with bcrypt and stores it in `users.db`. Default db_path: `./users/<username>.db`.

To specify a custom db path:

```bash
python scripts/add_user.py new_username their-password --db-path /path/to/new_username.db
```

> Changes take effect immediately without restarting services.

---

## Update Deployment

```bash
cd /root/envel-mcp-server
git pull
pip install -e apps/mcp-server
pip install -e apps/auth-server
systemctl restart envel-auth envel-mcp
```

---

## Troubleshooting

```bash
# View realtime logs
journalctl -u envel-mcp -f
journalctl -u envel-auth -f

# Check if services are running
systemctl status envel-mcp envel-auth

# Test endpoints directly (bypass Nginx)
curl http://localhost:8001/health
curl -X POST http://localhost:9004/introspect -d "token=test"
```
