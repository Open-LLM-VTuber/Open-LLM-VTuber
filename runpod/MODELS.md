# Model Configuration Guide for RTX-5090

This guide explains the optimized configurations available for RunPod deployment.

## 📂 Available Configurations

We provide 5 pre-configured setups optimized for different use cases:

| Config | VRAM | Speed | Quality | Cost/Hr* | Best For |
|--------|------|-------|---------|----------|----------|
| **Budget** | 6GB | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | $0.60 | Testing, casual use |
| **Performance** | 10GB | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | $1.00 | Fast interactions |
| **Balanced** | 18GB | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | $1.50 | **Recommended** |
| **Quality** | 22GB | ⚡⚡ | ⭐⭐⭐⭐⭐ | $2.00 | Best quality |
| **Multilingual** | 18GB | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | $1.50 | Multi-language |

*Estimated RunPod spot instance pricing

## 🎯 Quick Start

### Using a Configuration

**Method 1: Set in conf.runpod.yaml**

Edit the main configuration file:
```yaml
character_config:
  conf_name: 'rtx5090_balanced'  # or performance, quality, etc.
```

**Method 2: Use Character Switching**

The system supports loading different configurations:
```yaml
system_config:
  config_alts_dir: 'characters'
```

Then switch via web interface or API.

**Method 3: Environment Variable**

```bash
export CHARACTER_CONFIG=rtx5090-performance
```

## 📊 Detailed Configuration Comparison

### 1️⃣ Budget Mode (`rtx5090-budget.yaml`)

**Use Case:** Minimize costs, testing, light usage

**Specs:**
- LLM: Qwen2.5-7B (~5GB VRAM)
- ASR: Faster-Whisper Small (~500MB VRAM)
- TTS: Edge TTS (cloud, free)
- Total VRAM: ~6GB

**Performance:**
- First Response: ~1.2s
- Quality: Good for casual conversations
- Cost: ~$0.60/hr (spot) or $1.20/hr (on-demand)

**Best For:**
- Testing and development
- Budget-conscious users
- Simple Q&A tasks
- Can run on RTX 3060 or higher

**Trade-offs:**
- Less nuanced responses
- Lower transcription accuracy
- Cloud-dependent TTS

### 2️⃣ Performance Mode (`rtx5090-performance.yaml`)

**Use Case:** Fast responses with good quality

**Specs:**
- LLM: Qwen2.5-14B (~9GB VRAM)
- ASR: Faster-Whisper Medium (~1GB VRAM)
- TTS: Edge TTS (cloud, free)
- Total VRAM: ~10GB

**Performance:**
- First Response: ~1.5s
- Quality: Very good for most tasks
- Cost: ~$1.00/hr (spot)

**Best For:**
- Real-time conversations
- Interactive demos
- Streaming/content creation
- Users prioritizing responsiveness

**Trade-offs:**
- Slightly less sophisticated responses than 32B/70B models
- Medium ASR may miss some words

### 3️⃣ Balanced Mode (`rtx5090-balanced.yaml`) ⭐ RECOMMENDED

**Use Case:** Best overall experience for most users

**Specs:**
- LLM: Qwen2.5-32B (~18GB VRAM)
- ASR: Faster-Whisper Large-v3-turbo (~2GB VRAM)
- TTS: MeloTTS GPU-accelerated (~1GB VRAM)
- Total VRAM: ~18GB

**Performance:**
- First Response: ~2s
- Quality: Excellent for all tasks
- Cost: ~$1.50/hr (spot)

**Best For:**
- General purpose use
- Production deployments
- Professional applications
- Best price/performance ratio

**Why Recommended:**
- Excellent quality without sacrificing too much speed
- Fully GPU-accelerated (no cloud dependencies)
- Fits comfortably on RTX-5090
- Good for extended conversations

### 4️⃣ Quality Mode (`rtx5090-quality.yaml`)

**Use Case:** Maximum quality, professional use

**Specs:**
- LLM: Llama-3.3-70B-Q4 (~20GB VRAM)
- ASR: Faster-Whisper Large-v3 (~2GB VRAM)
- TTS: MeloTTS GPU-accelerated (~1GB VRAM)
- Total VRAM: ~22GB

**Performance:**
- First Response: ~3s
- Quality: Best possible (on-device)
- Cost: ~$2.00/hr (spot)

**Best For:**
- Professional applications
- Content creation
- Complex reasoning tasks
- Users who prioritize quality over speed

**Features:**
- Most sophisticated responses
- Best transcription accuracy
- MCP tools enabled for enhanced capabilities
- Natural voice synthesis

### 5️⃣ Multilingual Mode (`rtx5090-multilingual.yaml`)

**Use Case:** Multi-language support (EN, JA, ZH, KO)

**Specs:**
- LLM: Qwen2.5-32B (~18GB VRAM)
- ASR: Sherpa-ONNX SenseVoice (~1GB VRAM)
- TTS: Edge TTS or MeloTTS multilingual
- Total VRAM: ~18GB

**Performance:**
- First Response: ~2.5s
- Quality: Excellent in all supported languages
- Cost: ~$1.50/hr (spot)

**Supported Languages:**
- English (en)
- Japanese (ja)
- Chinese (zh)
- Korean (ko)
- Cantonese (yue)

**Best For:**
- International users
- Language learning
- Cross-cultural communication
- Japanese VTuber content

