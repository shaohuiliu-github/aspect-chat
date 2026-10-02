# 安装与开始使用 / Install and start

## 中文

先安装并启动 [Docker Desktop](https://docs.docker.com/get-started/get-docker/)（Linux 可以用 Docker Engine）。公开镜像已在 GitHub Container Registry，无需 GitHub 账号，也无需下载 GitHub 压缩包。在 Mac 或 Linux 的终端复制：

```sh
mkdir -p chatgfd-workspace
docker pull ghcr.io/shaohuiliu-github/aspect-chat:2.0.0
docker run -d --name chatgfd --restart unless-stopped --user "$(id -u):$(id -g)" -p 127.0.0.1:8517:8517 -v "$(pwd)/chatgfd-workspace:/workspace" -e "ASPECT_CHAT_HOST_WORKSPACE=$(pwd)/chatgfd-workspace" ghcr.io/shaohuiliu-github/aspect-chat:2.0.0
```

Windows 在 Docker Desktop 中选 Linux 容器，PowerShell 运行：

```powershell
$workspace = Join-Path (Get-Location) 'chatgfd-workspace'
New-Item -ItemType Directory -Force -Path $workspace | Out-Null
docker pull ghcr.io/shaohuiliu-github/aspect-chat:2.0.0
docker run -d --name chatgfd --restart unless-stopped -p 127.0.0.1:8517:8517 --mount "type=bind,source=$workspace,target=/workspace" -e "ASPECT_CHAT_HOST_WORKSPACE=$workspace" ghcr.io/shaohuiliu-github/aspect-chat:2.0.0
```

打开 http://127.0.0.1:8517，在“设置”中填写自己的 API 密钥；左上选择 ASPECT 或 i2vis，对话框下方选择大模型。结果实时保存在当前目录的 `chatgfd-workspace/runs/`。下次使用只需打开同一网址；停止时运行 `docker stop chatgfd`，重启时运行 `docker start chatgfd`。从旧版升级时，在原工作目录执行 `docker stop chatgfd && docker rm chatgfd`，然后重新执行上面的 `docker pull` 和 `docker run`；工作目录中的数据不会删除。如要让应用内的“打开文件夹”按钮调用主机文件管理器，可改用 [Release 启动包](https://github.com/shaohuiliu-github/aspect-chat/releases/tag/v2.0.0)；直接运行镜像时文件仍可从工作目录打开。

## English

Install and start [Docker Desktop](https://docs.docker.com/get-started/get-docker/) first (Docker Engine also works on Linux). The public image is on GitHub Container Registry; no GitHub account or ZIP download is needed. Copy the shell commands above into a Mac or Linux terminal, or the PowerShell commands on Windows with Linux containers enabled. Then open http://127.0.0.1:8517 and enter your own API key in Settings. Select ASPECT or i2vis at the upper left, and choose your chat model below the composer. Results are saved continuously under `chatgfd-workspace/runs/` in the current directory. To stop or restart, use `docker stop chatgfd` or `docker start chatgfd`. To upgrade an older container, run `docker stop chatgfd && docker rm chatgfd` from the original working directory, then repeat the `docker pull` and `docker run` commands above; the workspace remains intact. The optional [Release launcher](https://github.com/shaohuiliu-github/aspect-chat/releases/tag/v2.0.0) enables the in-app Open Folder button to call the host file manager; with plain Docker, open the workspace folder directly.
