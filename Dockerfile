# ──────────────────────────────────────────────────────────────────────────────
# DealMate / AgentMate Runtime Image
# ──────────────────────────────────────────────────────────────────────────────
FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime

WORKDIR /app

# 1. System libs:
#    • libgl1 + libglib2.0-0 are required by PyMuPDF (fitz)
#    • ffmpeg for Whisper audio handling
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 ffmpeg curl git && \
    rm -rf /var/lib/apt/lists/*

# 2. Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Application code
COPY . /app

# 4. Temp dir for large files / scratch
RUN mkdir -p /tmp/dealmate

EXPOSE 8000

# 5. Health check (RunPod will restart if curl fails)
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 6. Launch Flask on the public interface
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8000"]
