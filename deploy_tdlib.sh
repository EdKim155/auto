#!/bin/bash
# Deployment script for TDLib-based automation on server
# Usage: ./deploy_tdlib.sh

set -e  # Exit on error

echo "=================================="
echo "TDLib Automation Deployment"
echo "=================================="

# Configuration
SERVER="auto-server"
REMOTE_DIR="/root/auto"
BACKUP_DIR="/root/auto_backups"

echo ""
echo "[1/7] Creating backup on server..."
ssh $SERVER "mkdir -p $BACKUP_DIR && tar -czf $BACKUP_DIR/backup_\$(date +%Y%m%d_%H%M%S).tar.gz -C /root auto/ || true"

echo ""
echo "[2/7] Stopping current service..."
ssh $SERVER "systemctl stop telegram-bot.service || true"

echo ""
echo "[3/7] Uploading new files..."
# Upload new TDLib-based files
scp -r modules/ $SERVER:$REMOTE_DIR/
scp bot_automation_tdlib.py $SERVER:$REMOTE_DIR/
scp main_tdlib.py $SERVER:$REMOTE_DIR/
scp config_tdlib.py $SERVER:$REMOTE_DIR/config.py
scp requirements_tdlib.txt $SERVER:$REMOTE_DIR/

echo ""
echo "[4/7] Installing dependencies..."
ssh $SERVER "cd $REMOTE_DIR && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements_tdlib.txt"

echo ""
echo "[5/7] Updating systemd service..."
ssh $SERVER "cat > /etc/systemd/system/telegram-bot-tdlib.service << 'EOF'
[Unit]
Description=Telegram Bot Automation (TDLib)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$REMOTE_DIR
ExecStart=$REMOTE_DIR/venv/bin/python3 $REMOTE_DIR/main_tdlib.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/telegram-bot-tdlib.log
StandardError=append:/var/log/telegram-bot-tdlib.log

[Install]
WantedBy=multi-user.target
EOF"

echo ""
echo "[6/7] Reloading systemd and starting service..."
ssh $SERVER "systemctl daemon-reload && systemctl enable telegram-bot-tdlib.service && systemctl start telegram-bot-tdlib.service"

echo ""
echo "[7/7] Checking service status..."
sleep 3
ssh $SERVER "systemctl status telegram-bot-tdlib.service --no-pager"

echo ""
echo "=================================="
echo "✓ Deployment completed!"
echo "=================================="
echo ""
echo "Useful commands:"
echo "  - Check logs: ssh $SERVER 'tail -f /var/log/telegram-bot-tdlib.log'"
echo "  - Check status: ssh $SERVER 'systemctl status telegram-bot-tdlib.service'"
echo "  - Restart: ssh $SERVER 'systemctl restart telegram-bot-tdlib.service'"
echo ""
