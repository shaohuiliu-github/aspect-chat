# 安装与开始使用 / Install and start

## 中文

先安装并启动 [Docker Desktop](https://docs.docker.com/get-started/get-docker/)。无需下载 GitHub 源码，Mac / Linux 在终端复制：

```sh
mkdir -p "$HOME/chatgfd-workspace" && docker run -d --pull=always --name chatgfd --restart unless-stopped --user "$(id -u):$(id -g)" -p 127.0.0.1:8517:8517 -v "$HOME/chatgfd-workspace:/workspace" -e "ASPECT_CHAT_HOST_WORKSPACE=$HOME/chatgfd-workspace" ghcr.io/shaohuiliu-github/aspect-chat:2.0.5
```

Windows 启动 Docker Desktop，使用 Linux 容器，在 PowerShell 复制：

```powershell
$workspace = Join-Path $HOME 'chatgfd-workspace'; New-Item -ItemType Directory -Force -Path $workspace | Out-Null
docker run -d --pull=always --name chatgfd --restart unless-stopped -p 127.0.0.1:8517:8517 --mount "type=bind,source=$workspace,target=/workspace" -e "ASPECT_CHAT_HOST_WORKSPACE=$workspace" ghcr.io/shaohuiliu-github/aspect-chat:2.0.5
```

打开 http://127.0.0.1:8517，在“设置”填写自己的 API 密钥，即可开始对话。模型与结果实时保存到主文件夹的 `chatgfd-workspace`；新任务目录按分钟命名。以后停止用 `docker stop chatgfd`，重新启动用 `docker start chatgfd`。

`docker pull` 只下载镜像；上面的 `docker run` 同时下载并启动，因此不需要另做 pull。镜像沿用已公开的 `aspect-chat` 地址，仓库改名不影响旧安装命令。纯 Docker 模式中，文件夹按钮提供本机路径和文件下载；调用 Finder / Explorer 需要可选的 [启动包](https://github.com/shaohuiliu-github/chatGFD/releases/tag/v2.0.5)，或本机辅助进程。不要向镜像开放主机命令执行权限。

如果 8517 端口被占用，把命令中的 `127.0.0.1:8517:8517` 改为 `127.0.0.1:8518:8517`，并添加 `-e ASPECT_CHAT_PUBLIC_PORT=8518`，然后打开 http://127.0.0.1:8518。

升级旧的 `chatgfd` 容器时，先执行 `docker stop chatgfd` 和 `docker rm chatgfd`，再复制上面的启动命令；主机工作目录中的模型与结果保留。使用其他容器名或工作目录时沿用自己的原配置。

需要文件夹按钮直接打开 Finder / Explorer 时，可用[可选启动包](https://github.com/shaohuiliu-github/chatGFD/releases/download/v2.0.5/chatGFD-2.0.5-online.zip)。解压后，Mac 在终端输入 `bash `，拖入 `start.sh` 并回车；停止时在末尾加 ` stop`。Windows 使用 `Start.bat` / `Stop.bat`。启动包结果保存在其 `workspace` 文件夹，关闭终端不会停止容器。

## English

Install and start [Docker Desktop](https://docs.docker.com/get-started/get-docker/), then copy the Mac/Linux Docker command above, or the Windows PowerShell commands with Linux containers enabled. No GitHub source download is required.

Open http://127.0.0.1:8517 and enter your API key in Settings. Models and outputs are saved continuously in `chatgfd-workspace` under your home directory, with minute-based task folder names. Use `docker stop chatgfd` and `docker start chatgfd` later.

`docker pull` downloads only; `docker run` starts a container and can pull automatically. The image keeps its published `aspect-chat` address, so previous install commands still work after the repository rename. Plain Docker offers a host path and file download from the folder buttons. Calling Finder / Explorer requires the optional [launcher](https://github.com/shaohuiliu-github/chatGFD/releases/tag/v2.0.5) or a host helper. To upgrade, stop and remove the old container, then repeat the run command with the original workspace mount; host files are retained.

For direct Finder / Explorer actions, download the [optional launcher](https://github.com/shaohuiliu-github/chatGFD/releases/download/v2.0.5/chatGFD-2.0.5-online.zip). Extract it. On Mac, type `bash ` in Terminal, drag in `start.sh`, and press Return; add ` stop` to stop it. Windows uses Start.bat / Stop.bat. Files stay in the launcher folder’s `workspace`; closing Terminal does not stop Docker.

If port 8517 is occupied, replace `127.0.0.1:8517:8517` with `127.0.0.1:8518:8517`, add `-e ASPECT_CHAT_PUBLIC_PORT=8518`, and open http://127.0.0.1:8518.
