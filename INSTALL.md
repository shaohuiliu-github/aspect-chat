# 安装与开始使用 / Install and start

## 中文

先安装并启动 [Docker Desktop](https://docs.docker.com/get-started/get-docker/)（Linux 可以用 Docker Engine）。公开镜像已在 GitHub Container Registry，无需 GitHub 账号，也无需下载 GitHub 压缩包。在 Mac 或 Linux 的终端复制：

```sh
mkdir -p aspect-chat-workspace
docker pull ghcr.io/shaohuiliu-github/aspect-chat:1.1.0
docker run -d --name aspect-chat --restart unless-stopped --user "$(id -u):$(id -g)" -p 127.0.0.1:8517:8517 -v "$(pwd)/aspect-chat-workspace:/workspace" -e "ASPECT_CHAT_HOST_WORKSPACE=$(pwd)/aspect-chat-workspace" ghcr.io/shaohuiliu-github/aspect-chat:1.1.0
```

Windows 在 Docker Desktop 中选 Linux 容器，PowerShell 运行：

```powershell
$workspace = Join-Path (Get-Location) 'aspect-chat-workspace'
New-Item -ItemType Directory -Force -Path $workspace | Out-Null
docker pull ghcr.io/shaohuiliu-github/aspect-chat:1.1.0
docker run -d --name aspect-chat --restart unless-stopped -p 127.0.0.1:8517:8517 --mount "type=bind,source=$workspace,target=/workspace" -e "ASPECT_CHAT_HOST_WORKSPACE=$workspace" ghcr.io/shaohuiliu-github/aspect-chat:1.1.0
```

打开 http://127.0.0.1:8517，在“设置”中填写自己的 API 密钥。结果实时保存在当前目录的 `aspect-chat-workspace/runs/`。下次使用只需打开同一网址；停止时运行 `docker stop aspect-chat`，重启时运行 `docker start aspect-chat`。如要让应用内的“打开文件夹”按钮调用主机文件管理器，可改用 [Release 启动包](https://github.com/shaohuiliu-github/aspect-chat/releases/tag/v1.1.0)；直接运行镜像时文件仍可从工作目录打开。

## English

Install and start [Docker Desktop](https://docs.docker.com/get-started/get-docker/) first (Docker Engine also works on Linux). The public image is on GitHub Container Registry; no GitHub account or ZIP download is needed. Copy the shell commands above into a Mac or Linux terminal, or the PowerShell commands on Windows with Linux containers enabled. Then open http://127.0.0.1:8517 and enter your own API key in Settings. Results are saved continuously under `aspect-chat-workspace/runs/` in the current directory. To stop or restart, use `docker stop aspect-chat` or `docker start aspect-chat`. The optional [Release launcher](https://github.com/shaohuiliu-github/aspect-chat/releases/tag/v1.1.0) enables the in-app Open Folder button to call the host file manager; with plain Docker, open the workspace folder directly.
