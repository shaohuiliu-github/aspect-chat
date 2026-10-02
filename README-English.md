# ASPECT Chat 1.1.1

[极简安装说明 / Quick installation](INSTALL.md)

Describe, modify and run local ASPECT models in a bilingual chat interface. ASPECT 3.1.0, MPI and a versioned offline knowledge base are bundled in the image. Upload PDF, image or PRM inputs; review model files; run parameter sweeps; retain ordinary ASPECT result files in your own workspace.

Version 1.1.1 fixes a DeepSeek HTTP 400 caused by interleaving rendered PDF pages with replies to a batch of tool calls.

## Use

Install and start Docker Desktop, then pull the public image directly from GitHub Container Registry. No GitHub ZIP or registry account is needed. The exact commands are in the [installation guide](INSTALL.md). Enter your own provider API key in Settings. CPU, concurrency and timeout are configurable. The Release launcher remains available if you want the in-app Open Folder button to call the host file manager.

```sh
docker pull ghcr.io/shaohuiliu-github/aspect-chat:1.1.1
mkdir -p workspace
docker run -d --name aspect-chat --restart unless-stopped --user "$(id -u):$(id -g)" -p 127.0.0.1:8517:8517 -v "$(pwd)/workspace:/workspace" -e "ASPECT_CHAT_HOST_WORKSPACE=$(pwd)/workspace" ghcr.io/shaohuiliu-github/aspect-chat:1.1.1
```

Open http://127.0.0.1:8517. For host Open Folder buttons, use the launcher rather than the plain docker command. Output files remain in `workspace/runs/<id>/output` and are readable by ParaView. API keys and conversations are local to your workspace; do not redistribute a used workspace.

## Knowledge and source

The runtime knowledge uses ASPECT 3.1.0. Development snapshots and Wiki navigation are opt-in references and cannot be loaded as runtime models. See knowledge-manifest.json for pinned origins and coverage. This repository contains application source and packaging tools. The complete release build context, including the full official ASPECT source and offline knowledge, is attached as the source ZIP in Releases and is also inside the image under /opt/aspect-chat. Export it with docker cp. Rebuild from the release source directory using `docker build -f packaging/Dockerfile -t aspect-chat-local .` (requires substantial CPU/RAM and download access).

ASPECT is GPL-2.0-or-later; this application is AGPL-3.0-or-later. See LICENSE and packaging/LICENSE-NOTICES.md. This project has no upstream endorsement. Cloud conversation calls need your internet connection and API quota. Generated candidate models still require scientific review and actual validation; the application does not perform automatic inverse optimization. World Builder is enabled; FastScape is disabled.
