#!/bin/bash

# Exit on error
set -e

APP_DIR="/var/www/simplii"
USER="ubuntu" # Default AWS user, change if using 'ec2-user' or 'admin'

echo "--- Starting Simplii Deployment ---"

# 1. Update System
echo "[1/7] Updating system packages..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv nginx git acl

# 2. Setup Directory
echo "[2/7] Setting up application directory at $APP_DIR..."
# Create directory if not exists
if [ ! -d "$APP_DIR" ]; then
    sudo mkdir -p $APP_DIR
fi

# Set permissions (allow current user to write)
sudo setfacl -R -m u:$USER:rwx $APP_DIR

# 3. Copy files (Assumes this script is run from the uploaded folder or files are already there)
# In this workflow, we assume files are uploaded to ~ and we copy them to /var/www
# OR we assume we are running INSIDE the repo and we just copy everything.
# Let's assume the user SCP'd the 'simplii' folder to ~/simplii and runs this script from there.

SOURCE_DIR=$(pwd)
if [ "$SOURCE_DIR" != "$APP_DIR" ]; then
    echo "Copying files from $SOURCE_DIR to $APP_DIR..."
    cp -r ./* $APP_DIR/
fi

cd $APP_DIR

# 4. Setup Virtual Environment
echo "[4/7] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "WARNING: requirements.txt not found!"
fi

# 5. Setup Systemd Service
echo "[5/7] Configuring Systemd Service..."
SERVICE_FILE="/etc/systemd/system/simplii.service"

# Generate service file content dynamically to ensure correct paths
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Simplii Automation Backend
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.server:app --bind 0.0.0.0:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable simplii
sudo systemctl restart simplii

# 6. Setup Nginx Reverse Proxy
echo "[6/7] Configuring Nginx..."
NGINX_CONF="/etc/nginx/sites-available/simplii"

sudo bash -c "cat > $NGINX_CONF" <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
if [ -f "/etc/nginx/sites-enabled/default" ]; then
    sudo rm /etc/nginx/sites-enabled/default
fi

if [ ! -f "/etc/nginx/sites-enabled/simplii" ]; then
    sudo ln -s $NGINX_CONF /etc/nginx/sites-enabled/simplii
fi

sudo systemctl restart nginx

echo "--- Deployment Complete! ---"
echo "Ensure your .env file is present in $APP_DIR"
echo "You can check status with: sudo systemctl status simplii"
