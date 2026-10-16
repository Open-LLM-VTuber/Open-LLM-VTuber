# Free Cloud-Based LLM Directory

A comprehensive directory of cloud-based LLM providers offering free tiers, suitable for Open-LLM-VTuber and other AI applications.

## Quick Reference

| Provider | API Endpoint | Auth | Free Tier | Rate Limit | Best For |
|---|---|---|---|---|---|
| **Google Gemini** | `https://generativelanguage.googleapis.com/v1beta` | API Key | Yes | 60 RPM (free) | Multimodal, high context |
| **Groq** | `https://api.groq.com/openai/v1` | API Key | Yes | 14 RPM (free) | Ultra-low latency |
| **OpenRouter** | `https://openrouter.ai/api/v1` | API Key | Yes | Varies | Model marketplace |
| **Cloudflare Workers AI** | `https://api.cloudflare.com/client/v4/accounts/{id}/ai/run` | API Token | Yes | 10K req/day | Edge deployment |
| **Mistral** | `https://api.mistral.ai/v1` | API Key | Yes | 10 RPM (free) | European privacy |
| **Cohere** | `https://api.cohere.ai/v1` | API Key | Yes | 10 RPM (free) | Enterprise RAG |
| **Hugging Face** | `https://api-inference.huggingface.co/models/{id}` | Bearer Token | Yes | 30 req/min | Open model access |

---

## 1. Google Gemini

**URL:** https://aistudio.google.com  
**Console:** https://console.cloud.google.com/ai  
**API Docs:** https://ai.google.dev

### Authentication
- Create a Google Cloud Project
- Enable Generative Language API
- Create an API key or use OAuth 2.0

### Free Tier
- **Gemini 1.5 Flash**: Free tier available with 60 requests/minute
- **Gemini 1.5 Pro**: Free trial credits ($300 for 90 days)
- **Gemini 2.0 Flash**: Available via API with free tier

### Key Models
| Model | Context Window | Strength |
|---|---|---|
| Gemini 2.0 Flash | 1M tokens | Fast, multimodal |
| Gemini 1.5 Pro | 2M tokens | Deep reasoning |
| Gemini 1.5 Flash | 1M tokens | Cost-effective |
| Gemini Nano | On-device | Lightweight |

### Endpoints
```python
# Chat completion
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=YOUR_KEY

# Embeddings
POST https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key=YOUR_KEY
```

### Rate Limits
- Free tier: 60 RPM, 600 requests/hour
- 1.5 Pro: Rate-limited based on usage

### Notes
- Best multimodal support (text, image, audio, video)
- Largest context window available
- Integrated with Google Cloud ecosystem
- Supports function calling and tool use

---

## 2. Groq

**URL:** https://groq.com  
**Console:** https://console.groq.com  
**API Docs:** https://docs.groq.com

### Authentication
- Sign up at console.groq.com
- Create an API key (starts with `gsk_`)

### Free Tier
- **Llama 3.1 70B**: Free inference available
- **Llama 3.1 8B**: Free inference available
- **Mixtral 8x7B**: Free inference available

### Key Models
| Model | Parameters | Speed (tokens/s) | Strength |
|---|---|---|---|
| Llama 3.1 405B | 405B | ~100 | Cutting-edge reasoning |
| Llama 3.1 70B | 70B | ~250 | Strong general purpose |
| Llama 3.1 8B | 8B | ~700 | Fast, efficient |
| Mixtral 8x7B | 47B | ~200 | Balanced performance |
| Gemma 2 9B | 9B | ~500 | Google-designed |

### Endpoints
```python
# Chat completion (OpenAI-compatible)
POST https://api.groq.com/openai/v1/chat/completions
Headers:
  Authorization: Bearer gsk_YOUR_KEY
  Content-Type: application/json

# Request body:
{
  "model": "llama3.1-70b-versatile",
  "messages": [{"role": "user", "content": "Hello"}],
  "max_tokens": 4096
}
```

### Rate Limits
- Free tier: 14 requests/minute (Llama 3.1 70B)
- 30 requests/minute (Llama 3.1 8B)
- Higher limits available with paid plans

### Notes
- **Fastest inference speeds** in the industry (LPU architecture)
- OpenAI-compatible API — drop-in replacement
- Best for latency-sensitive applications
- No streaming overhead — instant first token

