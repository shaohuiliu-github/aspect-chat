# Reuse the verified ASPECT 3.1.0 binary; retain its full corresponding source.
# RUNTIME_BASE must be the immutable multi-platform 1.1.1 release index.
ARG RUNTIME_BASE=ghcr.io/shaohuiliu-github/aspect-chat:1.1.1@sha256:39343226db0736504be6a08ef4b966a3853b9dcb56b639c67d8488f2e6505d62
FROM ${RUNTIME_BASE}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends gcc libhdf5-dev libsuitesparse-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/aspect-chat
COPY knowledge/ /opt/aspect-chat/knowledge/
COPY packaging/ /opt/aspect-chat/packaging/
COPY packaging/container_entry.py /opt/aspect-chat/container_entry.py
COPY packaging/LICENSE-AGPL-3.0.txt /opt/aspect-chat/LICENSE
COPY packaging/i2vis/ /opt/chatgfd-adapter/
RUN /opt/chat-venv/bin/pip install --no-cache-dir -r /opt/aspect-chat/packaging/requirements.lock \
    && /opt/chat-venv/bin/pip freeze > /opt/chat-venv/installed-packages.txt \
    && mkdir -p /opt/i2vis \
    && ln -s /opt/aspect-chat/knowledge/i2vis-source /opt/i2vis/source \
    && sh /opt/chatgfd-adapter/build.sh /opt/i2vis/source /opt/i2vis/bin \
    && gcc -O2 -I/opt/chatgfd-adapter -I/usr/include/suitesparse /opt/chatgfd-adapter/adapter_test.c -lumfpack -lamd -lsuitesparseconfig -lm -o /tmp/adapter-test \
    && /tmp/adapter-test \
    && /home/dealii/aspect/bin/aspect-release --version | grep 'version 3.1.0'
COPY app/ /opt/aspect-chat/
ENV CHATGFD_I2VIS_ROOT=/opt/i2vis ASPECT_CHAT_APP_VERSION=2.0.0
USER dealii
EXPOSE 8517
ENTRYPOINT ["/usr/bin/tini","--","python","/opt/aspect-chat/container_entry.py"]
LABEL org.opencontainers.image.title="chatGFD" \
      org.opencontainers.image.version="2.0.0" \
      org.opencontainers.image.source="https://github.com/shaohuiliu-github/aspect-chat" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later AND GPL-2.0-or-later AND GPL-3.0 AND MIT"
