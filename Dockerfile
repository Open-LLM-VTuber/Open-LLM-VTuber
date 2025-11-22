# Multi-stage Dockerfile for Open-LLM-VTuber on RunPod with RTX-5090
# Optimized for GPU inference with CUDA 12.1

FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 AS base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    git \
    curl \
    wget \
    ca-certificates \
    build-essential \
    libsndfile1 \
    ffmpeg \
    portaudio19-dev \
    espeak-ng \
    libespeak-ng-dev \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install uv package manager for faster dependency installation
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /workspace

# Copy dependency files first (for layer caching)
COPY pyproject.toml uv.lock ./

# Install Python dependencies using uv
RUN uv sync --frozen

# Install Ollama for local LLM inference
RUN curl -fsSL https://ollama.com/install.sh | sh

# Copy application code
COPY . .

# Download and install frontend submodule
RUN git submodule update --init --recursive || echo "Frontend submodule already initialized"

# Create necessary directories
RUN mkdir -p /workspace/models \
    /workspace/cache \
    /workspace/logs \
    /workspace/chat_history \
    /workspace/characters \
    /workspace/live2d-models \
    /workspace/backgrounds \
    /workspace/avatars

# Set permissions
RUN chmod +x /workspace/start.sh 2>/dev/null || echo "start.sh will be added later"

# Expose port
EXPOSE 12393

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:12393/ || exit 1

# Set entrypoint
ENTRYPOINT ["/workspace/start.sh"]
