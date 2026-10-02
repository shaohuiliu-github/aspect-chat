#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
mode="${1:-start}"
root="$PWD"
workspace="$root/workspace"
mkdir -p "$workspace/inputs" "$workspace/.host-open"
name="aspect-chat-$(printf '%s' "$root" | cksum | awk '{print $1}')"
if ! command -v docker >/dev/null; then
  printf '请安装并启动 Docker Desktop，然后再打开此文件。\nInstall and start Docker Desktop, then open this file again.\nhttps://docs.docker.com/get-started/get-docker/\n'
  exit 1
fi
# Reuse a running Colima profile without changing the user's default Docker context.
if ! docker info >/dev/null 2>&1; then
  if command -v colima >/dev/null; then
    export DOCKER_HOST="unix://$HOME/.colima/aspect-package/docker.sock"
    if ! docker info >/dev/null 2>&1 && [ "$mode" != stop ]; then
      printf '正在启动本机 Colima 环境…\nStarting the local Colima environment…\n'
      if [ -f "$HOME/.colima/aspect-package/colima.yaml" ]; then
        colima start aspect-package --activate=false --ssh-config=false --mount "$root:w"
      else
        colima start aspect-package --activate=false --ssh-config=false --cpu 4 --memory 8 --disk 40 --mount "$root:w"
      fi
    fi
  fi
fi
if ! docker info >/dev/null 2>&1; then
  printf 'Docker 尚未启动，请启动 Docker Desktop 或 Colima。\nStart Docker Desktop or Colima first.\n'
  exit 1
fi
if [ "$mode" = stop ]; then
  if docker container inspect "$name" >/dev/null 2>&1; then docker stop -t 30 "$name"; fi
  printf '已停止，模型和结果仍在 workspace。\nStopped; files remain in workspace.\n'; exit 0
fi
arch="$(docker info --format '{{.Architecture}}')"
case "$arch" in aarch64|arm64) arch=arm64;; x86_64|amd64) arch=amd64;; *) printf 'Unsupported architecture: %s\n' "$arch"; exit 1;; esac
image="aspect-chat:1.1.1-aspect3.1.0-$arch"
if ! docker image inspect "$image" >/dev/null 2>&1; then
  archive="images/aspect-chat-$arch.tar.gz"
  if [ -f "$archive" ]; then
    printf '首次启动正在导入运行环境…\nImporting the environment for first launch…\n'
    gzip -dc "$archive" | docker load
  elif [ -f image-reference.txt ]; then
    remote="$(tr -d '\r\n' < image-reference.txt)"
    if [[ ! "$remote" =~ ^[a-z0-9][a-z0-9./_:@-]+$ ]]; then printf 'Invalid registry image reference.\n'; exit 1; fi
    printf '首次启动正在从容器仓库下载运行环境…\nDownloading the environment from the registry for first launch…\n'
    docker pull "$remote"
    docker tag "$remote" "$image"
  elif [ -f source/packaging/Dockerfile ]; then
    printf '正在联网构建运行环境，需要下载约 2 GB。\nBuilding the environment online (about 2 GB download).\n'
    docker build -f source/packaging/Dockerfile -t "$image" source
  else printf 'Missing image for %s. Use the matching release package.\n' "$arch"; exit 1; fi
fi
if docker container inspect "$name" >/dev/null 2>&1; then
  running="$(docker inspect --format '{{.State.Running}}' "$name")"
  if [ "$running" != true ]; then docker start "$name" >/dev/null; fi
  port="$(docker inspect --format '{{index .Config.Labels "aspect-chat.port"}}' "$name")"
else
  port="${ASPECT_CHAT_PORT:-8517}"
  launched=false
  # Docker binds atomically; an occupied port causes a retry without killing any process.
  for attempt in $(seq 1 30); do
    if (: >/dev/tcp/127.0.0.1/"$port") 2>/dev/null; then port=$((port+1)); continue; fi
    if docker run -d --name "$name" --restart unless-stopped --stop-timeout 30 \
      --label "aspect-chat.port=$port" --label aspect-chat.package=1.1.1 \
      --user "$(id -u):$(id -g)" -p "127.0.0.1:$port:8517" \
      --mount "type=bind,source=$workspace,target=/workspace" \
      -e "ASPECT_CHAT_HOST_WORKSPACE=$workspace" -e "ASPECT_CHAT_PUBLIC_PORT=$port" \
      -e "ASPECT_CHAT_INSTANCE=$name" \
      "$image" > "$workspace/container-start.log" 2>&1; then launched=true; break; fi
    if docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null | grep -q '^created$'; then docker rm "$name" >/dev/null; fi
    if grep -Eqi 'address already in use|port is already allocated' "$workspace/container-start.log"; then port=$((port+1)); else cat "$workspace/container-start.log"; exit 1; fi
  done
  if [ "$launched" != true ]; then printf 'No free port found.\n'; exit 1; fi
fi
url="http://127.0.0.1:$port"
printf '正在启动… / Starting…\n'
ready=false
for attempt in $(seq 1 90); do
  if curl --noproxy '*' -fsS "$url/api/health" 2>/dev/null | grep -Fq "\"instance\": \"$name\""; then ready=true; break; fi
  sleep 1
done
if [ "$ready" != true ]; then docker logs --tail 80 "$name"; exit 1; fi
printf '\nASPECT Chat: %s\n模型与结果 / Models and results: %s\n关闭此窗口后计算会继续；停止计算请运行 Stop。\nClosing this window leaves computations running; use Stop to stop them.\n\n' "$url" "$workspace"
if [ "${ASPECT_CHAT_NO_BROWSER:-0}" != 1 ]; then
  if [ "$(uname -s)" = Darwin ]; then open "$url"; else xdg-open "$url" >/dev/null 2>&1 || true; fi
fi
# Requests contain only a known object type and 12 hex digits, never commands or paths.
while [ "$(docker inspect --format '{{.State.Running}}' "$name" 2>/dev/null || true)" = true ]; do
  for request in "$workspace/.host-open/"*.request; do
    [ -f "$request" ] || continue
    value="$(cat "$request")"
    if [[ "$value" =~ ^(case|job):([a-f0-9]{12})$ ]]; then
      if [ "${BASH_REMATCH[1]}" = case ]; then target="$workspace/cases/${BASH_REMATCH[2]}"; else target="$workspace/runs/${BASH_REMATCH[2]}/output"; fi
      # Refuse redirected folders, including symlinked parents.
      actual="$(cd "$target" 2>/dev/null && pwd -P || true)"
      base="$(cd "$workspace" && pwd -P)"
      if [[ "$actual" == "$base/"* ]]; then
        if [ "$(uname -s)" = Darwin ]; then open "$actual"; else xdg-open "$actual" >/dev/null 2>&1 || true; fi
      fi
    fi
    rm -f "$request"
  done
  sleep 1
done
