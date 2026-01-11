#!/usr/bin/env bash
set -euo pipefail

# ==========================
# Multi-arch build server setup
# Supports: Ubuntu 18.04/20.04/22.04/24.04, WSL2
# Usage: sudo bash server_config_cn.sh
# ==========================

# Config
BUILDER_NAME="multi-builder"
TIMEOUT_SECS=300

echo "==== 开始服务器配置：安装 Docker, QEMU, buildx 等（Ubuntu） ===="

# Helper: wait for command success with timeout
wait_for_success() {
  local cmd="$1"
  local timeout=${2:-$TIMEOUT_SECS}
  local interval=2
  local waited=0
  until bash -c "$cmd"; do
    sleep $interval
    waited=$((waited + interval))
    if [ "$waited" -ge "$timeout" ]; then
      echo "等待超时：命令未成功： $cmd"
      return 1
    fi
  done
  return 0
}

# 0) Basic apt update
echo "[1/11] apt update & install base packages..."
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

# 1) Install Docker (official repo)
echo "[2/11] 安装 Docker（官方 repo）..."
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
  DISTRO="$(lsb_release -is | tr '[:upper:]' '[:lower:]')"
  CODENAME="$(lsb_release -cs)"
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $CODENAME stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
else
  echo "docker 已存在，跳过安装"
fi

# 2) Enable docker service if systemctl available
echo "[3/11] 启动并启用 docker 服务（如果支持 systemctl）..."
if command -v systemctl >/dev/null 2>&1; then
  if systemctl list-unit-files | grep -q '^docker.service'; then
    systemctl enable docker --now
    echo "docker 服务已启用并启动"
  else
    echo "docker.service 未找到，可能环境不支持 systemd，跳过启用"
  fi
else
  echo "systemctl 不可用，跳过 docker 服务启用（WSL2 或受限环境）"
fi

# 3) Install qemu-user-static & binfmt-support
echo "[4/11] 安装 qemu-user-static 与 binfmt-support..."
apt-get install -y qemu-user-static binfmt-support || true

# 4) Register QEMU handlers via multiarch/qemu-user-static
echo "[5/11] 注册 QEMU handlers..."
if docker run --rm --privileged multiarch/qemu-user-static --reset -p yes; then
  echo "qemu-user-static 注册成功"
else
  echo "警告：qemu-user-static 注册可能失败，请检查或在 CI 中构建"
fi

# 5) Install/Prepare buildx builder
echo "[6/11] 检查 buildx 与准备 builder..."
if ! docker buildx version >/dev/null 2>&1; then
  echo "docker buildx plugin 未发现，尝试启用或安装..."
fi

if docker buildx ls | grep -q "^${BUILDER_NAME}"; then
  echo "builder ${BUILDER_NAME} 已存在，使用该 builder"
else
  echo "创建 buildx builder: ${BUILDER_NAME} (driver: docker-container)"
  docker buildx create --name "${BUILDER_NAME}" --driver docker-container --use || {
    echo "创建 builder 失败，尝试使用默认 builder"
  }
fi

echo "[7/11] bootstrap buildx（启动 builder 并注册 binfmt）..."
docker buildx inspect --bootstrap || {
  echo "警告：buildx inspect --bootstrap 失败，请检查 docker 权限与网络"
}

# 6) Add current user to docker group (if not root)
CURRENT_USER="$(logname 2>/dev/null || echo ${SUDO_USER:-$(whoami)})"
if [ -n "$CURRENT_USER" ] && id -nG "${CURRENT_USER}" | grep -qw docker; then
  echo "[8/11] 用户 ${CURRENT_USER} 已在 docker 组中"
else
  echo "[8/11] 将用户 ${CURRENT_USER} 加入 docker 组（需要重新登录才能生效）"
  usermod -aG docker "$CURRENT_USER" || true
fi

# 7) Useful CLI tools
echo "[9/11] 安装常用工具：python3-pip（可选）、skopeo（optional）"
apt-get install -y python3-pip || true

# 8) Test basic behaviour
echo "[10/11] 验证：docker 版本、buildx 版本"
docker --version || true
docker buildx version || true

echo "[11/11] quick test：运行一个 arm64 容器（应输出 aarch64）"
if docker run --rm --platform linux/arm64 arm64v8/ubuntu uname -m; then
  echo "ARM 容器运行测试通过"
else
  echo "注意：运行 arm64 容器测试失败，请确认 qemu 注册步骤成功或使用 --privileged 环境"
fi

cat <<'EOF'

==========================================
完成：服务器基础配置已完成。
建议操作：

1) 确认 docker login（如果需要 push）：
   sudo docker login

2) 构建 multi-arch 镜像示例：
   docker buildx build \
     --platform linux/amd64,linux/arm64 \
     -t <your-repo/imagename:tag> \
     -f dockerfile ../ \
     --push

3) 修改 builder 名称：
   docker buildx rm multi-builder
   docker buildx create --name mybuilder --driver docker-container --use
   docker buildx inspect --bootstrap

4) 若出现 exec format error：
   - 确认 binfmt_misc 已加载： sudo modprobe binfmt_misc
   - 重新注册 QEMU
   - 检查 docker buildx inspect --bootstrap 输出

安全提示：
- 脚本在注册 QEMU 时使用 --privileged，WSL2 或受限环境可能无法使用
- 修改用户组后需要重新登录
==========================================
EOF