---

## 3. OpenRouter

**URL:** https://openrouter.ai  
**Console:** https://openrouter.ai/settings/keys  
**API Docs:** https://docs.openrouter.ai

### Authentication
- Sign up at openrouter.ai
- Create an API key (starts with `sk-or-v1-`)
- Fund wallet (minimum $1 for free trial credits)

### Free Tier
- Access to hundreds of models including open-source
- Some models fully free (no cost per token)
- Others pay-per-token at very low rates ($0.01-0.15/1M tokens)

### Key Models (Free or Near-Free)
| Model | Provider | Cost | Strength |
|---|---|---|---|
| DeepSeek V3 | DeepSeek | Free | Coding, reasoning |
| DeepSeek R1 | DeepSeek | Free | Chain-of-thought |
| Llama 3.1 70B | Meta | Free | General purpose |
| Mistral Large 2 | Mistral | Free | Multilingual |
| Qwen 2.5 72B | Alibaba | Free | Multimodal |
| Command R+ | Cohere | Free | RAG, chat |
| Gemma 2 9B | Google | Free | Lightweight |
| Phi-4 | Microsoft | $0.03/1M | Small, efficient |

### Endpoints
```python
# Chat completion (OpenAI-compatible)
POST https://openrouter.ai/api/v1/chat/completions
Headers:
  Authorization: Bearer sk-or-v1-YOUR_KEY
  HTTP-Referer: YOUR_SITE_URL
  X-Title: YOUR_APP_NAME
```

### Rate Limits
- Varies by model (provider-specific)
- Default: 3000 requests/hour
- Burst: 100 requests/minute

### Notes
- **Largest model marketplace** — access 200+ models via single API
- Smart routing — automatically selects best model per prompt
- Built-in caching — repeated prompts served instantly
- Great for A/B testing different models
- OpenAI-compatible API with extended features

---

## 4. Cloudflare Workers AI

**URL:** https://developers.cloudflare.com/workers-ai  
**Console:** https://dash.cloudflare.com  
**API Docs:** https://developers.cloudflare.com/workers-ai/run-models

### Authentication
- Create a Cloudflare account
- Create a Workers AI namespace
- Generate an API token from dashboard

### Free Tier
- **10,000 AI model runs per day** (free)
- Includes Llama 3.1, Mistral, Whisper, and more
- No credit card required

### Key Models
| Model | Type | Strength |
|---|---|---|
| Llama 3.1 8B/70B | Chat | Open-source |
| Mistral 7B | Chat | Efficient |
| Whisper | ASR | Speech-to-text |
| SoundStorm | TTS | Natural voice |
| Llama 3.1 70B instruct | Chat | Strong reasoning |
| SDXL | Image | Image generation |
| Baai LLM | Embedding | V2 base |

### Endpoints
```python
# Run a model
POST https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_name}
Headers:
  Authorization: Bearer YOUR_API_TOKEN
  Content-Type: application/json

# Example body:
{
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "max_tokens": 1000
}
```

### Rate Limits
- Free: 10,000 requests/day
- 10 requests/minute per model
- Concurrent: 10 requests per model

### Notes
- **Edge deployment** — runs at Cloudflare's 300+ PoPs worldwide
- Lowest latency for globally distributed users
- Built-in ASR and TTS models
- Bundled with Workers/KV/D1 ecosystem
- Great for VTuber apps already on Cloudflare
- No egress fees

---

## 5. Mistral AI

**URL:** https://mistral.ai  
**Console:** https://console.mistral.ai  
**API Docs:** https://docs.mistral.ai

### Authentication
- Sign up at console.mistral.ai
- Create an API key

### Free Tier
- **Codestral**: Free tier available (250 requests/day)
- **Mistral Small**: Free tier available
- **Mistral Large**: Free trial credits

### Key Models
| Model | Parameters | Strength |
|---|---|---|
| Mistral Large 2 | 123B | Top-tier reasoning |
| Mistral Medium | Proprietary | Balanced |
| Mistral Small | Proprietary | Fast, cheap |
| Codestral | 22B | Best coding model |
| Pixtral | 124B | Multimodal (vision) |
| Mistral 7B | 7B | Efficient open-source |

