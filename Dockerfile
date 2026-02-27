FROM python:3.12-slim

WORKDIR /app

# Install necessary system dependencies (ffmpeg for video merging, aria2 for fast downloads, build-essential for tgcrypto)
RUN apt-get update && \
    apt-get install -y ffmpeg aria2 build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Run the bot with unbuffered output so Render logs work in real-time
CMD ["python", "-u", "bot.py"]
