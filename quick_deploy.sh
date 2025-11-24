#!/bin/bash
# Quick deployment script - minimal steps
# Usage: ./quick_deploy.sh

set -e

SERVER="auto-server"
REMOTE_DIR="/root/auto"

echo "🚀 Quick TDLib Deployment..."

# Upload only changed files
echo "📤 Uploading files..."
scp -r modules/ $SERVER:$REMOTE_DIR/ > /dev/null 2>&1
scp bot_automation_tdlib.py main_tdlib.py config_tdlib.py requirements_tdlib.txt $SERVER:$REMOTE_DIR/ > /dev/null 2>&1

# Restart service
echo "🔄 Restarting service..."
ssh $SERVER "cd $REMOTE_DIR && cp config_tdlib.py config.py && systemctl restart telegram-bot-tdlib.service" > /dev/null 2>&1

# Wait and check status
sleep 2
echo "✅ Status:"
ssh $SERVER "systemctl status telegram-bot-tdlib.service --no-pager | head -15"

echo ""
echo "📊 Latest logs:"
ssh $SERVER "tail -20 /var/log/telegram-bot-tdlib.log"
