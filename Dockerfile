FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV BLENDER_PATH=blender
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        blender \
        ffmpeg \
        ca-certificates \
        libegl1 \
        libgl1 \
        libglx-mesa0 \
        libopengl0 \
        libgles2 \
        libx11-6 \
        libxext6 \
        libxrender1 \
        libxi6 \
        libxfixes3 \
        libxkbcommon0 \
        libsm6 \
        libice6 \
        libfontconfig1 \
        libfreetype6 \
        && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/projects /app/output

EXPOSE 8501

CMD streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true
