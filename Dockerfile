# ============================================================
# CARTOON STUDIO — RENDER-SAFE BLENDER CONTAINER
# Blender 4.3.2 + Python 3.11 + Streamlit
# Headless/software rendering for Render.com
# ============================================================

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# ------------------------------------------------------------
# System dependencies
# ------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    xz-utils \
    ffmpeg \
    xvfb \
    mesa-utils \
    libgl1 \
    libegl1 \
    libgles2 \
    libglvnd0 \
    libglu1-mesa \
    libx11-6 \
    libx11-xcb1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrender1 \
    libxrandr2 \
    libxkbcommon0 \
    libxkbcommon-x11-0 \
    libsm6 \
    libice6 \
    libfontconfig1 \
    libfreetype6 \
    libdbus-1-3 \
    libnss3 \
    libwayland-client0 \
    libwayland-egl1 \
    libwayland-cursor0 \
    libdecor-0-plugin-1-cairo \
    libglib2.0-0 \
    libgomp1 \
    libstdc++6 \
    libgcc-s1 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Install Blender 4.3.2
# ------------------------------------------------------------
WORKDIR /opt

RUN wget -q \
    https://download.blender.org/release/Blender4.3/blender-4.3.2-linux-x64.tar.xz \
    -O /tmp/blender.tar.xz \
    && tar -xJf /tmp/blender.tar.xz -C /opt \
    && rm /tmp/blender.tar.xz \
    && ln -s /opt/blender-4.3.2-linux-x64/blender /usr/local/bin/blender

# Verify Blender installation during image build
RUN blender --version

# ------------------------------------------------------------
# Force software rendering
# ------------------------------------------------------------
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
ENV GALLIUM_DRIVER=llvmpipe
ENV EGL_PLATFORM=surfaceless

# Blender configuration
ENV BLENDER_USER_CONFIG=/tmp/blender-config
ENV BLENDER_USER_DATAFILES=/tmp/blender-data
ENV BLENDER_USER_SCRIPTS=/tmp/blender-scripts

# Prevent GUI/audio-related problems
ENV SDL_VIDEODRIVER=dummy
ENV SDL_AUDIODRIVER=dummy

# Virtual display fallback
ENV DISPLAY=:99

# ------------------------------------------------------------
# Application
# ------------------------------------------------------------
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# ------------------------------------------------------------
# Required directories
# ------------------------------------------------------------
RUN mkdir -p \
    /app/projects \
    /app/output \
    /tmp/blender-config \
    /tmp/blender-data \
    /tmp/blender-scripts

# ------------------------------------------------------------
# Make Blender executable available everywhere
# ------------------------------------------------------------
ENV PATH="/opt/blender-4.3.2-linux-x64:${PATH}"

# ------------------------------------------------------------
# Render port
# Render supplies $PORT automatically.
# ------------------------------------------------------------
EXPOSE 10000

# ------------------------------------------------------------
# Start:
# 1. Create a virtual X display
# 2. Start Streamlit on Render's PORT
#
# Xvfb provides a virtual display as an additional fallback
# for Blender components that expect an X11 display.
# ------------------------------------------------------------
CMD ["sh", "-c", "Xvfb :99 -screen 0 1280x720x24 -ac >/tmp/xvfb.log 2>&1 & exec streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-10000} --server.headless=true --browser.gatherUsageStats=false"]
