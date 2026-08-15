# ============================================================
# CARTOON STUDIO
# Blender 4.3.2
# Render-safe headless software OpenGL
# ============================================================

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# ------------------------------------------------------------
# SYSTEM DEPENDENCIES
# ------------------------------------------------------------

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    xz-utils \
    ffmpeg \
    xvfb \
    xauth \
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
    libglib2.0-0 \
    libgomp1 \
    libstdc++6 \
    libgcc-s1 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*


# ------------------------------------------------------------
# BLENDER
# ------------------------------------------------------------

WORKDIR /opt

RUN wget -q \
    https://download.blender.org/release/Blender4.3/blender-4.3.2-linux-x64.tar.xz \
    -O /tmp/blender.tar.xz \
    && tar -xJf /tmp/blender.tar.xz -C /opt \
    && rm -f /tmp/blender.tar.xz \
    && ln -s /opt/blender-4.3.2-linux-x64/blender /usr/local/bin/blender


# ------------------------------------------------------------
# BLENDER VERIFICATION
# ------------------------------------------------------------

RUN blender --version


# ------------------------------------------------------------
# FORCE SOFTWARE OPENGL
# ------------------------------------------------------------

ENV LIBGL_ALWAYS_SOFTWARE=1
ENV MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
ENV GALLIUM_DRIVER=llvmpipe
ENV LIBGL_DRI3_DISABLE=1

# Do NOT force an EGL platform.
# We want Blender to use the X11/GLX context supplied by Xvfb.


# ------------------------------------------------------------
# BLENDER USER DIRECTORIES
# ------------------------------------------------------------

ENV BLENDER_USER_CONFIG=/tmp/blender-config
ENV BLENDER_USER_DATAFILES=/tmp/blender-data
ENV BLENDER_USER_SCRIPTS=/tmp/blender-scripts


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
    /tmp/blender-config \
    /tmp/blender-data \
    /tmp/blender-scripts


# ------------------------------------------------------------
# PORT
# ------------------------------------------------------------

EXPOSE 10000


# ============================================================
# START
# ============================================================
#
# xvfb-run creates a real X11 virtual display with GLX.
#
# Blender launched by engine.py inherits DISPLAY.
#
# ============================================================

CMD ["sh", "-c", "exec xvfb-run -a -e /tmp/xvfb-error.log -s '-screen 0 1024x768x24 +extension GLX +render -noreset' streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-10000} --server.headless=true --browser.gatherUsageStats=false"]
