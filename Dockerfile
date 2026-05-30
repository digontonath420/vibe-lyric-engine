FROM python:3.11-slim

# Video aur lyrics ke liye saare zaroori tools install karenge
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fontconfig \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Sabse pehle pip ko upgrade karenge taaki koi package error na de
RUN pip install --no-cache-dir --upgrade pip

# Requirements copy karke install karenge
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baaki saara code copy karenge
COPY . .

# Render ka port setup
ENV PORT=5000
EXPOSE 5000

# Gunicorn command (120 seconds timeout ke sath)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "--timeout", "120", "app:app"]
