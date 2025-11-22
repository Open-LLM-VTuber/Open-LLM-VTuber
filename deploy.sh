#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
IMAGE_NAME="open-llm-vtuber"
IMAGE_TAG="latest"
REGISTRY="${DOCKER_REGISTRY:-}" # Set to your Docker Hub username or registry

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

show_banner() {
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════════════════╗"
    echo "║   Open-LLM-VTuber RunPod Deployment Tool          ║"
    echo "║   RTX-5090 Optimized                              ║"
    echo "╚════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_help() {
    echo "Usage: ./deploy.sh [OPTION]"
    echo ""
    echo "Options:"
    echo "  build         Build Docker image locally"
    echo "  push          Push image to registry (requires DOCKER_REGISTRY)"
    echo "  run-local     Run locally with docker-compose"
    echo "  stop-local    Stop local deployment"
    echo "  test          Test the deployment"
    echo "  clean         Clean up containers and volumes"
    echo "  logs          Show logs from running container"
    echo "  runpod-setup  Generate RunPod deployment instructions"
    echo "  help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh build                  # Build image"
    echo "  ./deploy.sh run-local              # Run with docker-compose"
    echo "  DOCKER_REGISTRY=username ./deploy.sh push  # Push to Docker Hub"
}

check_requirements() {
    log_step "Checking requirements..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker compose &> /dev/null; then
        log_warn "docker-compose not found as plugin, checking for standalone..."
        if ! command -v docker-compose &> /dev/null; then
            log_error "docker-compose is not installed."
            exit 1
        fi
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi

    log_info "All requirements satisfied"
}

build_image() {
    log_step "Building Docker image..."

    # Check if frontend submodule is initialized
    if [ ! -f "frontend/index.html" ]; then
        log_warn "Frontend submodule not found. Initializing..."
        git submodule update --init --recursive
    fi

    docker build \
        --platform linux/amd64 \
        -t "${IMAGE_NAME}:${IMAGE_TAG}" \
        -f Dockerfile \
        .

    log_info "Image built successfully: ${IMAGE_NAME}:${IMAGE_TAG}"
}

push_image() {
    if [ -z "$REGISTRY" ]; then
        log_error "DOCKER_REGISTRY environment variable not set!"
        log_info "Usage: DOCKER_REGISTRY=your-dockerhub-username ./deploy.sh push"
        exit 1
    fi

    log_step "Pushing image to registry..."

    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
    docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "$FULL_IMAGE_NAME"
    docker push "$FULL_IMAGE_NAME"

    log_info "Image pushed: $FULL_IMAGE_NAME"
    log_info "Use this image in RunPod template"
}

run_local() {
    log_step "Starting local deployment with docker-compose..."

    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        log_info "Creating .env file..."
        cat > .env << EOF
# API Keys (optional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=

# Security
API_KEY=

# Ollama Model
OLLAMA_MODEL=qwen2.5:32b
EOF
        log_warn "Please edit .env file to add your API keys"
    fi

    $COMPOSE_CMD up -d

    log_info "Deployment started!"
    log_info "Access at: http://localhost:12393"
    log_info "View logs: ./deploy.sh logs"
}

stop_local() {
    log_step "Stopping local deployment..."
    $COMPOSE_CMD down
    log_info "Deployment stopped"
}

show_logs() {
    log_step "Showing logs (Ctrl+C to exit)..."
    $COMPOSE_CMD logs -f
}

test_deployment() {
    log_step "Testing deployment..."

    # Wait for service to be ready
    log_info "Waiting for service to be ready..."
    MAX_RETRIES=30
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s http://localhost:12393/ > /dev/null 2>&1; then
            log_info "Service is responding!"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo -n "."
        sleep 2
    done

    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        log_error "Service failed to respond within timeout"
        exit 1
    fi

    log_info "✓ HTTP endpoint is accessible"
    log_info "✓ Deployment test passed!"
}

clean_deployment() {
    log_step "Cleaning up deployment..."

    read -p "This will remove containers and volumes. Continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $COMPOSE_CMD down -v
        log_info "Cleanup complete"
    else
        log_info "Cleanup cancelled"
    fi
}

runpod_setup() {
    log_step "Generating RunPod deployment instructions..."

    cat << 'EOF'

╔════════════════════════════════════════════════════════════════════╗
║                    RunPod Deployment Guide                         ║
╚════════════════════════════════════════════════════════════════════╝

📋 STEP 1: Build and Push Image (if using custom image)
----------------------------------------------------------
1. Build the image:
   ./deploy.sh build

2. Push to Docker Hub:
   DOCKER_REGISTRY=your-username ./deploy.sh push

📋 STEP 2: Create RunPod Pod
----------------------------------------------------------
1. Go to https://runpod.io/console/pods
2. Click "Deploy" → "Deploy a Pod"
3. Select GPU: RTX 5090 (or RTX 4090/A100 as fallback)
4. Choose deployment method:

   Option A - Use Docker Image:
   - Select "Custom Container"
   - Image: your-username/open-llm-vtuber:latest
   - Expose HTTP Port: 12393
   - Expose TCP Port: 12393

   Option B - Use RunPod Template (after creating):
   - Select your saved template

5. Configure Storage:
   - Container Disk: 50GB minimum
   - Volume Disk: 100GB (recommended for models)
   - Mount Path: /workspace

6. Environment Variables (optional):
   - OLLAMA_MODEL=qwen2.5:32b
   - API_KEY=your-secret-key

📋 STEP 3: Access Your Deployment
----------------------------------------------------------
After deployment, RunPod will provide URLs:

WebSocket URL: wss://[POD-ID]-12393.proxy.runpod.net/client-ws
HTTP URL: https://[POD-ID]-12393.proxy.runpod.net

📋 STEP 4: Connect Frontend
----------------------------------------------------------
1. Download the frontend from this repo
2. Edit frontend config to point to your RunPod WebSocket URL
3. Open frontend in browser or deploy to Netlify/Vercel

📋 STEP 5: Monitor and Manage
----------------------------------------------------------
- View logs: Click "Logs" in RunPod console
- SSH access: Use RunPod's built-in terminal
- Stop/Start: Use RunPod console controls

💰 Cost Optimization Tips
----------------------------------------------------------
- Use Spot Instances for development ($0.60-1.20/hr)
- Use On-Demand for production ($1.50-2.50/hr)
- Stop pod when not in use
- Use smaller models (7B-13B) if budget constrained

🔧 Troubleshooting
----------------------------------------------------------
- If service won't start: Check logs for errors
- If model download fails: Check storage space
- If WebSocket fails: Verify port 12393 is exposed
- If GPU not detected: Select GPU pod type

EOF

    log_info "Setup guide displayed above"
}

# Main script
show_banner

case "${1:-help}" in
    build)
        check_requirements
        build_image
        ;;
    push)
        check_requirements
        push_image
        ;;
    run-local)
        check_requirements
        run_local
        ;;
    stop-local)
        check_requirements
        stop_local
        ;;
    logs)
        check_requirements
        show_logs
        ;;
    test)
        check_requirements
        test_deployment
        ;;
    clean)
        check_requirements
        clean_deployment
        ;;
    runpod-setup)
        runpod_setup
        ;;
    help|*)
        show_help
        ;;
esac