### Endpoints
```python
# Chat completion (OpenAI-compatible)
POST https://api.mistral.ai/v1/chat/completions
Headers:
  Authorization: Bearer YOUR_API_KEY
  Content-Type: application/json
```

### Rate Limits
- Free tier: 10 requests/minute
- 30 requests/minute (paid)
- Codestral free: 250 requests/day

### Notes
- **European AI leader** — GDPR compliant by design
- Excellent multilingual support (23 languages)
- Strong coding capabilities (Codestral)
- Mixtral MoE architecture for efficiency
- Vision model support (Pixtral)

---

## 6. Cohere

**URL:** https://cohere.com  
**Console:** https://console.cohere.com  
**API Docs:** https://docs.cohere.com

### Authentication
- Sign up at console.cohere.com
- Create an API key

### Free Tier
- **Cohere Create trial**: Free for developers ($10 monthly credits)
- **Cohere Command R+**: Free trial tier
- **Embed models**: Always free (up to limits)

### Key Models
| Model | Strength |
|---|---|
| Command R+ | Enterprise chat, RAG |
| Command R | Multilingual chat |
| Cohere Embed English | Text embeddings |
| Cohere Embed Multilingual | 100+ language embeddings |
| Command R+ 104K | Long context (104K tokens) |

### Endpoints
```python
# Chat completion
POST https://api.cohere.com/v1/chat
Headers:
  Authorization: Bearer YOUR_API_KEY
  Content-Type: application/json

# Request body:
{
  "model": "command-r-plus",
  "messages": [{"role": "user", "content": "Hello"}],
  "max_tokens": 4096
}
```

### Rate Limits
- Free tier: 10 requests/minute
- Embed endpoints: Higher limits
- Rate limits vary by model

### Notes
- **Best-in-class RAG** and retrieval capabilities
- Excellent for enterprise applications
- Strong multilingual support (100+ languages)
- Built-in guardrails for safety
- Cohere's RAG system is the industry benchmark
- Good for knowledge-grounded VTuber responses

---

## 7. Hugging Face Inference API

**URL:** https://huggingface.co  
**Console:** https://huggingface.co/settings/tokens  
**API Docs:** https://docs.huggingface.co/inference

### Authentication
- Create a Hugging Face account
- Create an access token (starts with `hf_`)

### Free Tier
- **Inference API**: Free for most models
- **Inference Endpoints**: Free trial ($0 for 30 days on Serverless)
- **Hugging Face Hub**: Access to 500,000+ models

### Key Models (Free on Inference API)
| Model | Type | Strength |
|---|---|---|
| Llama 3.1 8B | Chat | Open-source |
| Mistral 7B | Chat | Efficient |
| Qwen 2.5 72B | Chat | Multimodal |
| DeepSeek V3 | Chat | Reasoning |
| Gemma 2 9B | Chat | Google-quality |
| Phi-4 | Chat | Small, fast |
| SmolLM2 | Chat | Ultra-efficient |
| Zephyr 7B | Chat | Aligned |
| All-MiniLM | Embedding | Text embeddings |
| Whisper | ASR | Speech recognition |

### Endpoints
```python
# Text generation via Inference API
POST https://api-inference.huggingface.co/models/{model_id}
Headers:
  Authorization: Bearer hf_YOUR_TOKEN
  Content-Type: application/json

# Chat completion (via Together or other providers on HF)
POST https://api-inference.huggingface.co/v1/chat/completions
```

### Rate Limits
- Free Inference API: 30 requests/minute
- Cold start: 5-30 seconds for first request
- Burst: Limited concurrent requests

### Notes
- **Access to 500,000+ models** including latest open-source releases
- Community-driven — users can publish and share models
- Often the first to access new models (day-zero availability)
- Great for testing models before committing
- Free CPU inference for most models
- Pay-per-token GPU inference available
- Transformers.js for browser-based inference

---

## Provider Comparison Matrix

### Latency (First Token)
| Provider | First Token (ms) | Notes |
|---|---|---|
| Groq | 50-150 | Fastest — LPU architecture |
| Cloudflare Workers AI | 100-300 | Edge-deployed globally |
| Google Gemini | 200-500 | Highly variable by model |
| Mistral | 200-500 | Direct from provider |
| OpenRouter | 200-800 | Depends on underlying model |
| Cohere | 300-600 | Optimized for RAG |
| Hugging Face | 500-5000 | CPU cold start can be slow |

