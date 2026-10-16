# Contributing Guide

Thank you for your interest in contributing to Open-LLM-VTuber! This guide will help you get started.

## Types of Contributions

- **Bug Reports**: Found a bug? Please file an issue with reproduction steps.
- **Feature Requests**: Have an idea? Check existing issues first.
- **Code Contributions**: PRs welcome! See `good first issue` labels.
- **Documentation**: Docs improvements are always appreciated.
- **Model Contributions**: New TTS/ASR/LLM provider integrations.

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/Open-LLM-VTuber.git
cd Open-LLM-VTuber
git remote add upstream https://github.com/Open-LLM-VTuber/Open-LLM-VTuber.git
```

### 2. Setup Development Environment

```bash
# Using uv (recommended)
uv sync

# Or using venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 3. Run Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_nova_core.py -v

# With coverage
pytest tests/ --cov=src/open_llm_vtuber
```

### 4. Code Style

```bash
# Check linting
ruff check .

# Check formatting
ruff format --check .

# Fix formatting
ruff format .
```

### 5. Development Workflow

```bash
# Create a branch
git checkout -b feature/your-feature-name

# Make changes
# ...

# Run tests
pytest tests/ -v

# Commit
git add .
git commit -m "feat: add your feature description"

# Push
git push origin feature/your-feature-name
```

## Architecture Overview

```
src/open_llm_vtuber/
├── agent/          # LLM routing, conversation agents
├── audio/          # TTS, voice processing, effects
├── cache/          # Redis caching layer
├── db/             # Database models & sessions
├── live/           # Stream platforms & moderation
├── memory/         # Fan memory & CRM
├── radar/          # Social monitoring & chat analysis
├── security/       # Rate limiting, validation, spoofing
├── telemetry/      # OpenTelemetry & metrics
├── tts/            # TTS engine interfaces
├── vision/         # Screen watching, gaze, grounding
├── vad/            # Voice activity detection
├── websocket_handler.py
├── routes.py
└── lifecycle.py
```

## Good First Issues

Look for issues tagged `good first issue` - these are specifically chosen for new contributors.

## Contribution Process

1. **Issue Discussion**: For larger features, open an issue first for discussion.
2. **Branch Naming**: Use `feature/`, `fix/`, `docs/`, `test/` prefixes.
3. **PR Requirements**:
   - All tests passing
   - Linting clean (ruff check .)
   - Formatted (ruff format .)
   - Tested (new code must have tests)
4. **Review**: PRs are reviewed within 48 hours.

## Questions?

- **Discord/Zulip**: Join the community for real-time discussion
- **GitHub Issues**: Bug reports and feature requests
- **Weekly Meeting**: Check announcements for schedule

## Code of Conduct

- Be respectful and constructive
- No harassment or discrimination
- Welcome beginners
- Focus on what's best for the community

---

**Thank you for contributing!** 🎙️