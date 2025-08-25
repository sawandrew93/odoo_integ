#!/bin/bash

# HTTPS Setup with Let's Encrypt for AI Middleware
# Run this script on your Ubuntu server

DOMAIN="your-domain.com"  # Change this to your domain
EMAIL="your-email@example.com"  # Change this to your email

echo "🚀 Setting up HTTPS with Let's Encrypt for $DOMAIN"

# Install Nginx and Certbot
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/ai-middleware << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/ai-middleware /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive

# Create systemd service for the middleware
sudo tee /etc/systemd/system/ai-middleware.service << EOF
[Unit]
Description=AI Middleware for Odoo Live Chat
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/odoo_integ/ai_middleware
Environment=PATH=/home/ubuntu/odoo_integ/ai_middleware/venv/bin
ExecStart=/home/ubuntu/odoo_integ/ai_middleware/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable ai-middleware
sudo systemctl start ai-middleware

echo "✅ HTTPS setup complete!"
echo "Your AI middleware is now available at: https://$DOMAIN"
echo "Widget URL: https://$DOMAIN/widget.js"