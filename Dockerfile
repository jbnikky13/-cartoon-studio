FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV LIBGL_ALWAYS_SOFTWARE=1

RUN apt-get update && apt-get install -y \
    blender \
    ffmpeg \
    xvfb \
    libegl1 \
    libgl1 \
    libgles2 \
    libgbm1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxi6 \
    libxfixes3 \
    libxkbcommon0 \
    libfontconfig1 \
    libfreetype6 \
    libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/projects /app/output

EXPOSE 8501

CMD ["sh", "-c", "streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true"]
