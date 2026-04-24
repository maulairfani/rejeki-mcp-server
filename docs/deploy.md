# Deployment Guide

Step-by-step guide to deploying Envel MCP on a fresh Ubuntu VPS.

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Server Setup](#2-server-setup)
3. [Clone & Install](#3-clone--install)
4. [Environment Configuration](#4-environment-configuration)
5. [Create Users](#5-create-users)
6. [Build Frontend](#6-build-frontend)
7. [Systemd Services](#7-systemd-services)
8. [Nginx Configuration](#8-nginx-configuration)
9. [TLS with Certbot](#9-tls-with-certbot)
10. [Google OAuth Setup](#10-google-oauth-setup)
11. [Verification Checklist](#11-verification-checklist)
12. [Updating](#12-updating)

---

## 1. Prerequisites

**Server**
- Ubuntu 22.04 LTS (or 24.04)
- 1 vCPU, 1 GB RAM minimum
- Domain with two subdomains pointed to the server's IP:
  - `envel.dev` (or your root domain)
  - `platform.envel.dev`

**DNS records (A)**

| Name | Value |
|---|---|
| `envel.dev` | `<server-ip>` |
| `platform.envel.dev` | `<server-ip>` |

---

## 2. Server Setup

```bash
apt update && apt upgrade -y
apt install -y python3.11 python3.11-venv python3-pip nginx certbot python3-certbot-nginx curl git
```

Verify Python version:

```bash
python3.11 --version  # should print Python 3.11.x
```

---

## 3. Clone & Install

```bash
cd /opt
git clone https://github.com/maulairfani/envel-mcp.git
cd envel-mcp

# Install all Python packages
pip install -e apps/mcp-server
pip install -e apps/auth-server
pip install -e apps/platform/server
```

Verify the CLI entrypoints are available:

```bash
which envel        # /usr/local/bin/envel
which envel-auth   # /usr/local/bin/envel-auth
which envel-platform
```

---

## 4. Environment Configuration

Copy the example file and fill in your values:

```bash
cp .env.example .env
nano .env
```

Minimum required values for production:

```env
# ── Shared ────────────────────────────────────────────────────────────────────
USERS_DB=/opt/envel-mcp/users.db

# ── MCP Server ───────────────────────────────────────────────────────────────
MCP_BASE_URL=https://envel.dev/mcp
INTROSPECT_URL=http://127.0.0.1:9004/introspect
PORT=8001

# ── Auth Server ───────────────────────────────────────────────────────────────
AS_BASE_URL=https://envel.dev/auth
AUTH_PORT=9004
PLATFORM_URL=https://platform.envel.dev
PLATFORM_SERVICE_SECRET=<generate with: openssl rand -hex 32>

# Google OAuth — fill after step 10
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# ── Platform ──────────────────────────────────────────────────────────────────
PLATFORM_PORT=8002
SESSION_SECRET=<generate with: openssl rand -hex 32>
SESSION_COOKIE_DOMAIN=.envel.dev
SECURE_COOKIES=true
FORCE_HTTPS=true
CORS_ORIGINS=https://platform.envel.dev
AUTH_SERVER_URL=https://envel.dev/auth

# ── Chat Agent ────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY=sk-or-...
```

Generate secrets:

```bash
openssl rand -hex 32   # run twice: once for PLATFORM_SERVICE_SECRET, once for SESSION_SECRET
```

Set correct file permissions:

```bash
chmod 600 .env
```

---

## 5. Create Users

```bash
mkdir -p /opt/envel-mcp/users

# python scripts/add_user.py <username> <password> [--db-path <path>]
python scripts/add_user.py alice strongpassword --db-path /opt/envel-mcp/users/alice.db
```

Each user gets their own isolated SQLite database at the path you specify. You can add more users at any time — no restart needed.

---

## 6. Build Frontend

```bash
cd /opt/envel-mcp/apps/platform/web
npm install
npm run build
# Output: apps/platform/web/dist/
```

The platform backend serves this `dist/` folder as static files. No separate static file server needed.

> Re-run this step after each `git pull` that includes frontend changes.

---

## 7. Systemd Services

Create one service file per process.

### Auth Server

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
WorkingDirectory=/opt/envel-mcp
EnvironmentFile=/opt/envel-mcp/.env
ExecStart=envel-auth
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### MCP Server

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
WorkingDirectory=/opt/envel-mcp
EnvironmentFile=/opt/envel-mcp/.env
ExecStart=envel
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Platform Server

```bash
nano /etc/systemd/system/envel-platform.service
```

```ini
[Unit]
Description=Envel Platform Server
After=network.target envel-auth.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/envel-mcp
EnvironmentFile=/opt/envel-mcp/.env
ExecStart=envel-platform
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Enable and start all services

```bash
systemctl daemon-reload
systemctl enable envel-auth envel-mcp envel-platform
systemctl start envel-auth envel-mcp envel-platform

# Verify all three are running
systemctl status envel-auth envel-mcp envel-platform
```

---

## 8. Nginx Configuration

Create a config file for each domain.

### envel.dev (MCP + Auth + Marketing)

```bash
nano /etc/nginx/sites-available/envel.dev
```

```nginx
server {
    listen 80;
    server_name envel.dev;

    # Marketing site (static)
    root /opt/envel-mcp/apps/marketing/dist;
    index index.html;

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

    # OAuth discovery (required by MCP clients)
    location /.well-known/oauth-protected-resource {
        proxy_pass http://127.0.0.1:8001/mcp/.well-known/oauth-protected-resource;
        proxy_set_header Host $http_host;
    }

    # SPA fallback for marketing site
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### platform.envel.dev

```bash
nano /etc/nginx/sites-available/platform.envel.dev
```

```nginx
server {
    listen 80;
    server_name platform.envel.dev;

    location / {
        proxy_pass http://127.0.0.1:8002/;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Enable sites and reload

```bash
ln -s /etc/nginx/sites-available/envel.dev /etc/nginx/sites-enabled/
ln -s /etc/nginx/sites-available/platform.envel.dev /etc/nginx/sites-enabled/

nginx -t && systemctl reload nginx
```

---

## 9. TLS with Certbot

```bash
certbot --nginx -d envel.dev -d platform.envel.dev
```

Certbot will automatically update both Nginx config files with TLS settings and set up auto-renewal.

Verify renewal works:

```bash
certbot renew --dry-run
```

After this step, your services are reachable at:

| URL | Service |
|---|---|
| `https://envel.dev` | Marketing site |
| `https://envel.dev/mcp/` | MCP Server |
| `https://envel.dev/auth/` | Auth Server |
| `https://platform.envel.dev` | Platform dashboard |

---

## 10. Google OAuth Setup

Skip this step if you only use password-based login.

### Create OAuth credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Add these **Authorized redirect URIs**:
   ```
   https://envel.dev/auth/google/callback
   https://envel.dev/auth/platform/google/callback
   ```
5. Copy **Client ID** and **Client Secret**

### Update .env

```env
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>
```

### Restart auth server

```bash
systemctl restart envel-auth
```

---

## 11. Verification Checklist

Run these checks after deployment.

```bash
# MCP server health
curl https://envel.dev/mcp/health

# Auth server — should return 400 (missing token), not 502
curl -X POST https://envel.dev/auth/introspect

# Platform — should return 200 or redirect to login
curl -I https://platform.envel.dev

# Check all services are running
systemctl status envel-auth envel-mcp envel-platform

# Check logs for errors
journalctl -u envel-mcp --since "5 minutes ago"
journalctl -u envel-auth --since "5 minutes ago"
journalctl -u envel-platform --since "5 minutes ago"
```

**MCP client test:**
1. Open Claude → **Settings → Integrations → Add**
2. URL: `https://envel.dev/mcp/`
3. Log in with a user created in step 5
4. Ask Claude: *"What's my ready-to-assign balance?"*

---

## 12. Updating

```bash
cd /opt/envel-mcp
git pull

# Reinstall Python packages (picks up any dependency changes)
pip install -e apps/mcp-server
pip install -e apps/auth-server
pip install -e apps/platform/server

# Rebuild frontend if web files changed
cd apps/platform/web && npm install && npm run build && cd /opt/envel-mcp

# Restart services
systemctl restart envel-auth envel-mcp envel-platform
```

Check everything came back up:

```bash
systemctl status envel-auth envel-mcp envel-platform
curl https://envel.dev/mcp/health
```
