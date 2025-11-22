# 🚀 RunPod Deployment for Open-LLM-VTuber

Complete deployment solution for running Open-LLM-VTuber on RunPod with RTX-5090 GPU.

## 📂 Directory Structure

```
runpod/
├── README.md (this file)      # Overview and navigation
├── DEPLOYMENT.md              # Quick start guide
├── MODELS.md                  # Model configuration guide
├── SECURITY.md                # Security setup guide
├── template.json              # RunPod template (import to console)
├── conf.yaml                  # Default RunPod configuration
└── characters/                # Pre-configured character setups
    ├── balanced.yaml          # ⭐ RECOMMENDED (18GB VRAM)
    ├── performance.yaml       # Fast response (10GB VRAM)
    ├── quality.yaml           # Best quality (22GB VRAM)
    ├── budget.yaml            # Minimal cost (6GB VRAM)
    └── multilingual.yaml      # Multi-language (18GB VRAM)
```

## 📚 Documentation Guide

### New to RunPod Deployment?
**Start here:** [DEPLOYMENT.md](DEPLOYMENT.md)
- Quick 3-step deployment
- RunPod setup instructions
- First-time deployment checklist

### Want to Optimize Performance?
**Read:** [MODELS.md](MODELS.md)
- Model selection guide
- VRAM usage breakdown
- Configuration switching
- Performance tuning tips

### Setting Up Security?
**Read:** [SECURITY.md](SECURITY.md)
- API key authentication
- Rate limiting
- Security best practices
- Network configuration

## 🎯 Quick Start (3 Steps)

### 1. Build Docker Image
```bash
# From repository root
./deploy.sh build
```

### 2. Push to Docker Hub
```bash
DOCKER_REGISTRY=your-username ./deploy.sh push
```

### 3. Deploy on RunPod
- Import `template.json` to RunPod console
- Or use image: `your-username/open-llm-vtuber:latest`
- Select GPU: RTX-5090
- Deploy and wait ~10-30 minutes

**Access:** `https://[POD-ID]-12393.proxy.runpod.net`

## 🎨 Choose Your Configuration

| Configuration | VRAM | Response Time | Cost/Hour* | Use Case |
|--------------|------|---------------|------------|----------|
| **budget** | 6GB | ~1.5s | $0.60 | Testing, minimal cost |
| **performance** | 10GB | ~2s | $1.00 | Fast interactions |
| **balanced** ⭐ | 18GB | ~2.5s | $1.50 | Best overall (default) |
| **quality** | 22GB | ~3s | $2.00 | Maximum quality |
| **multilingual** | 18GB | ~2.5s | $1.50 | EN/JA/ZH/KO support |

*RunPod spot instance estimates

### Switch Configuration

**Before building:**
```bash
# From repository root
cp runpod/characters/performance.yaml runpod/conf.yaml
./deploy.sh build
```

**After deployment:**
```bash
# In RunPod terminal
cp runpod/characters/quality.yaml conf.yaml
docker-compose restart
```

## 🔧 Files Overview

### Configuration Files

**`conf.yaml`** - Main RunPod configuration
- Optimized for remote access (host: 0.0.0.0)
- GPU-accelerated ASR and TTS
- Balanced mode (Qwen2.5-32B, Whisper Large-v3-turbo, MeloTTS)

**`characters/*.yaml`** - Pre-configured setups
- Each file is a complete character configuration
- Copy any to `conf.yaml` to switch modes
- All optimized for RTX-5090

**`template.json`** - RunPod Template
- Import to RunPod console for one-click deployment
- Pre-configured ports, volumes, environment variables
- Remember to update Docker image name

## 💡 Common Tasks

### Test Locally First
```bash
./deploy.sh run-local
# Opens at http://localhost:12393
```

### View Deployment Logs
```bash
# Local
./deploy.sh logs

# RunPod
# Use RunPod console → Pods → Your Pod → Logs tab
```

### Update Configuration
```bash
# Edit config
nano runpod/conf.yaml

# Or copy a preset
cp runpod/characters/performance.yaml runpod/conf.yaml

# Rebuild
./deploy.sh build
DOCKER_REGISTRY=username ./deploy.sh push

# Restart pod in RunPod
```

### Check Model Usage
```bash
# In RunPod terminal
nvidia-smi  # GPU/VRAM usage
ollama list  # Loaded models
docker stats  # Container stats
```

## 📊 What's Included

### Pre-configured Components

**LLM Backend:** Ollama with Qwen2.5-32B
- Excellent quality (rivals GPT-3.5)
- Fast inference on RTX-5090
- Fully offline operation

**ASR:** Faster-Whisper Large-v3-turbo
- GPU-accelerated transcription
- ~1 second latency
- High accuracy

**TTS:** MeloTTS
- GPU-accelerated synthesis
- Natural-sounding voice
- Multiple languages support

**Security:** Optional API key authentication
- Protects your deployment
- Rate limiting included
- HTTPS/WSS via RunPod proxy

## 🆘 Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| Pod won't start | Check logs; ensure 100GB+ storage |
| Out of memory | Use smaller model (budget/performance config) |
| Slow responses | Switch to performance config |
| WebSocket fails | Verify port 12393 exposed; use wss:// |
| High costs | Use spot instances; stop when idle |

**Detailed troubleshooting:** See [DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting)

## 🔗 Quick Links

**Main Deployment Guide:** [DEPLOYMENT.md](DEPLOYMENT.md)
**Model Configuration:** [MODELS.md](MODELS.md)
**Security Setup:** [SECURITY.md](SECURITY.md)
**RunPod Template:** [template.json](template.json)

**Repository Root Files:**
- [Dockerfile](../Dockerfile) - Docker build definition
- [docker-compose.yml](../docker-compose.yml) - Service orchestration
- [deploy.sh](../deploy.sh) - Deployment automation
- [start.sh](../start.sh) - Container entrypoint

## 💰 Cost Estimates

### RTX-5090 Pricing (2025)

| Usage Pattern | Instance Type | Monthly Cost |
|--------------|---------------|--------------|
| Casual (2hr/day) | Spot | $36-72 |
| Regular (4hr/day) | Spot | $72-144 |
| Heavy (8hr/day) | Spot | $144-288 |
| Production (24/7) | On-Demand | $1,080-1,800 |

**Save money:**
- Use spot instances (50-70% cheaper)
- Auto-stop when idle
- Use budget config for testing
- Share one deployment across users

## 🎓 Next Steps

1. **Read the deployment guide:** [DEPLOYMENT.md](DEPLOYMENT.md)
2. **Choose your configuration:** [MODELS.md](MODELS.md)
3. **Build and test locally:** `./deploy.sh run-local`
4. **Deploy to RunPod:** Follow [DEPLOYMENT.md](DEPLOYMENT.md)
5. **Secure your deployment:** [SECURITY.md](SECURITY.md)
6. **Start talking to your AI VTuber!** 🎉

## 📞 Support

**Documentation Issues:** Open an issue on GitHub
**Deployment Help:** Check [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting
**RunPod Support:** https://docs.runpod.io

---

**Ready to deploy?** → Start with [DEPLOYMENT.md](DEPLOYMENT.md)

Built with ❤️ for the Open-LLM-VTuber community
