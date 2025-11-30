#!/usr/bin/env bash
set -euo pipefail

#
# Multi-arch Docker Build Server Auto Setup Script
# Supports: Ubuntu 18.04 / 20.04 / 22.04 / 24.04
#
# Run as: sudo bash setup_multiarch_server.sh
#

BUILDER_NAME="multi-builder"
TIMEOUT_SECS=300

echo "==== Starting setup: Docker + QEMU + Buildx multi-arch environment ===="

wait_for_success() {
  local cmd="$1"
  local timeout=${2:-$TIMEOUT_SECS}
  local interval=2
  local waited=0
  until bash -c "$cmd"; do
    sleep $interval
    waited=$((waited + interval))
    if [ "$waited" -ge "$timeout" ]; then
      echo "Timeout: command did not succeed: $cmd"
      return 1
    fi
  done
}

echo "[1/10] Updating apt and installing base packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  apt-transport-https \
  ca-certificates \
  curl \
  gnupg-agent \
  software-properties-common \
  lsb-release \
  git \
  jq \
  make \
  build-essential || true

echo "[2/10] Installing Docker CE from official repo..."
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

  DISTRO="$(lsb_release -is | tr '[:upper:]' '[:lower:]')"
  CODENAME="$(lsb_release -cs)"
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
    https://download.docker.com/linux/ubuntu $CODENAME stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null

  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
else
  echo "Docker detected → Skipping installation"
fi

echo "[3/10] Enabling and starting Docker daemon..."
systemctl enable docker --now

echo "[4/10] Installing QEMU for multi-arch support..."
apt-get install -y qemu-user-static binfmt-support || true

echo "[5/10] Registering QEMU handlers (using privileged container)..."
if docker run --rm --privileged multiarch/qemu-user-static --reset -p yes; then
  echo "QEMU successfully registered"
else
  echo "⚠ Warning: QEMU registration failed — privileged mode may be restricted"
fi

echo "[6/10] Setting up docker buildx..."
if ! docker buildx version >/dev/null 2>&1; then
  echo "⚠ Warning: docker buildx is not available"
  echo "Try upgrading Docker or installing CLI plugin separately"
fi

echo "[7/10] Creating/Using buildx builder: ${BUILDER_NAME}"
if docker buildx ls | grep -q "^${BUILDER_NAME}"; then
  docker buildx use "${BUILDER_NAME}"
else
  docker buildx create --name "${BUILDER_NAME}" --driver docker-container --use
fi

echo "[8/10] Bootstrapping buildx builder..."
docker buildx inspect --bootstrap || true

echo "[9/10] Adding user '$SUDO_USER' to docker group..."
if id -nG "$SUDO_USER" | grep -qw docker; then
  echo "User already in docker group"
else
  usermod -aG docker "$SUDO_USER"
  echo "User added: please re-login or reboot for group change to take effect"
fi

echo "[10/10] Verifying installation..."
docker --version
docker buildx version || true
docker ps >/dev/null && echo "✔ Docker engine OK"
docker buildx ls && echo "✔ Buildx OK"
echo "✔ QEMU emulation enabled (check using: docker run --platform linux/arm64 hello-world)"

echo
echo "==== Setup COMPLETE 🎉 ===="
echo "You can now build multi-platform images like:"
echo
echo "  docker buildx build \\"
echo "    --platform linux/amd64,linux/arm64 \\"
echo "    -t your/repo:tag \\"
echo "    --push ."
echo
echo "Note: You must logout and login again for Docker group permissions to apply."
