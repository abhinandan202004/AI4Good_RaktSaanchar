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
| `SERVER_IP` | `129.153.xx.xx` | Same as `ORACLE_HOST` (used for Vite build args) |

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

## Useful Commands

```bash
# View logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Check server memory consumption (should show swap file in use)
free -h

# Check Docker container memory usage
docker stats
```
