# Deployment Instructions

## Quick Deploy to DigitalOcean

### 1. Create Droplet
- Ubuntu 22.04 LTS
- Basic Plan - $6/month
- 1GB RAM / 1 CPU

### 2. Connect to Server
```bash
ssh root@YOUR_DROPLET_IP
```

### 3. Install Dependencies
```bash
apt update && apt upgrade -y
apt install python3 python3-pip python3-venv nginx supervisor git -y
```

### 4. Deploy Application
```bash
mkdir -p /var/www/reddit-tracker
cd /var/www/reddit-tracker
git clone YOUR_REPO_URL .

python3 -m venv venv
source venv/bin/activate
pip install -r requirements_production.txt
```

### 5. Configure Environment
```bash
nano .env
```
Add your credentials from .env.example

### 6. Setup Gunicorn Service
```bash
nano /etc/supervisor/conf.d/reddit-tracker.conf
```

Paste:
```ini
[program:reddit-tracker]
directory=/var/www/reddit-tracker
command=/var/www/reddit-tracker/venv/bin/gunicorn app_production:app --workers 4 --bind 127.0.0.1:8000 --timeout 300
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/reddit-tracker.err.log
stdout_logfile=/var/log/reddit-tracker.out.log
environment=PATH="/var/www/reddit-tracker/venv/bin"
```

Start service:
```bash
supervisorctl reread
supervisorctl update
supervisorctl start reddit-tracker
```

### 7. Configure Nginx
```bash
nano /etc/nginx/sites-available/reddit-tracker
```

Paste:
```nginx
server {
    listen 80;
    server_name YOUR_IP_OR_DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

Enable:
```bash
ln -s /etc/nginx/sites-available/reddit-tracker /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

### 8. Configure Firewall
```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

### 9. Test
Open browser: http://YOUR_DROPLET_IP

Done! 🎉