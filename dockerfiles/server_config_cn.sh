#!/usr/bin/env bash
set -euo pipefail

# ==========================
# Multi-arch build server setup
# Supports: Ubuntu 18.04/20.04/22.04/24.04
# Usage: sudo bash setup_multiarch_server.sh
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

# Ensure docker service is enabled and running
echo "[3/11] 启动并启用 docker 服务..."
systemctl enable docker --now

# 2) Install qemu-user-static & binfmt-support
echo "[4/11] 安装 qemu-user-static 与 binfmt-support..."
apt-get install -y qemu-user-static binfmt-support || true

# 3) Register QEMU handlers via multiarch/qemu-user-static
echo "[5/11] 注册 QEMU handlers（将使用 docker run --privileged）..."
if docker run --rm --privileged multiarch/qemu-user-static --reset -p yes; then
  echo "qemu-user-static 注册成功"
else
  echo "警告：qemu-user-static 注册可能失败（可能环境不支持 --privileged）。请检查或在 CI 中构建。"
fi

# 4) Install/Prepare buildx builder (docker-container driver recommended)
echo "[6/11] 检查 buildx 与准备 builder..."
# docker buildx 是 docker CLI plugin，一般随新版 docker-ce-cli 附带
if ! docker buildx version >/dev/null 2>&1; then
  echo "docker buildx plugin 未发现，尝试启用或安装..."
  # Some systems have it embedded; otherwise try to install via apt plugin path (best-effort)
  # Note: modern docker-ce includes buildx; if missing, user may need to upgrade docker.
fi

# Create builder if not exists
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

# 5) Add current user to docker group (if not root)
CURRENT_USER="$(logname 2>/dev/null || echo ${SUDO_USER:-$(whoami)})"
if [ -n "$CURRENT_USER" ] && id -nG "${CURRENT_USER}" | grep -qw docker; then
  echo "[8/11] 用户 ${CURRENT_USER} 已在 docker 组中"
else
  echo "[8/11] 将用户 ${CURRENT_USER} 加入 docker 组（需要重新登录才能生效）"
  usermod -aG docker "$CURRENT_USER" || true
fi

# 6) Useful CLI tools
echo "[9/11] 安装常用工具：python3-pip（可选）、skopeo（optional）"
apt-get install -y python3-pip || true

# 7) Test basic behaviour
echo "[10/11] 验证：docker 版本、buildx 版本"
docker --version || true
docker buildx version || true

echo "[11/11] 进行 quick test：在本机尝试运行一个 arm64 容器（应输出 aarch64）"
if docker run --rm --platform linux/arm64 arm64v8/ubuntu uname -m; then
  echo "ARM 容器运行测试通过"
else
  echo "注意：运行 arm64 容器测试失败（exec format error）。请确认上面的 qemu 注册步骤是否成功，或使用具有 --privileged 权限的环境。"
fi

cat <<'EOF'

==========================================
完成：服务器基础配置已完成。
接下来建议执行（手动或脚本）：

1) 确认 docker login（如果需要 push）：
   sudo docker login

2) 构建 multi-arch 镜像示例：
   docker buildx build \
     --platform linux/amd64,linux/arm64 \
     -t <your-repo/imagename:tag> \
     -f dockerfile ../ \
     --push

3) 如果你想把 builder 名称改回其他名称：
   docker buildx rm multi-builder
   docker buildx create --name mybuilder --driver docker-container --use
   docker buildx inspect --bootstrap

4) 若出现 exec format error：
   - 确认内核模块 binfmt_misc 已加载： sudo modprobe binfmt_misc
   - 重新注册 QEMU： sudo docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
   - 检查 docker buildx inspect --bootstrap 的输出

安全提示：
- 脚本在注册 QEMU 时使用了 --privileged（必要）。在受限托管环境或不允许 privileged 的环境中无法使用此方法，请改用 CI（GitHub Actions）来做 multi-arch 构建。
- 修改用户组 (usermod -aG docker) 后需要用户 logout/login 以使权限生效。

==========================================
EOF
