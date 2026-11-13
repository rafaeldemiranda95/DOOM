# Linux DOOM 1.10 — build 32-bit + runtime Xvfb 8-bit + noVNC (browser)
FROM debian:bookworm-slim AS build

RUN dpkg --add-architecture i386 \
 && apt-get update && apt-get install -y --no-install-recommends \
    gcc-multilib \
    make \
    libc6-dev \
    libc6-dev:i386 \
    libx11-dev:i386 \
    libxext-dev:i386 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY sndserv/ /src/sndserv/
COPY linuxdoom-1.10/ /src/linuxdoom-1.10/

# Patches para GCC/glibc modernos + build i386 (código assume ponteiros 32-bit)
RUN sed -i 's/#include <errnos\.h>/#include <errno.h>/' /src/linuxdoom-1.10/i_video.c \
 && sed -i 's/#ifdef LINUX/#if 0 \/* LINUX values.h removed in modern glibc *\//' /src/linuxdoom-1.10/doomtype.h \
 && sed -i 's|#include <values.h>|#include "doomtype.h"|' /src/linuxdoom-1.10/m_bbox.h \
 && sed -i 's|^CFLAGS=.*|CFLAGS=-m32 -g -Wall -DNORMALUNIX -DLINUX|' /src/linuxdoom-1.10/Makefile \
 && sed -i 's|^LDFLAGS=.*|LDFLAGS=-m32|' /src/linuxdoom-1.10/Makefile \
 && sed -i 's|^LIBS=.*|LIBS=-lXext -lX11 -lm|' /src/linuxdoom-1.10/Makefile \
 && sed -i 's|^CFLAGS=.*|CFLAGS=-m32 -O -DNORMALUNIX -DLINUX|' /src/sndserv/Makefile \
 && sed -i 's|^LDFLAGS=.*|LDFLAGS=-m32|' /src/sndserv/Makefile \
 && sed -i 's/extern int\terrno;/#include <errno.h>/' /src/sndserv/linux.c \
 && sed -i 's/extern int\terrno;/#include <errno.h>/' /src/linuxdoom-1.10/i_sound.c \
 && sed -i 's/extern int errno;/#include <errno.h>/' /src/linuxdoom-1.10/i_video.c \
 && sed -i 's|#include <unistd.h>|#include <unistd.h>\n#include <sys/ioctl.h>|' /src/sndserv/linux.c \
 && mkdir -p /src/sndserv/linux /src/linuxdoom-1.10/linux \
 && make -C /src/sndserv \
 && make -C /src/linuxdoom-1.10

FROM debian:bookworm-slim

RUN dpkg --add-architecture i386 \
 && apt-get update && apt-get install -y --no-install-recommends \
    libx11-6:i386 \
    libxext6:i386 \
    libc6:i386 \
    xvfb \
    xauth \
    x11-utils \
    x11vnc \
    novnc \
    websockify \
    python3 \
    && rm -rf /var/lib/apt/lists/* \
 && ln -sfn /usr/share/novnc/vnc.html /usr/share/novnc/index.html

WORKDIR /doom
COPY --from=build /src/linuxdoom-1.10/linux/linuxxdoom /doom/linuxxdoom
COPY --from=build /src/sndserv/linux/sndserver /doom/sndserver
COPY docker-entrypoint.sh /doom/docker-entrypoint.sh
COPY maps/e1m1_expandido.wad /doom/pwad/e1m1_expandido.wad

RUN sed -i 's/\r$//' /doom/docker-entrypoint.sh \
 && chmod +x /doom/linuxxdoom /doom/sndserver /doom/docker-entrypoint.sh

ENV HOME=/root \
    DOOMWADDIR=/doom \
    DISPLAY=:99 \
    XVFB_GEOM=640x400x24

VOLUME ["/wad"]
EXPOSE 8080

ENTRYPOINT ["/doom/docker-entrypoint.sh"]
