FROM python:3.9-slim

# System dependencies (FFmpeg, Fontconfig aur Fonts video lyrics ke liye)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fontconfig \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pehle requirements copy karke packages install karenge
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baaki saara project code copy karenge
COPY . .

# Render ke liye port setup
ENV PORT=5000
EXPOSE 5000

# Gunicorn command (120 seconds timeout ke sath taaki video poori render ho sake)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "--timeout", "120", "app:app"]
