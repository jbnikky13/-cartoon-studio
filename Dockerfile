# ============================================================
# CARTOON STUDIO
# BLENDER 4.3.2 + RENDER-SAFE HEADLESS ENVIRONMENT
# ============================================================

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# ------------------------------------------------------------
# SYSTEM PACKAGES
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
    libosmesa6 \
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
# BLENDER 4.3.2
# ------------------------------------------------------------

WORKDIR /opt

RUN wget -q \
    https://download.blender.org/release/Blender4.3/blender-4.3.2-linux-x64.tar.xz \
    -O /tmp/blender.tar.xz \
    && tar -xJf /tmp/blender.tar.xz -C /opt \
    && rm -f /tmp/blender.tar.xz \
    && ln -s /opt/blender-4.3.2-linux-x64/blender /usr/local/bin/blender


# ------------------------------------------------------------
# VERIFY BLENDER
# ------------------------------------------------------------

RUN blender --version


# ------------------------------------------------------------
# SOFTWARE GRAPHICS
# ------------------------------------------------------------

ENV LIBGL_ALWAYS_SOFTWARE=1

ENV MESA_LOADER_DRIVER_OVERRIDE=llvmpipe

ENV GALLIUM_DRIVER=llvmpipe

ENV LIBGL_DRI3_DISABLE=1

ENV MESA_GL_VERSION_OVERRIDE=3.3

ENV MESA_GLSL_VERSION_OVERRIDE=330


# ------------------------------------------------------------
# BLENDER HEADLESS CONFIGURATION
# ------------------------------------------------------------

ENV BLENDER_USER_CONFIG=/tmp/blender-config

ENV BLENDER_USER_DATAFILES=/tmp/blender-data

ENV BLENDER_USER_SCRIPTS=/tmp/blender-scripts


# ------------------------------------------------------------
# VIRTUAL DISPLAY
# ------------------------------------------------------------

ENV DISPLAY=:99

ENV SDL_VIDEODRIVER=dummy

ENV SDL_AUDIODRIVER=dummy


# ------------------------------------------------------------
# APPLICATION
# ------------------------------------------------------------

WORKDIR /app

COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    --upgrade pip \
    && pip install \
    --no-cache-dir \
    -r requirements.txt

COPY . .


# ------------------------------------------------------------
# DIRECTORIES
# ------------------------------------------------------------

RUN mkdir -p \
    /app/output \
    /app/projects \
    /tmp/cartoon_studio \
    /tmp/blender-config \
    /tmp/blender-data \
    /tmp/blender-scripts


# ------------------------------------------------------------
# BLENDER PATH
# ------------------------------------------------------------

ENV PATH="/opt/blender-4.3.2-linux-x64:${PATH}"


# ------------------------------------------------------------
# RENDER PORT
# ------------------------------------------------------------

EXPOSE 10000


# ============================================================
# START APPLICATION
# ============================================================
#
# 1. Start Xvfb virtual display.
# 2. Give Blender a virtual X11 display.
# 3. Force software graphics.
# 4. Start Streamlit.
#
# ============================================================

CMD ["sh", "-c", "Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset >/tmp/xvfb.log 2>&1 & sleep 2; export DISPLAY=:99; export LIBGL_ALWAYS_SOFTWARE=1; export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe; exec streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-10000} --server.headless=true --browser.gatherUsageStats=false"]
