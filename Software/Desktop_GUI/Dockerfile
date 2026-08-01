FROM ros:jazzy-perception

#Get pip in place, plus system libs PyQt6's xcb platform plugin needs at
#runtime. pip itself is present in this base image but Ubuntu Noble treats
#system Python as "externally managed" (PEP 668) -- installs still need
#--break-system-packages (see docker-compose.yml command), this apt step
#alone doesn't get around that.
RUN apt-get update && apt-get install -y \
    python3-pip \
    libgl1 \
    libegl1 \
    libxkbcommon-x11-0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libdbus-1-3 \
    libfontconfig1 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*