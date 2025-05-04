# Dockerfile
FROM python:3.10-slim

# Install FFmpeg and dependencies
RUN apt update && apt install -y ffmpeg

# Set working dir
WORKDIR /app

# Copy files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Env for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_PORT=10000
ENV FLASK_RUN_HOST=0.0.0.0

# Create necessary directories
RUN mkdir -p uploads/youtube

# Start Flask server
CMD ["flask", "run", "--host=0.0.0.0", "--port=10000"] 