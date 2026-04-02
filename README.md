# Rejeki MCP Server

AI-powered personal finance agent built with FastMCP, SQLite, and WorkOS AuthKit.

## Deploy ke VPS

### Asumsi
- VPS Ubuntu 22.04+
- DNS `rejeki.maulairfani.my.id` sudah diarahkan ke IP VPS
- Akses SSH sebagai root atau user dengan sudo

### 1. Setup awal VPS

```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip nginx certbot python3-certbot-nginx git
```

### 2. Clone repo & install

```bash
cd /opt
sudo git clone https://github.com/maulairfani/rejeki-mcp-server.git rejeki
sudo chown -R $USER:$USER /opt/rejeki
cd /opt/rejeki

python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Buat `.env` produksi

```bash
mkdir -p /data/users

cat > /opt/rejeki/.env << 'EOF'
PLATFORM_DB_PATH=/data/platform.db
AUTHKIT_DOMAIN=https://intelligent-hedge-61-staging.authkit.app
BASE_URL=https://rejeki.maulairfani.my.id
EOF
```

### 4. Register user

Edit `scripts/add_user.py`, ganti `DB_PATH` ke `/data/users/irfani.db`, lalu:

```bash
cd /opt/rejeki
source .venv/bin/activate
python scripts/add_user.py
```

### 5. Systemd service

```bash
sudo nano /etc/systemd/system/rejeki.service
```

```ini
[Unit]
Description=Rejeki MCP Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/rejeki
EnvironmentFile=/opt/rejeki/.env
ExecStart=/opt/rejeki/.venv/bin/rejeki
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rejeki
sudo systemctl status rejeki
```

### 6. Nginx + HTTPS

```bash
sudo nano /etc/nginx/sites-available/rejeki
```

```nginx
server {
    listen 80;
    server_name rejeki.maulairfani.my.id;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection keep-alive;
        proxy_set_header Host $host;
        proxy_read_timeout 300s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/rejeki /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d rejeki.maulairfani.my.id
```

### 7. Update AuthKit callback URL

Di dashboard WorkOS, tambahkan redirect URI:
```
https://rejeki.maulairfani.my.id/mcp
```

### 8. Update Claude Desktop

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rejeki": {
      "command": "npx",
      "args": ["mcp-remote", "https://rejeki.maulairfani.my.id/mcp"]
    }
  }
}
```