**Features:**
- Auto-language detection
- Native speaker quality in all languages
- Optional translation (speak in one language, AI responds in another)

## 🔄 Switching Configurations

### During Initial Setup

1. **Copy desired config:**
   ```bash
   cp characters/rtx5090-balanced.yaml conf.runpod.yaml
   ```

2. **Or edit existing config:**
   ```yaml
   # In conf.runpod.yaml
   character_config:
     conf_name: 'rtx5090_balanced'
   ```

3. **Rebuild Docker image:**
   ```bash
   ./deploy.sh build
   ```

### After Deployment (RunPod)

1. **SSH into pod:**
   ```bash
   # Use RunPod web terminal
   ```

2. **Edit configuration:**
   ```bash
   cd /workspace
   cp characters/rtx5090-performance.yaml conf.yaml
   ```

3. **Restart service:**
   ```bash
   docker-compose restart open-llm-vtuber
   ```

### Using Environment Variables

```bash
# In .env file
CHARACTER_CONFIG=rtx5090-quality
OLLAMA_MODEL=llama3.3:70b-instruct-q4_K_M
```

## 🎨 Creating Custom Configurations

### Template

```yaml
character_config:
  conf_name: 'my_custom_config'
  conf_uid: 'custom_001'

  agent_config:
    agent_settings:
      basic_memory_agent:
        llm_provider: 'ollama_llm'
    llm_configs:
      ollama_llm:
        model: 'your-model-choice'

  asr_config:
    asr_model: 'your-asr-choice'

  tts_config:
    tts_model: 'your-tts-choice'
```

### Best Practices

1. **Match VRAM budget:**
   - 7B model: ~5GB
   - 14B model: ~9GB
   - 32B model: ~18GB
   - 70B-Q4 model: ~20GB

2. **Balance components:**
   - Fast LLM? Use medium ASR, cloud TTS
   - Slow LLM? Use large ASR, GPU TTS for quality

3. **Test incrementally:**
   - Start with budget config
   - Increase model sizes gradually
   - Monitor VRAM usage: `nvidia-smi`

4. **Consider use case:**
   - Casual chat → Budget/Performance
   - Professional → Balanced/Quality
   - Language learning → Multilingual

## 📈 Performance Tuning Tips

### Faster Response

```yaml
faster_first_response: True
segment_method: 'regex'
use_mcpp: False
temperature: 0.7  # Lower = faster generation
```

### Better Quality

```yaml
faster_first_response: False
segment_method: 'pysbd'
use_mcpp: True
temperature: 1.0  # Higher = more creative
```

### Lower VRAM Usage

```yaml
# Use quantized models
model: 'qwen2.5:7b-q4'  # Instead of 'qwen2.5:7b'

# Use INT8 compute
compute_type: 'int8'  # Instead of 'float16'

# Use cloud TTS
tts_model: 'edge_tts'  # Instead of 'melo_tts'
```

### Reduce Latency

```yaml
# Use nearby Ollama server
ollama_llm:
  base_url: 'http://localhost:11434/v1'

# Use faster ASR model
asr_config:
  faster_whisper:
    model_path: 'medium'  # Instead of 'large-v3'
```

## 🔍 Monitoring and Diagnostics

### Check VRAM Usage

```bash
# In RunPod terminal
nvidia-smi

# Watch continuously
watch -n 1 nvidia-smi
```

### Check Model Loading

```bash
# List loaded Ollama models
ollama list

# Check model size
ollama show qwen2.5:32b
```

### Performance Profiling

```bash
# Monitor response times
tail -f /workspace/logs/*.log | grep "Response time"

# Check container stats
docker stats open-llm-vtuber
```

## 🆘 Troubleshooting

### Out of Memory

**Solution:** Use smaller model or higher quantization
```yaml
model: 'qwen2.5:14b'  # Instead of 32b
# Or
model: 'qwen2.5:32b-q4'  # Quantized version
```

### Slow Responses

**Solution:** Enable performance optimizations
```yaml
faster_first_response: True
keep_alive: -1  # Keep model in memory
compute_type: 'int8'  # Faster inference
```

### Poor Quality

**Solution:** Upgrade to larger models
```yaml
model: 'qwen2.5:32b'  # Instead of 14b
model_path: 'large-v3'  # Instead of medium
```

## 📚 Additional Resources

- **Model Downloads:** https://ollama.com/library
- **ASR Models:** https://github.com/k2-fsa/sherpa-onnx/releases
- **TTS Models:** https://github.com/myshell-ai/MeloTTS
- **Voice Samples:** https://speech.microsoft.com/portal/voicegallery

## 🎓 Advanced Topics

### Hybrid Deployments

Mix local and cloud services:
```yaml
llm_provider: 'ollama_llm'  # Local
asr_model: 'groq_whisper_asr'  # Cloud
tts_model: 'edge_tts'  # Cloud
```

Benefits:
- Lower VRAM usage
- Faster startup
- Pay only for LLM GPU time

### Model Quantization

```bash
# Create quantized model
ollama create qwen2.5:32b-q4 -f Modelfile

# Modelfile:
# FROM qwen2.5:32b
# PARAMETER quantization q4_K_M
```

### Multi-Model Setup

```yaml
# Run multiple models
ollama pull qwen2.5:7b
ollama pull qwen2.5:32b
ollama pull llama3.3:70b-q4

# Switch between them via config
```

---

**Questions?** Check the main [README.runpod.md](README.runpod.md) or open an issue on GitHub.
