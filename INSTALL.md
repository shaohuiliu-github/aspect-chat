# 安装与开始使用 / Install and start

## 中文

最简单的方法：安装并启动 [Docker Desktop](https://docs.docker.com/get-started/get-docker/)，下载[启动包](https://github.com/shaohuiliu-github/chatGFD/releases/download/v2.0.4/chatGFD-2.0.4-online.zip) 并解压。Mac 打开「终端」，输入 `bash `（末尾留一个空格），把解压目录里的 `start.sh` 拖入终端，按回车。Windows 双击 `Start.bat`。首次启动会自动下载环境并打开网页。在左下角 Settings（设置）中填入自己的 API 密钥即可使用。模型和结果保存在解压目录的 `chatGFD-2.0.4-online/workspace`。

Mac 新版启动包不再包含未经签名的 `.command` 文件，所以不要打开旧版 `Start.command`。以后仍按上面的方法运行 `start.sh`。停止时在终端输入 `bash `，拖入同一个 `start.sh`，再输入 ` stop` 并回车。关闭终端窗口不会停止 Docker 中的计算。升级时先按旧包的停止方法停止旧容器，再下载新版，将旧 `workspace` 复制到新解压目录后启动。

如需直接用 Docker 命令，Mac / Linux 终端复制这段：

```sh
mkdir -p "$HOME/chatgfd-workspace" && docker run -d --pull=always --name chatgfd --restart unless-stopped --user "$(id -u):$(id -g)" -p 127.0.0.1:8517:8517 -v "$HOME/chatgfd-workspace:/workspace" -e "ASPECT_CHAT_HOST_WORKSPACE=$HOME/chatgfd-workspace" ghcr.io/shaohuiliu-github/aspect-chat:2.0.4
```

Windows 启动 Docker Desktop，使用 Linux 容器，在 PowerShell 复制：

```powershell
$workspace = Join-Path $HOME 'chatgfd-workspace'; New-Item -ItemType Directory -Force -Path $workspace | Out-Null
docker run -d --pull=always --name chatgfd --restart unless-stopped -p 127.0.0.1:8517:8517 --mount "type=bind,source=$workspace,target=/workspace" -e "ASPECT_CHAT_HOST_WORKSPACE=$workspace" ghcr.io/shaohuiliu-github/aspect-chat:2.0.4
```

打开 http://127.0.0.1:8517，在“设置”填写自己的 API 密钥，即可开始对话。模型与结果实时保存到主文件夹的 `chatgfd-workspace`；新任务目录按分钟命名。以后停止用 `docker stop chatgfd`，重新启动用 `docker start chatgfd`。

`docker pull` 只下载镜像；上面的 `docker run` 同时下载并启动，因此不需要另做 pull。镜像沿用已公开的 `aspect-chat` 地址，仓库改名不影响旧安装命令。纯 Docker 模式中，文件夹按钮提供本机路径和文件下载；调用 Finder / Explorer 需要可选的 [启动包](https://github.com/shaohuiliu-github/chatGFD/releases/tag/v2.0.4)，或本机辅助进程。不要向镜像开放主机命令执行权限。

升级旧的 `chatgfd` 容器时，先执行 `docker stop chatgfd` 和 `docker rm chatgfd`，再复制上面的启动命令；主机工作目录中的模型与结果保留。使用其他容器名或工作目录时沿用自己的原配置。

## English

The easiest route is to install and start [Docker Desktop](https://docs.docker.com/get-started/get-docker/), download the [launcher](https://github.com/shaohuiliu-github/chatGFD/releases/download/v2.0.4/chatGFD-2.0.4-online.zip), and extract it. On Mac, open Terminal, type `bash ` (including the space), drag `start.sh` from the extracted folder into Terminal, and press Return. On Windows, double-click `Start.bat`. The first launch downloads the environment and opens the webpage. Enter your own API key in Settings at the lower left. Models and results stay in `chatGFD-2.0.4-online/workspace` inside the extracted folder.

The new Mac package omits the unsigned `.command` shortcut. Run `start.sh` using Terminal as above each time. To stop it, type `bash `, drag in the same `start.sh`, then type ` stop` and press Return. Closing Terminal does not stop the Docker container. To upgrade, stop the old container using the old launcher first, then copy its `workspace` into the new extracted folder before starting the new launcher.

For direct Docker use, copy the Mac/Linux command above, or the PowerShell commands on Windows with Linux containers enabled.

Open http://127.0.0.1:8517 and enter your API key in Settings. Models and outputs are saved continuously in `chatgfd-workspace` under your home directory, with minute-based task folder names. Use `docker stop chatgfd` and `docker start chatgfd` later.

`docker pull` downloads only; `docker run` starts a container and can pull automatically. The image keeps its published `aspect-chat` address, so previous install commands still work after the repository rename. Plain Docker offers a host path and file download from the folder buttons. Calling Finder / Explorer requires the optional [launcher](https://github.com/shaohuiliu-github/chatGFD/releases/tag/v2.0.4) or a host helper. To upgrade, stop and remove the old container, then repeat the run command with the original workspace mount; host files are retained.
