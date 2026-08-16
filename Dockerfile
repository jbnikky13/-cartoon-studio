# ============================================================
# CARTOON STUDIO
# Render-safe Streamlit + Blender container
# ============================================================

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# ------------------------------------------------------------
# SYSTEM DEPENDENCIES
# ------------------------------------------------------------

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ca-certificates \
    xz-utils \
    bzip2 \
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
    libharfbuzz0b \
    libwayland-client0 \
    libwayland-egl1 \
    libdecor-0-0 \
    mesa-utils \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# BLENDER 4.3.2
# ------------------------------------------------------------

WORKDIR /opt

RUN wget -q \
    https://download.blender.org/release/Blender4.3/blender-4.3.2-linux-x64.tar.xz \
    -O blender.tar.xz \
    && tar -xf blender.tar.xz \
    && rm blender.tar.xz \
    && ln -s /opt/blender-4.3.2-linux-x64/blender /usr/local/bin/blender

# Verify Blender installation during build
RUN blender --version

# ------------------------------------------------------------
# APPLICATION
# ------------------------------------------------------------

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY . /app

# ------------------------------------------------------------
# DIRECTORIES
# ------------------------------------------------------------

RUN mkdir -p \
    /app/output \
    /app/tmp \
    /app/uploads

# ------------------------------------------------------------
# ENVIRONMENT
# ------------------------------------------------------------

ENV HOME=/tmp
ENV BLENDER_USER_CONFIG=/tmp/blender-config
ENV BLENDER_USER_SCRIPTS=/tmp/blender-scripts

# Streamlit configuration
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Render normally supplies PORT=10000.
# This is only the fallback.
ENV PORT=10000

# ------------------------------------------------------------
# RENDER WEB PORT
# ------------------------------------------------------------

EXPOSE 10000

# ------------------------------------------------------------
# IMPORTANT:
# Streamlit is the WEB SERVER.
# Blender is launched by app.py only when rendering.
# ------------------------------------------------------------

CMD ["sh", "-c", "exec streamlit run /app/app.py --server.address=0.0.0.0 --server.port=${PORT:-10000}"]
