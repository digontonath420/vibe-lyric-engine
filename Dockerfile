FROM python:3.12-slim

# Install FFmpeg + fonts (Noto for Devanagari, Liberation fallback)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fontconfig \
    fonts-liberation \
    fonts-noto \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure downloads folder exists
RUN mkdir -p downloads

ENV PORT=5000
EXPOSE 5000

# Shell form to expand $PORT
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 180 app:app
