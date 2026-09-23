#!/bin/bash
set -e

echo "🚀 Deploying Alpha to Production (Safe Mode - Database Preserved)..."

rsync -avz -e "ssh -p 65002 -i ~/.ssh/cpanel_deploy_key -o StrictHostKeyChecking=no" \
    --exclude=".git" \
    --exclude="__pycache__" \
    --exclude=".DS_Store" \
    --exclude="venv" \
    --exclude="data/*.db" \
    --exclude="*.db" \
    --exclude="*.sqlite" \
    ./ pedulyco@109.106.253.21:/home/pedulyco/public_html/alpha.zainalmultazam.com/

echo "🔄 Restarting Server on Port 8089..."
ssh -p 65002 -i ~/.ssh/cpanel_deploy_key -o StrictHostKeyChecking=no pedulyco@109.106.253.21 "cd /home/pedulyco/public_html/alpha.zainalmultazam.com && bash start_server.sh --restart"

echo "✅ Deployment Finished Successfully!"
