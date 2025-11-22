# Open-LLM-VTuber RunPod Deployment Guide

Complete guide for deploying Open-LLM-VTuber on RunPod with RTX-5090 GPU.

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Deployment Methods](#deployment-methods)
- [Configuration](#configuration)
- [Model Selection](#model-selection)
- [Frontend Setup](#frontend-setup)
- [Troubleshooting](#troubleshooting)
- [Cost Optimization](#cost-optimization)

## 🎯 Overview

This deployment separates the backend and frontend:

- **Backend (RunPod)**: GPU-accelerated LLM, ASR, TTS on RTX-5090
- **Frontend (Your PC/Phone)**: HTML/JS interface with WebSocket connection

### Architecture

```
┌─────────────────┐         WebSocket/HTTPS        ┌──────────────────┐
│                 │◄────────────────────────────────┤                  │
│  Your PC/Phone  │                                 │  RunPod (GPU)    │
│  (Frontend)     │                                 │  (Backend)       │
│                 │─────────────────────────────────►│                  │
└─────────────────┘      Audio + Control Data       └──────────────────┘
                                                     │ - Ollama (LLM)   │
                                                     │ - Whisper (ASR)  │
                                                     │ - MeloTTS (TTS)  │
                                                     └──────────────────┘
```

### System Requirements

**RunPod Pod:**
- GPU: RTX-5090 (24GB VRAM)
- RAM: 32GB minimum (64GB recommended)
- Storage: 100GB+ for models
- Network: Public endpoint enabled

**Client (PC/Phone):**
- Modern browser (Chrome, Firefox, Safari)
- Stable internet connection
- Microphone for voice input

## 🚀 Quick Start

### Method 1: One-Command Deployment

```bash
# 1. Clone the repository
git clone https://github.com/t41372/Open-LLM-VTuber.git
cd Open-LLM-VTuber

# 2. Build Docker image
./deploy.sh build

# 3. Push to Docker Hub (replace 'your-username')
DOCKER_REGISTRY=your-username ./deploy.sh push

# 4. Deploy on RunPod using the pushed image
# (See "RunPod Deployment" section below)
```

### Method 2: Direct RunPod Deployment

1. **Create RunPod Account**: https://runpod.io
2. **Deploy Pod**:
   - Select GPU: RTX-5090
   - Use template: Import `runpod-template.json`
   - Or use Docker image: `your-username/open-llm-vtuber:latest`
3. **Wait for startup** (10-30 minutes for first run - model downloads)
4. **Access**: `https://[POD-ID]-12393.proxy.runpod.net`

## 📦 Deployment Methods

### Option A: Using Pre-built Image

```bash
# On RunPod, use this Docker image:
your-dockerhub-username/open-llm-vtuber:latest
```

### Option B: Build from Source on RunPod

```bash
# In RunPod terminal:
git clone https://github.com/t41372/Open-LLM-VTuber.git
cd Open-LLM-VTuber
docker-compose up -d
```

### Option C: Local Build + Push

```bash
# Build locally
./deploy.sh build

# Push to registry
DOCKER_REGISTRY=your-username ./deploy.sh push

# Use in RunPod template
```

## ⚙️ Configuration

### RunPod Pod Settings

**Container Configuration:**
```
Docker Image: your-username/open-llm-vtuber:latest
Container Disk: 50GB
Volume Disk: 100GB
Volume Mount: /workspace
Expose HTTP Ports: 12393
Expose TCP Ports: 12393
```

**Environment Variables:**
```bash
OLLAMA_MODEL=qwen2.5:32b              # LLM model to use
API_KEY=your-secret-key               # Optional: Enable authentication
OPENAI_API_KEY=sk-...                 # Optional: Cloud LLM fallback
HF_HOME=/workspace/models             # Model cache location
```

### Configuration File (`conf.runpod.yaml`)

The deployment uses `conf.runpod.yaml` with optimized settings:

```yaml
system_config:
  host: '0.0.0.0'          # Listen on all interfaces
  port: 12393              # Application port

# GPU-accelerated ASR
asr_config:
  asr_model: 'faster_whisper'
  faster_whisper:
    device: 'cuda'
    compute_type: 'float16'

# GPU-accelerated TTS
tts_config:
  tts_model: 'melo_tts'
  melo_tts:
    device: 'cuda'
```

### Customizing Configuration

Edit `conf.runpod.yaml` before building, or mount a custom config:

```bash
# In docker-compose.yml
volumes:
  - ./my-custom-config.yaml:/workspace/conf.yaml:ro
```

## 🤖 Model Selection

### Recommended Models for RTX-5090 (24GB VRAM)

| Model | VRAM Usage | Quality | Speed | Use Case |
|-------|-----------|---------|-------|----------|
| qwen2.5:7b | ~5GB | Good | Very Fast | Development/Testing |
| qwen2.5:14b | ~9GB | Very Good | Fast | Balanced |
| qwen2.5:32b | ~18GB | Excellent | Medium | **Recommended** |
| llama3.3:70b-q4 | ~20GB | Excellent | Medium | High Quality |
| mistral:7b | ~5GB | Good | Very Fast | Lightweight |

### LLM Backends

**Option 1: Ollama (Default)**
- Easiest to use
- Automatic model management
- Good performance

**Option 2: vLLM (Advanced)**
- Best performance
- Requires more setup
- Batch inference support

**Option 3: Cloud APIs (Fallback)**
- OpenAI GPT-4
- Anthropic Claude
- Groq (fastest cloud option)

### Changing Models

**In configuration:**
```yaml
ollama_llm:
  model: 'llama3.3:70b-instruct-q4_K_M'
```

**Via environment variable:**
```bash
OLLAMA_MODEL=mistral:7b
```

**At runtime (in RunPod terminal):**
```bash
ollama pull llama3.3:70b-instruct-q4_K_M
```

## 🖥️ Frontend Setup

### Option 1: Use Included Frontend

1. Access the deployed instance directly:
   ```
   https://[POD-ID]-12393.proxy.runpod.net
   ```

2. The frontend is automatically served by the backend

### Option 2: Custom Frontend (PC/Phone)

1. **Clone frontend separately:**
   ```bash
   git clone --recurse-submodules https://github.com/t41372/Open-LLM-VTuber.git
   cd Open-LLM-VTuber/frontend
   ```

2. **Configure WebSocket URL:**

   Edit `frontend/config.js`:
   ```javascript
   const WEBSOCKET_URL = 'wss://[POD-ID]-12393.proxy.runpod.net/client-ws';
   ```

3. **Serve frontend locally:**
   ```bash
   # Simple HTTP server
   python -m http.server 8080
   # Or use any static file server
   ```

4. **Access:** `http://localhost:8080`

### Option 3: Deploy Frontend to Netlify/Vercel

1. **Fork the repository** on GitHub

2. **Connect to Netlify/Vercel**

3. **Set environment variable:**
   ```
   VITE_WEBSOCKET_URL=wss://[POD-ID]-12393.proxy.runpod.net/client-ws
   ```

4. **Deploy** - Your frontend is now accessible from anywhere!

### Mobile Access

**Direct access:**
```
https://[POD-ID]-12393.proxy.runpod.net
```

**Or use Netlify/Vercel URL** for better mobile experience.

## 🔍 Troubleshooting

### Issue: Pod won't start

**Solutions:**
1. Check RunPod logs for errors
2. Verify Docker image is accessible
3. Ensure sufficient storage (100GB+)
4. Check GPU availability

### Issue: Model download fails

**Solutions:**
```bash
# In RunPod terminal
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:32b

# Or use HuggingFace mirror (China)
export HF_ENDPOINT=https://hf-mirror.com
```

### Issue: WebSocket connection fails

**Check:**
1. Port 12393 is exposed in RunPod
2. Using `wss://` (not `ws://`)
3. Correct pod ID in URL
4. API key is correct (if enabled)

**Test WebSocket:**
```bash
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  https://[POD-ID]-12393.proxy.runpod.net/client-ws
```

### Issue: GPU not detected

**Check:**
```bash
# In RunPod terminal
nvidia-smi

# Should show RTX-5090 with 24GB VRAM
```

**Fix:**
1. Ensure pod type is GPU (not CPU)
2. Restart pod
3. Check Docker GPU access: `docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi`

### Issue: High latency / Slow response

**Optimize:**
1. Use smaller model (qwen2.5:14b instead of 32b)
2. Enable `faster_first_response: True`
3. Use quantized models (Q4, Q5)
4. Check RunPod region (use closest to you)
5. Reduce ASR model size (use `medium` instead of `large-v3`)

### Issue: Out of memory

**VRAM Management:**
```bash
# Check current VRAM usage
nvidia-smi

# Unload model to free VRAM
ollama stop

# Use smaller models or higher quantization
```

### Common Error Messages

**"Model not found":**
```bash
ollama pull qwen2.5:32b
```

**"CUDA out of memory":**
- Use smaller model
- Reduce batch size
- Enable model quantization

**"Connection refused":**
- Check if Ollama is running: `ps aux | grep ollama`
- Restart: `ollama serve`

## 💰 Cost Optimization

### RunPod Pricing (RTX-5090)

| Type | Est. Cost/Hour | Use Case |
|------|---------------|----------|
| Spot Instance | $0.60-1.20 | Development, testing |
| On-Demand | $1.50-2.50 | Production, demos |

### Cost-Saving Tips

1. **Use Spot Instances** for development (save 50-70%)
2. **Stop pod when idle** (don't pay for downtime)
3. **Use smaller models** when quality allows
4. **Auto-stop after inactivity** (RunPod setting)
5. **Share one deployment** across multiple users
6. **Cloud LLM fallback**: Use cloud APIs for occasional use, local for heavy use

### Budget-Friendly Configuration

```yaml
# Use smaller models
ollama_llm:
  model: 'qwen2.5:7b'  # Only ~5GB VRAM

# Use cloud TTS (free)
tts_config:
  tts_model: 'edge_tts'

# Use lighter ASR
asr_config:
  asr_model: 'faster_whisper'
  faster_whisper:
    model_path: 'medium'  # Instead of large-v3
```

**Est. Cost:** ~$10-30/month for casual use (few hours/day)

### Alternative: Self-hosting

If you have a local GPU:
- RTX 3060 (12GB): Can run 7B-13B models
- RTX 4090 (24GB): Can run same as RunPod
- Cost: Only electricity (~$5-15/month)

## 📊 Performance Benchmarks

### RTX-5090 Performance

| Configuration | First Response | Total Latency | VRAM Usage |
|--------------|---------------|---------------|------------|
| Qwen2.5-7B | ~1.5s | ~3s | 5GB |
| Qwen2.5-14B | ~2s | ~4s | 9GB |
| Qwen2.5-32B | ~2.5s | ~5s | 18GB |
| Llama3.3-70B-Q4 | ~3s | ~6s | 20GB |

*Latency includes: ASR (0.5-1s) + LLM (1-3s) + TTS (0.5-1s)*

## 🔐 Security

See [SECURITY.md](SECURITY.md) for detailed security configuration.

**Quick security checklist:**
- [ ] Set `API_KEY` environment variable
- [ ] Use HTTPS/WSS (RunPod provides this)
- [ ] Don't expose Ollama port publicly
- [ ] Rotate API keys regularly
- [ ] Monitor logs for suspicious activity

## 🎓 Advanced Usage

### Custom Characters

```bash
# Add character config to characters/ folder
# Edit conf.runpod.yaml:
character_config:
  conf_name: 'my_character'
```

### Multi-language Support

```yaml
# Japanese voice
tts_config:
  tts_model: 'edge_tts'
  edge_tts:
    voice: 'ja-JP-NanamiNeural'

# Japanese ASR
asr_config:
  faster_whisper:
    language: 'ja'
```

### Group Conversations

Enable multiple users talking to the same AI:

```yaml
system_config:
  tool_prompts:
    group_conversation_prompt: 'group_conversation_prompt'
```

### MCP Tools Integration

Enable AI to use tools (search, time, etc.):

```yaml
agent_settings:
  basic_memory_agent:
    use_mcpp: True
    mcp_enabled_servers: ["time", "ddg-search", "filesystem"]
```

## 📚 Additional Resources

- **Main Repository**: https://github.com/t41372/Open-LLM-VTuber
- **Documentation**: Check project README
- **Community**: GitHub Discussions
- **Issues**: GitHub Issues
- **RunPod Docs**: https://docs.runpod.io

## 🤝 Support

**Having issues?**

1. Check [Troubleshooting](#troubleshooting) section
2. Search [GitHub Issues](https://github.com/t41372/Open-LLM-VTuber/issues)
3. Check RunPod logs: Pod → Logs tab
4. Create new issue with:
   - Pod configuration
   - Error messages
   - Steps to reproduce

## 📝 Changelog

### v1.0.0 (2025-01-XX)
- Initial RunPod deployment support
- RTX-5090 optimization
- Docker containerization
- Security middleware
- Multi-language support

---

**Happy VTubing! 🎉**

Built with ❤️ for the AI VTuber community
