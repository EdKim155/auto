#!/bin/bash
# Fast deployment script - Telethon + optimized modules
# Usage: ./deploy_fast.sh

set -e

SERVER="auto-server"
REMOTE_DIR="/root/auto"

echo "=================================="
echo "FAST Automation Deployment"
echo "Telethon + Optimized Modules"
echo "=================================="

echo ""
echo "[1/5] Creating backup..."
ssh $SERVER "mkdir -p /root/auto_backups && tar -czf /root/auto_backups/backup_\$(date +%Y%m%d_%H%M%S).tar.gz -C /root auto/ || true"

echo ""
echo "[2/5] Uploading optimized modules..."
scp -r modules/ $SERVER:$REMOTE_DIR/
scp bot_automation_fast.py main_fast.py config_tdlib.py $SERVER:$REMOTE_DIR/

echo ""
echo "[3/5] Updating config..."
ssh $SERVER "cd $REMOTE_DIR && cp config_tdlib.py config.py"

echo ""
echo "[4/5] Creating systemd service..."
ssh $SERVER "cat > /etc/systemd/system/telegram-bot-fast.service << 'EOF'
[Unit]
Description=Telegram Bot Automation (FAST)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$REMOTE_DIR
ExecStart=$REMOTE_DIR/venv/bin/python3 $REMOTE_DIR/main_fast.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/telegram-bot-fast.log
StandardError=append:/var/log/telegram-bot-fast.log

[Install]
WantedBy=multi-user.target
EOF"

echo ""
echo "[5/5] Starting service..."
ssh $SERVER "systemctl daemon-reload && systemctl enable telegram-bot-fast.service && systemctl restart telegram-bot-fast.service"

echo ""
sleep 3
echo "Status:"
ssh $SERVER "systemctl status telegram-bot-fast.service --no-pager | head -15"

echo ""
echo "=================================="
echo "✓ FAST Deployment completed!"
echo "=================================="
echo ""
echo "Useful commands:"
echo "  - Logs: ssh $SERVER 'tail -f /var/log/telegram-bot-fast.log'"
echo "  - Status: ssh $SERVER 'systemctl status telegram-bot-fast.service'"
echo "  - Restart: ssh $SERVER 'systemctl restart telegram-bot-fast.service'"
echo ""
