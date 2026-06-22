# RaktSaanchar — Deploy to Oracle Cloud Free Tier (1 GB AMD)

> **Target**: Oracle Cloud Always Free — AMD VM (`VM.Standard.E2.1.Micro` — 1 OCPU, 1 GB RAM, x86_64)  
> **Stack**: Docker Compose with Memory Limits  
> **Public URL**: `http://<YOUR-ORACLE-IP>/`

---

## Prerequisites Checklist

Before you start, have these ready:
- [ ] Oracle Cloud account (free at cloud.oracle.com)
- [ ] Your `SECRET_KEY` — run: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Gmail App Password (or Brevo SMTP credentials) for email notifications
- [ ] Mistral API key (for AI chatbot)
- [ ] Sarvam API key (for multilingual support)
- [ ] Your GitHub repo URL (public) or SSH key (private repo)

---

## Step 1 — Create an Oracle Cloud Account

1. Go to [cloud.oracle.com](https://cloud.oracle.com) ➔ **Start for Free**
2. Sign up with your email. You'll need a credit card for identity verification — **you will NOT be charged** as long as you use Always Free resources.
3. Choose your **Home Region** carefully (e.g., `ap-mumbai-1` for India).

---

## Step 2 — Create the AMD Instance

1. In the Oracle Cloud console, go to: **Compute ➔ Instances ➔ Create Instance**
2. **Name**: `raktsaanchar-server`
3. **Placement**: Expand this section and leave it on default `AD-1`.
4. **Image**: Click "Change image" ➔ Select **Canonical Ubuntu 22.04** (x86_64 standard version, not minimal).
5. **Shape**: Click "Change shape"
   - Select **Specialty and previous generation** tab.
   - Choose `VM.Standard.E2.1.Micro` (Always Free-eligible).
   - Click **Select shape**.
6. **Networking**:
   - Primary network: **Create new virtual cloud network** (or select default if exists).
   - Subnet: **Create new public subnet** (or select default public subnet if exists).
   - Public IP: **Automatically assign public IPv4 address** ➔ Set to **ON (Enabled)**.
7. **SSH Key**: 
   - Select **Generate a key pair for me**.
   - **CRITICAL**: Click **Download private key** and **Download public key** now. Save them somewhere safe. You cannot download them later.
8. Click **Create** and wait 1–2 minutes for the status to turn green (**RUNNING**).
9. Copy the **Public IP address** of your instance.

---

## Step 3 — Open Firewall Ports (Security List)

Oracle uses TWO layers of firewall: the VCN Security List AND the OS-level iptables.

### 3a — VCN Security List (Oracle Cloud Console)

1. **Find your VCN**: 
   * Click the hamburger menu (three lines) in the top-left corner of the Oracle Cloud Console.
   * Go to **Networking** ➔ **Virtual Cloud Networks**.
   * Click on the name of the VCN that was created (it will match the VCN name from your instance page, e.g., `vcn-20260617-xxxx`).

2. **Open the Security List**:
   * On the left sidebar under **Resources**, click on **Security Lists**.
   * Click on the **Default Security List for vcn-xxxx** link in the table.

3. **Add Ingress Rules**:
   * Click the blue **Add Ingress Rules** button.
   * Fill out the form for **Port 80 (HTTP)**:
     * **Source Type**: `CIDR` (leave as default)
     * **Source CIDR**: `0.0.0.0/0`
     * **IP Protocol**: `TCP` (leave as default)
     * **Source Port Range**: (leave blank)
     * **Destination Port Range**: `80`
     * **Description**: `HTTP web traffic`
   * Click the **+ Another Ingress Rule** button at the bottom of the dialog.
   * Fill out the second rule for **Port 443 (HTTPS)**:
     * **Source Type**: `CIDR`
     * **Source CIDR**: `0.0.0.0/0`
     * **IP Protocol**: `TCP`
     * **Source Port Range**: (leave blank)
     * **Destination Port Range**: `443`
     * **Description**: `HTTPS secure traffic`
   * Click the blue **Add Ingress Rules** button at the bottom of the pop-up to save.

### 3b — OS-level iptables (on the instance itself)

Ubuntu on Oracle blocks ports at the OS level too. Run this after SSH'ing in:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

---

## Step 4 — Connect via SSH

Use the private key you downloaded in Step 2:

```bash
# Set secure permissions on your key file (Mac/Linux only)
chmod 400 ~/Downloads/ssh-key-*.key

# Replace with your key path and Oracle instance's public IP
ssh -i ~/Downloads/ssh-key-*.key ubuntu@<YOUR-ORACLE-IP>
```

---

## Step 5 — Configure Swap Space (Mandatory for 1 GB VM)

Since the AMD instance has only 1 GB RAM, we must add **swap space** to prevent containers from crashing due to Out of Memory (OOM) errors during build/runtime.

On the VM terminal, run:

```bash
# 1. Create a 2 GB swap file
sudo fallocate -l 2G /swapfile

# 2. Set secure permissions
sudo chmod 600 /swapfile

# 3. Format the file as swap space
sudo mkswap /swapfile

# 4. Enable swap
sudo swapon /swapfile

# 5. Make the swap file persistent after reboots
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 6. Verify swap is active (should show ~2.0G swap available)
free -h
```

---

## Step 6 — Install Docker on the Instance

```bash
# Update packages
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo bash

# Add ubuntu user to docker group (no sudo needed)
sudo usermod -aG docker ubuntu

# Install Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# Apply group change (or logout/login)
newgrp docker

# Verify
docker --version
docker compose version
```

---

## Step 7 — Clone the Repository

### If your repo is PUBLIC:
```bash
git clone https://github.com/abhinandan202004/AI4Good_RaktSaanchar.git
cd AI4Good_RaktSaanchar
```

### If your repo is PRIVATE:
```bash
# Generate SSH key on server, add to GitHub
ssh-keygen -t ed25519 -C "oracle-deploy"
cat ~/.ssh/id_ed25519.pub
# → Add this public key to GitHub: Settings → SSH Keys → New SSH Key
git clone git@github.com:abhinandan202004/AI4Good_RaktSaanchar.git
cd AI4Good_RaktSaanchar
```

---

## Step 8 — First Manual Deploy (Recommended)

Before letting GitHub Actions take over, run a manual deploy once to ensure everything starts up cleanly.

1. **Create the `.env` file**:
   ```bash
   cp .env.example .env
   nano .env
   ```
   Fill in these values:
   ```bash
   SECRET_KEY=<your-32-char-random-string>
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASS=xxxx-xxxx-xxxx-xxxx # 16-char App Password
   NTFY_BASE_URL=https://ntfy.sh
   NTFY_TOPIC_PREFIX=raktsaanchar-prod
   MISTRAL_API_KEY=your-key
   SARVAM_API_KEY=your-key
   SERVER_IP=<YOUR-ORACLE-PUBLIC-IP>
   ```

2. **Deploy the stack**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```

3. **Verify running containers**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
   ```

4. **Seed the database**:
   ```bash
   pip3 install httpx passlib bcrypt python-dotenv sqlalchemy psycopg2-binary
   python3 scripts/seed_donors.py
   ```

---

## Step 9 — Configure GitHub Actions CI/CD (Automation)

To automate subsequent deployments on every push to the `main` branch, we use the pre-configured GitHub workflow.

### 9a — Add Secrets to GitHub

In your GitHub repository, navigate to: **Settings ➔ Secrets and variables ➔ Actions ➔ New repository secret**.

Add the following secrets:

| Secret Name | Value Example | Description |
|-------------|---------------|-------------|
| `ORACLE_HOST` | `129.153.xx.xx` | Public IP of your Oracle instance |
| `ORACLE_USER` | `ubuntu` | Standard Ubuntu user |
| `ORACLE_SSH_KEY` | `-----BEGIN OPENSSH PRIVATE KEY-----...` | Entire contents of your private key `.key` file |
| `SECRET_KEY` | `5c6130b...` | Same shared 32-character JWT secret |
| `SMTP_USER` | `your-email@gmail.com` | Email address |
| `SMTP_PASS` | `xxxx-xxxx-xxxx-xxxx` | Gmail App Password |
| `MISTRAL_API_KEY`| `mistral-key` | AI Chatbot key |
| `SARVAM_API_KEY` | `sarvam-key` | Translation service key |
| `SERVER_IP` | `raktsaanchar.duckdns.org` | Your domain name (or public IP for HTTP) — used for Vite API build arguments (must be the domain name for HTTPS) |

### 9b — Test the Automation
1. Make a small code change (or edit `README.md`).
2. Push your changes to the `main` branch:
   ```bash
   git add .
   git commit -m "Configure CI/CD"
   git push origin main
   ```
3. Go to the **Actions** tab on your GitHub repository. You should see the **Production Deployment** run starting.
4. Once completed, the runner will have successfully SSH'd into the VM, updated the code, written the `.env` file, built/started the services, and cleaned up unused Docker cache images!

---

## Step 10 — Transitioning to HTTPS (SSL/TLS)

To enable secure HTTPS and WSS (secure WebSockets), you need to get a domain name pointed to your server IP, obtain a Let's Encrypt certificate, and update the repository configurations.

### 10a — Prerequisites
1. **Domain Name**: Get a free subdomain at [DuckDNS](https://www.duckdns.org) (e.g., `raktsaanchar.duckdns.org`) or use a custom domain. Point the DNS A record to your VM's public IP (`140.238.229.46`).
2. **Oracle Ingress Rule**: Ensure port `443` is allowed in your Oracle Virtual Cloud Network (VCN) ingress security list (detailed in Step 3a).
3. **OS-Level Firewall**: Ensure port `443` is open in the OS-level iptables (detailed in Step 3b).

### 10b — Obtain Let's Encrypt SSL Certificate
Run the following commands on your Oracle VM terminal:

```bash
# 1. Stop the Nginx gateway container to free up port 80
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop gateway

# 2. Install certbot on the VM
sudo apt-get update
sudo apt-get install -y certbot

# 3. Request the certificate using standalone challenge (replace with your domain)
sudo certbot certonly --standalone -d <YOUR_DOMAIN>

# 4. Verify certificates were generated successfully
# They should be at: /etc/letsencrypt/live/<YOUR_DOMAIN>/
sudo ls -l /etc/letsencrypt/live/<YOUR_DOMAIN>/
```

### 10c — Configure and Restart the Stack
1. **Configure Nginx**: Locally or on the server, open `infra/nginx.prod.conf` and replace `YOUR_DOMAIN_HERE` with your actual domain name (e.g. `raktsaanchar.duckdns.org`):
   ```bash
   # On the server or locally before pushing:
   sed -i 's/YOUR_DOMAIN_HERE/<YOUR_DOMAIN>/g' infra/nginx.prod.conf
   ```
2. **Update GitHub Secrets**:
   - Go to your GitHub repo ➔ **Settings** ➔ **Secrets and variables** ➔ **Actions**.
   - Edit the secret `SERVER_IP` and replace the numeric IP address with your new domain name (e.g., `raktsaanchar.duckdns.org`).
3. **Push to deploy**:
   - Commit and push your changes to GitHub `main` branch. GitHub Actions will build the frontend container referencing the new `https://` API address, mount the host certificates directory into Nginx, and restart the gateway on ports `80` and `443`.
   ```bash
   git add .
   git commit -m "Enable HTTPS support"
   git push origin main
   ```

---

## Step 11 — Deploying ML Services to Hugging Face Spaces (Serverless)

Moving ML workloads to Hugging Face Spaces saves a massive amount of RAM and CPU on your Oracle Cloud VM. Hugging Face provides a **free 16 GB RAM container** which is perfect for PyTorch and EasyOCR.

### 11a — Create the Hugging Face Space
1. Sign up or log in at [huggingface.co](https://huggingface.co/).
2. Go to **Spaces** ➔ [Create new Space](https://huggingface.co/new-space).
3. Set the following settings:
   - **Space Name**: `raktsaanchar-ml`
   - **SDK**: `Docker`
   - **Docker Template**: `Blank`
   - **Space Hardware**: `CPU basic • 2 vCPU • 16 GB • Free`
   - **Visibility**: `Public` (recommended — since it contains no database secrets)
4. Click **Create Space**.

### 11b — Upload ML Code and Model Files
Hugging Face Spaces are backed by a Git repository. You can push the files directly using Git:

1. Clone your new Hugging Face Space locally:
   ```bash
   git clone https://huggingface.co/spaces/<YOUR_HF_USERNAME>/raktsaanchar-ml
   ```
2. Copy the contents of the `services/ml-service/` folder (which includes `Dockerfile`, `requirements.txt`, `app/`, and the `models/` directory containing all `.pkl` model files) into the cloned Hugging Face Space directory.
3. Commit and push the changes:
   ```bash
   cd raktsaanchar-ml
   git add .
   git commit -m "Deploy serverless ML and OCR API"
   git push
   ```
4. Hugging Face will automatically build and start the container. You can monitor the progress on the **App** or **Logs** tab of your Hugging Face Space.

### 11c — Add ML_SERVICE_URL to GitHub Secrets
1. Go to your GitHub repository ➔ **Settings** ➔ **Secrets and variables** ➔ **Actions**.
2. Click **New repository secret**:
   - **Name**: `ML_SERVICE_URL`
   - **Value**: `https://<YOUR_HF_USERNAME>-raktsaanchar-ml.hf.space` (replace `<YOUR_HF_USERNAME>` with your actual Hugging Face username, all lowercase).
3. If you have a Mistral API key, make sure to add `MISTRAL_API_KEY` as a secret in your Hugging Face Space **Settings** under **Variables and secrets** (so the OCR explainer can generate summaries).

Once the secret is added, push any code change to GitHub main. The CI/CD pipeline will deploy, and `core-service` on the VM will automatically forward all ML queries to the Hugging Face Space!

---

## Useful Commands

```bash
# View logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Check server memory consumption (should show swap file in use)
free -h

# Check Docker container memory usage
docker stats
```

---

## Billing & Instance Management

### ⚠️ Understanding Oracle Cloud Always Free

Your instance is a **VM.Standard.E2.1.Micro** (Always Free eligible). As long as you stay within the Always Free limits, **you will not be billed**. However, some actions can inadvertently trigger charges:

| Resource | Always Free | Paid |
|---|---|---|
| `VM.Standard.E2.1.Micro` compute | ✅ Free (up to 2 instances) | — |
| Boot volume storage (47 GB default) | ✅ Free | Extra storage costs money |
| Public IP address (static) | ✅ Free (1 per Always Free instance) | Extra reserved IPs cost money |
| **Data egress (outbound traffic)** | ✅ 10 GB/month free | Above 10 GB is charged |
| **Block Volume (additional disk)** | ⚠️ Only 200 GB free total | Extra costs money |

> **Bottom line**: Your `VM.Standard.E2.1.Micro` instance with default boot volume is **free to run 24/7**. Stopping it saves no money but also costs nothing. The main billing risk is **outbound data transfer > 10 GB/month**.

---

### 🔴 How to STOP the Instance (via Oracle Cloud Console)

Stopping the instance shuts down the VM. Docker containers stop, and your website goes offline. The storage and IP address are preserved.

1. Go to [cloud.oracle.com](https://cloud.oracle.com) and log in.
2. Navigate to: **☰ Menu** ➔ **Compute** ➔ **Instances**.
3. Click on your instance name (e.g., `instance-20260617-0046`).
4. On the instance details page, click the **Stop** button at the top.
5. In the confirmation dialog, click **Stop Instance**.
6. Wait for the instance state to change from `RUNNING` → `STOPPING` → **`STOPPED`**.

> Your website (`https://raktsaanchar.servehttp.com`) will go offline immediately.

**Alternative — Stop via SSH (graceful Docker shutdown before VM stop):**
```bash
# SSH into the VM
ssh -i ~/Downloads/ssh-key-2026-06-16.key ubuntu@140.238.229.46

# Gracefully stop all Docker containers first
docker compose -f ~/AI4Good_RaktSaanchar/docker-compose.yml -f ~/AI4Good_RaktSaanchar/docker-compose.prod.yml down

# Then stop the instance from Oracle Console as described above
```

---

### 🟢 How to START the Instance (via Oracle Cloud Console)

1. Go to [cloud.oracle.com](https://cloud.oracle.com) and log in.
2. Navigate to: **☰ Menu** ➔ **Compute** ➔ **Instances**.
3. Click on your instance name.
4. Click the **Start** button at the top.
5. Wait for the instance state to change from `STOPPED` → `STARTING` → **`RUNNING`**.

> The VM will boot up in ~1-2 minutes. **Docker containers set to `restart: unless-stopped` will automatically restart** because that policy only skips auto-restart when you explicitly ran `docker compose down`. If you gracefully stopped containers before shutting down, restart them manually:

```bash
# SSH into the VM after it starts
ssh -i ~/Downloads/ssh-key-2026-06-16.key ubuntu@140.238.229.46

# Start all Docker containers
cd ~/AI4Good_RaktSaanchar
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify everything is running
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

> Your website at `https://raktsaanchar.servehttp.com` will be back online in ~1-2 minutes after the containers start.

---

### 🗑️ How to TERMINATE (Permanently Delete) the Instance

> [!CAUTION]
> **Terminating permanently deletes the instance and all data on it.** This cannot be undone. Only do this if you are sure you no longer need the server.

1. Go to the instance details page in Oracle Cloud Console.
2. Click **More Actions** ➔ **Terminate**.
3. In the dialog, check **"Permanently delete the attached boot volume"** if you want to free all storage.
4. Click **Terminate Instance**.
