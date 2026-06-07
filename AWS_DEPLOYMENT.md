# RaktSaanchar — AWS Deployment Guide

## Architecture (Free Tier Optimized)

```
Users
  │
  ├──► CloudFront ──► S3 (React SPA)
  │         HTTPS, global CDN
  │
  └──► EC2 t2.micro (us-east-1)
            │  port 8000 → FastAPI + Redis (Docker)
            └──► RDS PostgreSQL t3.micro
                      (private, VPC-only access)
```

**Estimated cost on free tier: ~$0–$2/month** (just S3 + CloudFront data transfer)

---

## Prerequisites

- AWS account (free tier active)
- AWS CLI installed locally (`aws configure`)
- Git + GitHub repo with your code
- SSH key pair created in AWS console

---

## Step 1 — Create EC2 Instance

1. Go to **EC2 → Launch Instance**
2. Settings:
   - **Name**: `raktsaanchar-backend`
   - **AMI**: Ubuntu Server 22.04 LTS (Free tier eligible)
   - **Instance type**: `t2.micro` ✅ Free tier
   - **Key pair**: Create or select existing (save `.pem` file!)
   - **Storage**: 20 GB gp3
3. **Security Group** — create new `raktsaanchar-sg`:
   | Type | Port | Source |
   |------|------|--------|
   | SSH | 22 | My IP |
   | Custom TCP | 8000 | 0.0.0.0/0 |
   | All traffic | All | sg-SAME (self-reference for internal) |
4. Launch → note the **Public IPv4 address**

---

## Step 2 — Create RDS PostgreSQL

1. Go to **RDS → Create Database**
2. Settings:
   - **Engine**: PostgreSQL 15
   - **Template**: Free tier ✅
   - **Instance**: `db.t3.micro`
   - **DB identifier**: `raktsaanchar-db`
   - **Username**: `postgres`
   - **Password**: (set a strong password, save it!)
   - **DB name**: `rakt`
   - **VPC**: Default VPC
   - **Public access**: No
   - **Security Group**: Add `raktsaanchar-sg` (same as EC2)
3. Create → wait ~5 min → note the **Endpoint** (e.g. `raktsaanchar-db.xxxxx.us-east-1.rds.amazonaws.com`)

---

## Step 3 — Create IAM Role for EC2

> This lets EC2 call AWS SNS/SES without hardcoded credentials.

1. Go to **IAM → Roles → Create Role**
2. **Trusted entity**: AWS service → EC2
3. **Permissions**: Attach these policies:
   - `AmazonSNSFullAccess`
   - `AmazonSESFullAccess`
4. **Role name**: `raktsaanchar-ec2-role`
5. Go to **EC2 → select your instance → Actions → Security → Modify IAM Role**
6. Attach `raktsaanchar-ec2-role`

---

## Step 4 — Set Up EC2 (SSH In)

```bash
# On your local machine:
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

```bash
# On EC2 — install Docker
sudo apt-get update -y
sudo apt-get install -y docker.io docker-compose-plugin git
sudo systemctl enable docker && sudo systemctl start docker
sudo usermod -aG docker ubuntu
newgrp docker   # apply group without logout

# Clone your repo
git clone https://github.com/YOUR_USERNAME/AI4Good_RaktSaanchar.git /home/ubuntu/app
cd /home/ubuntu/app/backend

# Create production env file
cp .env.example .env.prod
nano .env.prod   # Fill in values below
```

### `.env.prod` values to fill in:

```env
APP_NAME="RaktaSanchaar API"
APP_VERSION="1.0.0"
DEBUG=False

DATABASE_URL=postgresql://postgres:YOUR_RDS_PASSWORD@YOUR_RDS_ENDPOINT:5432/rakt

REDIS_URL=redis://redis:6379

SECRET_KEY=GENERATE_WITH: python3 -c "import secrets; print(secrets.token_hex(32))"
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# AWS — NO KEYS NEEDED (handled by IAM role)
AWS_REGION=us-east-1
AWS_SNS_ENABLED=True
AWS_SES_SENDER=pujariabhinandann@gmail.com
AWS_SNS_TOPIC_ARN=YOUR_SNS_TOPIC_ARN

