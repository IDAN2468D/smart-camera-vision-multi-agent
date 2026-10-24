# Multi-Agent Python Backend Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HEADLESS=true \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5000

# Install Linux system dependencies required by OpenCV & Media
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies and Playwright Chromium
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium && \
    playwright install-deps chromium

# Copy backend application source
COPY config/ ./config/
COPY models/ ./models/
COPY dal/ ./dal/
COPY agents/ ./agents/
COPY services/ ./services/
COPY controllers/ ./controllers/
COPY main.py .
COPY .env .

# Expose Flask API port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Start Flask & Multi-Agent System
CMD ["python", "main.py"]
