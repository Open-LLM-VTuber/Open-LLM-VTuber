# Base image
FROM nvidia/cuda:12.6.0-cudnn-runtime-ubuntu22.04 AS base

# Set noninteractive mode for apt
ENV DEBIAN_FRONTEND=noninteractive

# Update and install dependencies
RUN apt-get -o Acquire::AllowInsecureRepositories=true update && \
    apt-get install -y libxcb-xfixes0 libxcb-shape0 || true && \
    apt-get install -y --no-install-recommends ffmpeg || true && \
    apt --fix-broken install -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements and install common dependencies
COPY requirements.txt /tmp/

# Install pip
RUN curl https://bootstrap.pypa.io/get-pip.py | python3 - && \
    pip install --root-user-action=ignore --no-cache-dir -r /tmp/requirements.txt && \
    pip install --root-user-action=ignore --no-cache-dir funasr modelscope huggingface_hub pywhispercpp torch torchaudio edge-tts azure-cognitiveservices-speech py3-tts

# MeloTTS installation
WORKDIR /opt/MeloTTS
RUN git clone https://github.com/myshell-ai/MeloTTS.git /opt/MeloTTS && \
    pip install --root-user-action=ignore --no-cache-dir -e . && \
    python3 -m unidic download && \
    python3 melo/init_downloads.py

# Whisper variant
FROM base AS whisper
ARG INSTALL_ORIGINAL_WHISPER=false
RUN if [ "$INSTALL_WHISPER" = "true" ]; then \
        pip install --root-user-action=ignore --no-cache-dir openai-whisper; \
    fi

# Bark variant
FROM whisper AS bark
ARG INSTALL_BARK=false
RUN if [ "$INSTALL_BARK" = "true" ]; then \
        pip install --root-user-action=ignore --no-cache-dir git+https://github.com/suno-ai/bark.git; \
    fi

# Final image
FROM bark AS final

# Copy application code to the container
COPY . /app

# Set working directory
WORKDIR /app

# Expose port 12393 (the new default port)
EXPOSE 12393

CMD ["python3", "server.py"]
