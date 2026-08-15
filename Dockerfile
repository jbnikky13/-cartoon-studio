FROM python:3.12-slim

# Prevent interactive package prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Blender, FFmpeg and required system libraries
RUN apt-get update && apt-get install -y \
    blender \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxi6 \
    libxfixes3 \
    libxkbcommon0 \
    libfontconfig1 \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# Application directory
WORKDIR /app

# Install Python dependencies first for better Docker caching
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the complete project
COPY . .

# Create directories used by the application
RUN mkdir -p /app/projects /app/output

# Render uses its own PORT environment variable
EXPOSE 8501

# Start Streamlit using Render's assigned PORT
CMD streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true
