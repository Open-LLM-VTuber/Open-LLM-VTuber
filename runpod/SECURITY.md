# Security Configuration Guide

This guide explains how to secure your Open-LLM-VTuber deployment on RunPod.

## Available Security Features

### 1. API Key Authentication

Protect your deployment with API key authentication.

**Enable:**
```bash
export API_KEY="your-secret-key-here"
```

Or in `.env` file:
```
API_KEY=your-secret-key-here
```

**Usage from clients:**

Option 1 - Authorization Header:
```javascript
const ws = new WebSocket('wss://your-pod.runpod.net/client-ws', {
    headers: {
        'Authorization': 'Bearer your-secret-key-here'
    }
});
```

Option 2 - Query Parameter:
```javascript
const ws = new WebSocket('wss://your-pod.runpod.net/client-ws?api_key=your-secret-key-here');
```

Option 3 - Custom Header:
```javascript
fetch('https://your-pod.runpod.net/api', {
    headers: {
        'X-API-Key': 'your-secret-key-here'
    }
});
```

### 2. Enable Security Middleware (Manual Integration)

To enable the security middleware, modify your `server.py`:

```python
from .security_middleware import (
    APIKeyMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMiddleware
)

# In WebSocketServer.__init__, after creating self.app:

# Add security headers
self.app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting (100 requests per minute per IP)
self.app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,
    window_seconds=60
)

# Add API key authentication (if API_KEY env var is set)
self.app.add_middleware(APIKeyMiddleware)
```

For WebSocket authentication, modify your WebSocket handler:

```python
from .security_middleware import verify_websocket_auth

@router.websocket("/client-ws")
async def client_websocket(websocket: WebSocket):
    # Verify authentication
    if not await verify_websocket_auth(websocket):
        await websocket.close(code=1008)  # Policy violation
        return

    # Continue with normal WebSocket handling
    await websocket.accept()
    # ... rest of your code
```

### 3. HTTPS/WSS (via RunPod Proxy)

RunPod automatically provides HTTPS/WSS through their proxy:

- HTTP: `https://[POD-ID]-12393.proxy.runpod.net`
- WebSocket: `wss://[POD-ID]-12393.proxy.runpod.net/client-ws`

No additional configuration needed!

### 4. Network Security

**Firewall Rules:**
- Only expose port 12393 (application port)
- Do NOT expose 11434 (Ollama) to the internet
- Keep SSH access restricted

**In docker-compose.yml:**
```yaml
services:
  ollama:
    ports:
      - "127.0.0.1:11434:11434"  # Only expose to localhost
    # NOT: "11434:11434" (would expose to internet)
```

### 5. Environment Variables Security

**NEVER** commit `.env` files with secrets!

Add to `.gitignore`:
```
.env
.env.*
!.env.example
```

**Create `.env.example`:**
```
# Copy this file to .env and fill in your values

# API Keys (optional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=

# Security
API_KEY=

# Ollama Model
OLLAMA_MODEL=qwen2.5:32b
```

### 6. RunPod-Specific Security

**Storage:**
- Use RunPod Network Volumes for persistent data
- Enable volume encryption if handling sensitive data

**Pod Configuration:**
- Use private templates (don't make public)
- Restrict SSH access to your IP
- Enable pod auto-stop when idle

**Monitoring:**
- Regularly check RunPod logs for suspicious activity
- Monitor bandwidth usage for anomalies
- Set up alerts for unexpected GPU usage

## Security Checklist

- [ ] Set `API_KEY` environment variable
- [ ] Use HTTPS/WSS (RunPod proxy provides this)
- [ ] Don't expose Ollama port (11434) publicly
- [ ] Use `.gitignore` for `.env` files
- [ ] Enable security middleware
- [ ] Set up rate limiting
- [ ] Monitor logs regularly
- [ ] Use strong API keys (minimum 32 characters)
- [ ] Rotate API keys periodically
- [ ] Keep dependencies updated

## Generating Secure API Keys

```bash
# Linux/Mac
openssl rand -base64 32

# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
```

## Security Best Practices

1. **Use Strong Authentication**: Always set API_KEY in production
2. **HTTPS Only**: Never use HTTP/WS in production (use RunPod proxy)
3. **Principle of Least Privilege**: Only expose necessary ports
4. **Regular Updates**: Keep dependencies and base images updated
5. **Monitoring**: Set up logging and monitoring
6. **Backup**: Regularly backup chat history and configurations
7. **Incident Response**: Have a plan for security incidents

## Reporting Security Issues

If you discover a security vulnerability, please report it to:
- GitHub Security Advisories: https://github.com/t41372/Open-LLM-VTuber/security/advisories

Do NOT create public issues for security vulnerabilities.
