# Upstream release index includes Linux amd64 and arm64.
FROM geodynamics/aspect:v3.1.0@sha256:a3b599ac1d20d2a150f567a31d39591de18cf0c7e31fa9e9807d07dc291526c4
# The upstream v3.1.0 tag currently contains a 3.2.0-pre executable.
# Build the real release tag rather than trusting the container label.
USER dealii
ARG ASPECT_BUILD_JOBS=4
ARG TARGETARCH
RUN --mount=type=cache,id=aspect-stable-${TARGETARCH},target=/tmp/aspect-stable,uid=1000,gid=1000 \
    ulimit -s unlimited && cd /home/dealii/aspect && git checkout --detach v3.1.0 \
    && git submodule update --init --recursive \
    && git ls-files -z | xargs -0 touch -d "@$(git log -1 --format=%ct v3.1.0)" \
    && cmake -S . -B /tmp/aspect-stable -DCMAKE_BUILD_TYPE=Release -DASPECT_WITH_WORLD_BUILDER=ON -DASPECT_WITH_FASTSCAPE=OFF \
    && cmake --build /tmp/aspect-stable --target aspect --parallel ${ASPECT_BUILD_JOBS} \
    && cp /tmp/aspect-stable/aspect /home/dealii/aspect/bin/aspect-release \
    && strip /home/dealii/aspect/bin/aspect-release \
    && /home/dealii/aspect/bin/aspect-release --version | grep 'version 3.1.0'
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates tini fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/chat-venv
COPY packaging/requirements.lock /tmp/chat-requirements.txt
RUN /opt/chat-venv/bin/pip install --no-cache-dir -r /tmp/chat-requirements.txt \
    && /opt/chat-venv/bin/pip freeze > /opt/chat-venv/installed-packages.txt
WORKDIR /opt/aspect-chat
COPY app/ /opt/aspect-chat/
COPY knowledge/ /opt/aspect-chat/knowledge/
COPY packaging/container_entry.py /opt/aspect-chat/container_entry.py
COPY packaging/ /opt/aspect-chat/packaging/
COPY packaging/LICENSE-AGPL-3.0.txt /opt/aspect-chat/LICENSE
ENV PATH="/opt/chat-venv/bin:/home/dealii/aspect/bin:${PATH}" \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    ASPECT_CHAT_CONTAINER=1 ASPECT_CHAT_MANAGED_WORKER=1 ASPECT_CHAT_VERSION=3.1.0 \
    ASPECT_CHAT_DATA=/workspace ASPECT_CHAT_KNOWLEDGE=/opt/aspect-chat/knowledge \
    ASPECT_CHAT_KNOWLEDGE_READONLY=1 ASPECT_CHAT_BINARY=/home/dealii/aspect/bin/aspect-release \
    ASPECT_CHAT_SOURCE=/opt/aspect-chat/knowledge/sources/aspect-3.1.0 ASPECT_CHAT_MPI=/usr/bin/mpirun \
    MPLCONFIGDIR=/workspace/.cache/matplotlib XDG_CACHE_HOME=/workspace/.cache \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
RUN test -x "$ASPECT_CHAT_BINARY" && "$ASPECT_CHAT_BINARY" --version \
    && chmod a+x /home/dealii \
    && mkdir -p /workspace && chown dealii:dealii /workspace
USER dealii
EXPOSE 8517
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=6 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8517/api/health',timeout=3)"
ENTRYPOINT ["/usr/bin/tini","--","python","/opt/aspect-chat/container_entry.py"]
LABEL org.opencontainers.image.title="ASPECT Chat" \
      org.opencontainers.image.version="1.1.0" \
      org.opencontainers.image.source="https://github.com/shaohuiliu-github/aspect-chat" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later AND GPL-2.0-or-later"
