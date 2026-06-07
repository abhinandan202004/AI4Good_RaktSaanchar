#!/bin/bash
# ==============================================================================
# RaktSaanchar — EC2 Production Startup Script
# Run this once on your EC2 instance to install Docker and start the backend
# ==============================================================================

set -e

echo "==> Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

echo "==> Installing Docker..."
sudo apt-get install -y docker.io docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu   # Allow ubuntu user to run docker without sudo

echo "==> Installing Git..."
sudo apt-get install -y git

echo "==> Cloning repository..."
git clone https://github.com/abhinandan202004/AI4Good_RaktSaanchar.git /home/ubuntu/app
cd /home/ubuntu/app/backend

echo "==> Creating .env.prod file..."
cat > /home/ubuntu/app/backend/.env.prod << 'EOF'
# ── App ───────────────────────────────────────────────────────────────────────
APP_NAME="RaktaSanchaar API"
APP_VERSION="1.0.0"
DEBUG=False

# ── Database — update with your RDS endpoint ──────────────────────────────────
DATABASE_URL=postgresql://postgres:REPLACE_DB_PASSWORD@REPLACE_RDS_ENDPOINT:5432/rakt

# ── Redis — running as local container ────────────────────────────────────────
REDIS_URL=redis://redis:6379

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY=REPLACE_WITH_LONG_RANDOM_SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── AWS — credentials handled by EC2 IAM role (no keys needed) ───────────────
AWS_REGION=us-east-1
AWS_SNS_ENABLED=True
AWS_SES_SENDER=pujariabhinandann@gmail.com
AWS_SNS_TOPIC_ARN=REPLACE_WITH_SNS_TOPIC_ARN

# ── Chatbot API Keys ──────────────────────────────────────────────────────────
MISTRAL_API_KEY=REPLACE_WITH_MISTRAL_KEY
SARVAM_API_KEY=REPLACE_WITH_SARVAM_KEY
EOF

echo "==> IMPORTANT: Edit .env.prod before continuing!"
echo "    nano /home/ubuntu/app/backend/.env.prod"
echo ""
echo "==> Once .env.prod is updated, start the backend with:"
echo "    cd /home/ubuntu/app/backend"
echo "    docker compose -f docker-compose.prod.yml up -d --build"
echo ""
echo "==> Check logs with:"
echo "    docker compose -f docker-compose.prod.yml logs -f backend"
