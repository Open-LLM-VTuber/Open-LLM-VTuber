#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Open-LLM-VTuber RunPod Bootstrap${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to print colored messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# ============================================================================
# STEP 1: System Setup (only if not already done)
# ============================================================================

if [ ! -f "/tmp/runpod_setup_complete" ]; then
    log_step "1/7 Installing system dependencies..."

    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq git curl wget ca-certificates build-essential > /dev/null 2>&1

    log_info "System packages installed"
    touch /tmp/runpod_setup_complete
else
    log_info "System already set up, skipping..."
fi

# ============================================================================
# STEP 2: Install uv package manager
# ============================================================================

if ! command -v uv &> /dev/null; then
    log_step "2/7 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh > /dev/null 2>&1
    export PATH="/root/.cargo/bin:$PATH"
    log_info "uv installed"
else
    log_info "uv already installed"
    export PATH="/root/.cargo/bin:$PATH"
fi

# ============================================================================
# STEP 3: Clone repository (if not already cloned)
# ============================================================================

if [ ! -d "/workspace/ai-mascot" ]; then
    log_step "3/7 Cloning repository..."
    cd /workspace
    git clone https://github.com/Synchlaire/ai-mascot.git
    cd ai-mascot
    git checkout claude/plan-runpod-deployment-01PDwYQpTiqVnW9ZEnRqfjDP
    log_info "Repository cloned"
else
    log_info "Repository already exists"
    cd /workspace/ai-mascot
fi

# ============================================================================
# STEP 4: Initialize submodules
# ============================================================================

log_step "4/7 Initializing frontend submodule..."
git submodule update --init --recursive || log_warn "Submodule init failed, continuing..."

# ============================================================================
# STEP 5: Install Python dependencies
# ============================================================================

if [ ! -f "/tmp/python_deps_installed" ]; then
    log_step "5/7 Installing Python dependencies (this may take 5-10 minutes)..."
    uv sync
    touch /tmp/python_deps_installed
    log_info "Python dependencies installed"
else
    log_info "Python dependencies already installed"
fi

# ============================================================================
# STEP 6: Install and start Ollama
# ============================================================================

if ! command -v ollama &> /dev/null; then
    log_step "6/7 Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh > /dev/null 2>&1
    log_info "Ollama installed"
else
    log_info "Ollama already installed"
fi

# Start Ollama service
if ! pgrep -x "ollama" > /dev/null; then
    log_info "Starting Ollama service..."
    ollama serve > /dev/null 2>&1 &
    OLLAMA_PID=$!

    # Wait for Ollama to be ready
    log_info "Waiting for Ollama to start..."
    MAX_RETRIES=30
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            log_info "✓ Ollama is ready!"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo -n "."
        sleep 2
    done
    echo ""

    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        log_error "Ollama failed to start"
        exit 1
    fi
else
    log_info "Ollama is already running"
fi

# Pull LLM model
MODEL_NAME="${OLLAMA_MODEL:-qwen2.5:32b}"
log_info "Checking for model: $MODEL_NAME"

if ! ollama list | grep -q "$MODEL_NAME"; then
    log_info "Downloading $MODEL_NAME (~20GB, this will take 10-20 minutes)..."
    log_warn "Go grab a coffee ☕ - this is the longest step..."
    ollama pull "$MODEL_NAME"
    log_info "✓ Model downloaded!"
else
    log_info "✓ Model already available"
fi

# Pre-load model into VRAM
log_info "Pre-loading model into GPU..."
curl -s http://localhost:11434/api/generate -d "{\"model\":\"$MODEL_NAME\",\"prompt\":\"Hello\",\"stream\":false}" > /dev/null 2>&1 || true

# ============================================================================
# STEP 7: Setup configuration
# ============================================================================

log_step "7/7 Setting up configuration..."

# Use RunPod config if exists, otherwise use default
if [ ! -f "conf.yaml" ]; then
    if [ -f "runpod/conf.yaml" ]; then
        log_info "Using RunPod configuration"
        cp runpod/conf.yaml conf.yaml
    else
        log_warn "No RunPod config found, using default"
        cp config_templates/conf.default.yaml conf.yaml
    fi
fi

# Check GPU
if ! nvidia-smi &> /dev/null; then
    log_warn "NVIDIA GPU not detected! Performance will be degraded."
else
    log_info "GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
fi

# ============================================================================
# Install missing dependencies (if any)
# ============================================================================

log_info "Checking runtime dependencies..."

# Check and install faster-whisper
if ! python -c "import faster_whisper" 2>/dev/null; then
    log_warn "Installing faster-whisper..."
    uv pip install faster-whisper ctranslate2
fi

# Check and install audio packages
for pkg in soundfile sounddevice; do
    if ! python -c "import $pkg" 2>/dev/null; then
        log_warn "Installing $pkg..."
        uv pip install $pkg
    fi
done

log_info "✓ All dependencies ready!"

# ============================================================================
# Display information
# ============================================================================

echo ""
log_info "========================================="
log_info "Configuration:"
log_info "  - Host: $(grep 'host:' conf.yaml | awk '{print $2}' | tr -d "'" || echo '0.0.0.0')"
log_info "  - Port: $(grep 'port:' conf.yaml | awk '{print $2}' || echo '12393')"
log_info "  - LLM: $MODEL_NAME"
log_info "  - ASR: $(grep 'asr_model:' conf.yaml | awk '{print $2}' | tr -d "'" || echo 'faster_whisper')"
log_info "  - TTS: $(grep 'tts_model:' conf.yaml | awk '{print $2}' | tr -d "'" || echo 'melo_tts')"
echo ""
log_info "Server will be accessible at:"
if [ -n "$RUNPOD_POD_ID" ]; then
    log_info "  ✓ https://${RUNPOD_POD_ID}-12393.proxy.runpod.net"
else
    log_info "  ✓ http://0.0.0.0:12393"
fi
log_info "========================================="
echo ""

# ============================================================================
# Start the server
# ============================================================================

log_info "🚀 Starting Open-LLM-VTuber server..."
echo ""

# Use uv to run the server
exec uv run run_server.py --verbose
