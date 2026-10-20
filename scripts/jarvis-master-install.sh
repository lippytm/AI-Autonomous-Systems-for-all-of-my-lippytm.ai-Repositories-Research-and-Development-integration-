#!/bin/bash
# JARVIS MASTER INSTALLER — AI Builds AI
# bash <(curl -s https://raw.githubusercontent.com/lippytm/AI-Autonomous-Systems-for-all-of-my-lippytm.ai-Repositories-Research-and-Development-integration-/main/scripts/jarvis-master-install.sh)
set -e
DOMAIN=aievolutionaryevolutions.com; PORT=3001; N8NPORT=5678
INSTALL=$HOME/jarvis; LOG=$HOME/jarvis.log
apt-get update -qq && apt-get install -y -qq git curl nginx certbot python3-certbot-nginx ufw
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs
npm install -g pm2 n8n >> $LOG 2>&1
mkdir -p $INSTALL
[ -d $INSTALL/mempalace ] && (cd $INSTALL/mempalace && git pull) || git clone https://github.com/lippytm/aievolutionaryevolutions.com-Hermes-Fabric-MemPalace-.git $INSTALL/mempalace
cd $INSTALL/mempalace && npm install >> $LOG 2>&1
[ ! -f .env ] && printf "PORT=$PORT\nMCP_ENABLED=true\nANTHROPIC_API_KEY=your-key\nOPENAI_API_KEY=your-key\n" > .env
pm2 start server.js --name jarvis && pm2 save
N8N_PASS=JarvisSwarm$(date +%Y)!
export N8N_BASIC_AUTH_ACTIVE=true N8N_BASIC_AUTH_USER=jarvis-admin N8N_BASIC_AUTH_PASSWORD=$N8N_PASS
pm2 start n8n --name n8n-jarvis -- start && pm2 save
[ ! -f ~/.ssh/jarvis_deploy ] && ssh-keygen -t ed25519 -f ~/.ssh/jarvis_deploy -N ""
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet") | sort -u | crontab -
pm2 list
echo "DONE: https://jarvis.$DOMAIN | n8n: jarvis-admin/$N8N_PASS"