MISTRAL_API_KEY=YOUR_MISTRAL_KEY
SARVAM_API_KEY=YOUR_SARVAM_KEY
```

```bash
# Start backend
docker compose -f docker-compose.prod.yml up -d --build

# Verify
docker compose -f docker-compose.prod.yml logs -f backend
curl http://localhost:8000/health
```

---

## Step 5 — Create S3 Bucket (Frontend)

```bash
# On your LOCAL machine (AWS CLI):
aws s3 mb s3://raktsaanchar-frontend --region us-east-1

# Enable static website hosting
aws s3 website s3://raktsaanchar-frontend \
  --index-document index.html \
  --error-document index.html

# Make bucket publicly readable
aws s3api put-bucket-policy \
  --bucket raktsaanchar-frontend \
  --policy '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Principal":"*",
      "Action":"s3:GetObject",
      "Resource":"arn:aws:s3:::raktsaanchar-frontend/*"
    }]
  }'
```

---

## Step 6 — Build & Upload Frontend

```bash
# On LOCAL machine — update the EC2 IP first
# Edit frontend/.env.production:
#   VITE_API_BASE_URL=http://<YOUR_EC2_PUBLIC_IP>:8000/api/v1

cd frontend
npm ci --legacy-peer-deps
npm run build

# Upload to S3
aws s3 sync dist/ s3://raktsaanchar-frontend --delete
```

---

## Step 7 — Create CloudFront Distribution

1. Go to **CloudFront → Create Distribution**
2. **Origin domain**: Select your S3 bucket (`raktsaanchar-frontend.s3.amazonaws.com`)
3. **Origin access**: Public (S3 already public)
4. **Viewer protocol policy**: Redirect HTTP to HTTPS
5. **Default root object**: `index.html`
6. **Custom error pages**:
   - Error code: `403` → Response page: `/index.html` → HTTP 200
   - Error code: `404` → Response page: `/index.html` → HTTP 200
   *(Required for React Router SPA routing)*
7. Create → wait ~5 min → note your **Distribution domain** (e.g. `dxxxxx.cloudfront.net`)

---

## Step 8 — Configure GitHub Actions Secrets

Go to **GitHub repo → Settings → Secrets and variables → Actions → New secret**:

| Secret Name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your AWS IAM user access key (for CI/CD only) |
| `AWS_SECRET_ACCESS_KEY` | Your AWS IAM user secret key |
| `S3_BUCKET_NAME` | `raktsaanchar-frontend` |
| `CLOUDFRONT_DISTRIBUTION_ID` | Your CloudFront distribution ID |
| `VITE_API_BASE_URL` | `http://<EC2_PUBLIC_IP>:8000/api/v1` |
| `EC2_HOST` | Your EC2 public IP |
| `EC2_SSH_KEY` | Contents of your `.pem` file (the full private key) |

> **Tip**: Create a dedicated IAM user for CI/CD with only `S3FullAccess` + `CloudFrontFullAccess` permissions — never use your root credentials.

---

## Step 9 — Test End to End

```bash
# Backend health
curl http://<EC2_PUBLIC_IP>:8000/health
# Expected: {"status": "ok"}

# API docs
open http://<EC2_PUBLIC_IP>:8000/docs

# Frontend
open https://<CLOUDFRONT_DOMAIN>.cloudfront.net
```

---

## Future Scope Upgrades

| When budget allows | Upgrade | Cost |
|---|---|---|
| Need HTTPS for API | Add ALB + ACM free SSL cert | +$16/month |
| High traffic | Move to t3.small or t3.medium | +$7–15/month |
| DB reliability | Enable RDS Multi-AZ | +$14/month |
| Managed Redis | ElastiCache t3.micro | +$12/month |
| Observability | CloudWatch dashboards + alerts | ~$2/month |
| PDF uploads | S3 presigned URLs in backend | ~$0.50/month |
| Secrets | AWS Secrets Manager | ~$0.40/secret |

---

## Useful Commands (On EC2)

```bash
# View live backend logs
cd /home/ubuntu/app/backend
docker compose -f docker-compose.prod.yml logs -f backend

# Restart backend
docker compose -f docker-compose.prod.yml restart backend

# Full rebuild after code change
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build

# Check running containers
docker compose -f docker-compose.prod.yml ps

# Check disk usage
df -h
docker system df
```
