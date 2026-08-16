# ============================================================
# CARTOON STUDIO
# Streamlit + Blender 4.3.2
# Render Web Service
# ============================================================

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# ============================================================
# SYSTEM PACKAGES
# ============================================================

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    xz-utils \
    ffmpeg \
    libgl1 \
    libegl1 \
    libgles2 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxi6 \
    libxxf86vm1 \
    libxfixes3 \
    libxkbcommon0 \
    libfontconfig1 \
    libfreetype6 \
    libdbus-1-3 \
    libwayland-client0 \
    libwayland-egl1 \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# BLENDER
# ============================================================

WORKDIR /opt

RUN wget -q \
    https://download.blender.org/release/Blender4.3/blender-4.3.2-linux-x64.tar.xz \
    -O /tmp/blender.tar.xz \
    && tar -xJf /tmp/blender.tar.xz \
    && rm /tmp/blender.tar.xz \
    && ln -s /opt/blender-4.3.2-linux-x64/blender /usr/local/bin/blender

RUN blender --version

# ============================================================
# APPLICATION
# ============================================================

WORKDIR /app

COPY . /app

# ============================================================
# PYTHON DEPENDENCIES
# ============================================================

RUN python -m pip install --no-cache-dir \
    streamlit \
    pillow \
    imageio-ffmpeg

# ============================================================
# DIRECTORIES
# ============================================================

RUN mkdir -p \
    /app/output \
    /app/uploads \
    /app/tmp

# ============================================================
# BLENDER ENVIRONMENT
# ============================================================

ENV BLENDER_BIN=/usr/local/bin/blender
ENV HOME=/tmp
ENV BLENDER_USER_CONFIG=/tmp/blender-config
ENV BLENDER_USER_SCRIPTS=/tmp/blender-scripts

# ============================================================
# STREAMLIT ENVIRONMENT
# ============================================================

ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# ============================================================
# RENDER PORT
# ============================================================

EXPOSE 10000

# ============================================================
# START STREAMLIT
# ============================================================

CMD ["sh", "-c", "exec streamlit run /app/app.py --server.address=0.0.0.0 --server.port=${PORT:-10000} --server.headless=true --browser.gatherUsageStats=false"]
