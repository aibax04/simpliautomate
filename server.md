[Unit]
Description=MyApp Web Application
After=network.target

[Service]
User=www-data
Group=www-data

WorkingDirectory=/var/www/myapp

Environment="PATH=/var/www/myapp/venv/bin"
EnvironmentFile=/var/www/myapp/.env

ExecStart=/var/www/myapp/venv/bin/uvicorn main:app \
    --host 0.0.0.0 \
    --port 35000 \
    --workers 2

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target




sudo systemctl daemon-reload
sudo systemctl enable myapp
sudo systemctl start myapp
