#!/bin/bash
set -euo pipefail

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

INSTALL_DIR="$HOME/Open-LLM-VTuber"

echo ""
echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN} Open-LLM-VTuber One-Click Installer${NC}"
echo -e "${CYAN}=========================================${NC}"
echo ""

echo -e "[...] Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python3 not found. Installing...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
    elif command -v brew &> /dev/null; then
        brew install python
    else
        echo -e "${RED}Cannot install Python automatically. Please install Python 3.11+ manually.${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}[OK] Python3 found${NC}"

echo -e "[...] Checking GPU..."
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}[OK] NVIDIA GPU detected${NC}"
    GPU_AVAILABLE=true
else
    echo -e "${YELLOW}[WARN] No NVIDIA GPU detected. CPU mode will be used.${NC}"
    GPU_AVAILABLE=false
fi

echo -e "[...] Cloning repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}[WARN] Existing installation found. Pulling latest...${NC}"
    cd "$INSTALL_DIR" && git pull --ff-only && cd -
    echo -e "${GREEN}[OK] Repository updated${NC}"
else
    git clone https://github.com/Open-LLM-VTuber/Open-LLM-VTuber.git "$INSTALL_DIR"
    echo -e "${GREEN}[OK] Repository cloned${NC}"
fi

cd "$INSTALL_DIR"

echo -e "[...] Creating virtual environment..."
python3 -m venv venv
echo -e "${GREEN}[OK] Virtual environment created${NC}"

echo -e "[...] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
if [ "$GPU_AVAILABLE" = true ]; then
    pip install -r requirements.txt
else
    pip install -r requirements.txt
    pip uninstall -y onnxruntime-gpu 2>/dev/null || true
    pip install onnxruntime
fi
echo -e "${GREEN}[OK] Dependencies installed${NC}"

echo -e "[...] Creating data directories..."
for dir in data cache logs config live2d-models; do
    mkdir -p "$dir"
done
echo -e "${GREEN}[OK] Directories created${NC}"

echo -e "[...] Checking for Live2D model..."
if [ $(find live2d-models -name "*.model3.json" 2>/dev/null | wc -l) -eq 0 ]; then
    echo -e "${YELLOW}[WARN] No Live2D model found.${NC}"
    echo -e "${YELLOW}         Please download your Live2D model and place it in live2d-models/${NC}"
else
    echo -e "${GREEN}[OK] Live2D model found${NC}"
fi

echo -e "[...] Creating launch script..."
cat > run.sh << 'SCRIPT'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
exec python run_server.py
SCRIPT
chmod +x run.sh
echo -e "${GREEN}[OK] Launch script created${NC}"

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN} Installation Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "To start Open-LLM-VTuber:"
echo "  ./run.sh"
echo ""
echo "Web interface: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""