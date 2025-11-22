#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Open-LLM-VTuber RunPod Startup${NC}"
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

# Check if running with GPU
if ! nvidia-smi &> /dev/null; then
    log_warn "NVIDIA GPU not detected! This deployment is optimized for GPU."
else
    log_info "NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
fi

# Start Ollama service in background (if not using docker-compose)
if ! pgrep -x "ollama" > /dev/null; then
    log_info "Starting Ollama service..."
    ollama serve &
    OLLAMA_PID=$!

    # Wait for Ollama to be ready
    log_info "Waiting for Ollama to be ready..."
    MAX_RETRIES=30
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            log_info "Ollama is ready!"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo -n "."
        sleep 2
    done

    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        log_error "Ollama failed to start within timeout"
        exit 1
    fi
else
    log_info "Ollama is already running"
fi

# Pull the default LLM model if not already present
MODEL_NAME="${OLLAMA_MODEL:-qwen2.5:32b}"
log_info "Checking for model: $MODEL_NAME"

if ! ollama list | grep -q "$MODEL_NAME"; then
    log_info "Pulling model $MODEL_NAME (this may take a while on first run)..."
    ollama pull "$MODEL_NAME"
    log_info "Model $MODEL_NAME downloaded successfully!"
else
    log_info "Model $MODEL_NAME already available"
fi

# Optional: Pre-load model into VRAM
log_info "Pre-loading model into GPU memory..."
curl -s http://localhost:11434/api/generate -d "{\"model\":\"$MODEL_NAME\",\"prompt\":\"Hello\",\"stream\":false}" > /dev/null 2>&1 || true

# Check for frontend submodule
if [ ! -f "frontend/index.html" ]; then
    log_warn "Frontend submodule not found. Attempting to initialize..."
    git submodule update --init --recursive || log_error "Failed to initialize frontend submodule"
fi

# Set up configuration
if [ ! -f "conf.yaml" ]; then
    if [ -f "runpod/conf.yaml" ]; then
        log_info "Using RunPod configuration..."
        cp runpod/conf.yaml conf.yaml
    else
        log_warn "No configuration found! Using default..."
        cp config_templates/conf.default.yaml conf.yaml
    fi
fi

# Display configuration info
log_info "Configuration:"
log_info "  - Host: $(grep 'host:' conf.yaml | awk '{print $2}' | tr -d "'")"
log_info "  - Port: $(grep 'port:' conf.yaml | awk '{print $2}')"
log_info "  - LLM Model: $MODEL_NAME"
log_info "  - ASR Model: $(grep 'asr_model:' conf.yaml | awk '{print $2}' | tr -d "'")"
log_info "  - TTS Model: $(grep 'tts_model:' conf.yaml | awk '{print $2}' | tr -d "'")"

# Display access information
log_info ""
log_info "========================================="
log_info "Server will be accessible at:"
if [ -n "$RUNPOD_POD_ID" ]; then
    log_info "  https://${RUNPOD_POD_ID}-12393.proxy.runpod.net"
else
    log_info "  http://0.0.0.0:12393"
fi
log_info "========================================="
log_info ""

# Start the Open-LLM-VTuber server
log_info "Starting Open-LLM-VTuber server..."

# Use uv to run the server
exec uv run run_server.py --verbose
