# ASPECT Chat 1.1.0

Describe, modify and run local ASPECT models in a bilingual chat interface. ASPECT 3.1.0, MPI and a versioned offline knowledge base are bundled in the image. Upload PDF, image or PRM inputs; review model files; run parameter sweeps; retain ordinary ASPECT result files in your own workspace.

## Use

Install and start Docker Desktop (Linux containers on Windows), then download the small online launcher from Releases. Mac: Start.command; Windows: Start.bat; Linux: bash start.sh. Enter your own provider API key in Settings. CPU, concurrency and timeout are configurable. A public image is downloadable without a registry account.

```sh
docker pull ghcr.io/shaohuiliu-github/aspect-chat:1.1.0
mkdir -p workspace
docker run -d --name aspect-chat --user "$(id -u):$(id -g)" -p 127.0.0.1:8517:8517 --mount type=bind,source="$(pwd)/workspace",target=/workspace ghcr.io/shaohuiliu-github/aspect-chat:1.1.0
```

Open http://127.0.0.1:8517. For host Open Folder buttons, use the launcher rather than the plain docker command. Output files remain in workspace/runs/<id>/output and are readable by ParaView. API keys and conversations are local to your workspace; do not redistribute a used workspace.

## Knowledge and source

The runtime knowledge uses ASPECT 3.1.0. Development snapshots and Wiki navigation are opt-in references and cannot be loaded as runtime models. See knowledge-manifest.json for pinned origins and coverage. This repository contains application source and packaging tools. The complete release build context, including the full official ASPECT source and offline knowledge, is attached as the source ZIP in Releases and is also inside the image under /opt/aspect-chat. Export it with docker cp. Rebuild from the release source directory using `docker build -f packaging/Dockerfile -t aspect-chat-local .` (requires substantial CPU/RAM and download access).

ASPECT is GPL-2.0-or-later; this application is AGPL-3.0-or-later. See LICENSE and packaging/LICENSE-NOTICES.md. This project has no upstream endorsement. Cloud conversation calls need your internet connection and API quota. Generated candidate models still require scientific review and actual validation; the application does not perform automatic inverse optimization. World Builder is enabled; FastScape is disabled.
