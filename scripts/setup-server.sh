#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Hetzner VPS Bootstrap Script for Multi-Lingual Podcast
# =============================================================================
# Run as root on a fresh Ubuntu 22.04/24.04 Hetzner VPS

APP_USER="podcast"
APP_DIR="/opt/multi-lingual-podcast"
LOG_DIR="/var/log/multi-lingual-podcast"

echo "=== Updating system packages ==="
apt-get update && apt-get upgrade -y

echo "=== Installing dependencies ==="
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    ufw \
    fail2ban \
    logrotate \
    git \
    jq

echo "=== Installing Docker ==="
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "=== Installing Docker Compose (standalone) ==="
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r .tag_name)
curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

echo "=== Configuring UFW ==="
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "=== Installing and configuring fail2ban ==="
systemctl enable fail2ban
systemctl start fail2ban

# Basic fail2ban config for SSH
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF

systemctl restart fail2ban

echo "=== Creating app user: ${APP_USER} ==="
useradd -r -s /bin/bash -m -d /home/${APP_USER} -G docker ${APP_USER} || true

echo "=== Setting up directory structure ==="
mkdir -p ${APP_DIR}
mkdir -p ${LOG_DIR}
mkdir -p ${APP_DIR}/backups
mkdir -p ${APP_DIR}/scripts
chown -R ${APP_USER}:${APP_USER} ${APP_DIR}
chown -R ${APP_USER}:${APP_USER} ${LOG_DIR}

echo "=== Configuring log rotation ==="
cat > /etc/logrotate.d/multi-lingual-podcast << EOF
${LOG_DIR}/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ${APP_USER} ${APP_USER}
    sharedscripts
    postrotate
        /usr/bin/systemctl reload docker > /dev/null 2>&1 || true
    endscript
}
EOF

echo "=== Adding app user to docker group ==="
usermod -aG docker ${APP_USER}

echo "=== Enabling Docker on boot ==="
systemctl enable docker
systemctl start docker

echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Switch to ${APP_USER}: su - ${APP_USER}"
echo "  2. Clone the repo into ${APP_DIR}"
echo "  3. Configure .env file"
echo "  4. Run ./scripts/deploy.sh"