### Context Window
| Provider | Max Context | Models |
|---|---|---|
| Google Gemini | 2M tokens | Gemini 1.5 Pro |
| Cohere | 104K tokens | Command R+ |
| OpenRouter | 128K tokens | Multiple providers |
| Mistral | 128K tokens | Mistral Large |
| Groq | 128K tokens | Llama 3.1 |
| Cloudflare | 128K tokens | Llama 3.1 |
| Hugging Face | 128K tokens | Model-dependent |

### Multimodal Support
| Provider | Text | Image | Audio | Video |
|---|---|---|---|---|
| Google Gemini | Yes | Yes | Yes | Yes |
| Mistral (Pixtral) | Yes | Yes | No | No |
| Cloudflare | Yes | No | Yes (Whisper/TTS) | No |
| OpenRouter | Yes | Some | No | No |
| Groq | Yes | No | No | No |
| Cohere | Yes | No | No | No |
| Hugging Face | Yes | Some | Some | No |

---

## Recommendation for Open-LLM-VTuber

### Primary LLM (for VTuber brain)
- **Groq** (Llama 3.1 70B) — Fastest response times for conversational AI
- Fallback: Google Gemini Flash for multimodal needs

### Secondary LLM (for complex reasoning)
- **Google Gemini 1.5 Pro** — Long context for conversation history
- Fallback: Mistral Large

### Embeddings/RAG
- **Cohere Embed** — Best RAG performance
- Fallback: Hugging Face All-MiniLM-L6-V2 (free, local)

### ASR (Speech-to-Text)
- **Cloudflare Workers AI Whisper** — Edge ASR
- Fallback: Hugging Face Whisper API

### TTS (Text-to-Speech)
- **Cloudflare Workers AI SoundStorm** — Edge TTS
- Fallback: ElevenLabs (paid)

### Testing/Sandbox
- **OpenRouter** — Access to all models for comparison
- **Hugging Face** — Day-zero open-source model access

---

## Getting Started Script

```python
import requests

PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "auth": "Bearer gsk_YOUR_GROQ_KEY",
        "model": "llama3.1-70b-versatile",
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
        "auth": "key=YOUR_GEMINI_KEY",
        "model": "gemini-2.0-flash",
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/chat/completions",
        "auth": "Bearer YOUR_MISTRAL_KEY",
        "model": "mistral-small-latest",
    },
}

def chat(provider: str, message: str, max_tokens: int = 1024) -> str:
    cfg = PROVIDERS[provider]
    body = {"model": cfg["model"], "messages": [{"role": "user", "content": message}], "max_tokens": max_tokens}
    headers = {"Authorization": cfg["auth"], "Content-Type": "application/json"}
    resp = requests.post(cfg["url"], json=body, headers=headers)
    return resp.json()["choices"][0]["message"]["content"]

# Try all providers
for name in PROVIDERS:
    response = chat(name, "Hello, who are you?")
    print(f"{name}: {response[:100]}...")
```

---

## Price Comparison (Per 1M Tokens)

| Model | Input | Output | Provider |
|---|---|---|---|
| Gemini 2.0 Flash | $0.10 | $0.40 | Google |
| Gemini 1.5 Pro | $2.50 | $10.00 | Google |
| Llama 3.1 70B | $0.27 | $0.27 | Groq |
| Llama 3.1 8B | $0.04 | $0.04 | Groq |
| Mistral Small | $0.25 | $0.25 | Mistral |
| Command R+ | $0.30 | $1.50 | Cohere |
| DeepSeek V3 (free) | $0.00 | $0.00 | OpenRouter |
| Qwen 2.5 72B (free) | $0.00 | $0.00 | OpenRouter |

---

## Notes

- All prices and rate limits are subject to change — check provider dashboards for current values
- Free tiers may require account verification or credit card on file
- Some providers offer student/non-profit discounts
- OpenRouter and Hugging Face aggregate models from multiple sources — availability varies
- Enterprise plans available for all providers with SLAs, dedicated instances, and custom deployments

---

*Last updated: 2026-09-23*
