# Start from the last runtime image that predates personal paper notes.
ARG RUNTIME_BASE=ghcr.io/shaohuiliu-github/aspect-chat:2.0.0@sha256:2a7cdae89c01b57593f5b6ef512b93b0ac965367a71d22f5448a9a63cec864cd
FROM ${RUNTIME_BASE}
USER root
RUN /opt/chat-venv/bin/pip install --no-cache-dir --no-deps tzdata==2026.4 \
    && /opt/chat-venv/bin/pip freeze > /opt/chat-venv/installed-packages.txt
COPY app/ /opt/aspect-chat/
COPY packaging/ /opt/aspect-chat/packaging/
COPY packaging/container_entry.py /opt/aspect-chat/container_entry.py
COPY knowledge/knowledge.sqlite knowledge/manifest.json /opt/aspect-chat/knowledge/
COPY knowledge/i2vis-source/templates/mantle_plume/init.t3c /opt/i2vis/source/templates/mantle_plume/init.t3c
COPY knowledge/i2vis-source/templates/mantle_plume/init.t3c /opt/aspect-chat/knowledge/i2vis-source/templates/mantle_plume/init.t3c

ENV ASPECT_CHAT_APP_VERSION=2.0.5
USER dealii
EXPOSE 8517
ENTRYPOINT ["/usr/bin/tini","--","python","/opt/aspect-chat/container_entry.py"]
ARG SOURCE_REVISION=local
LABEL org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.title="chatGFD" \
      org.opencontainers.image.version="2.0.5" \
      org.opencontainers.image.source="https://github.com/shaohuiliu-github/chatGFD"
