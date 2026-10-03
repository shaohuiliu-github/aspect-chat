# 安装与使用 / Install and use

[中文](#中文) · [English](#english)

## 中文

## 第一次使用：只做这四步

1. 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)，打开它，等待启动完成。
2. Mac 按 **⌘ + 空格**，搜索「终端」并打开。把下面整段命令复制进去，按回车。第一次下载需要一些时间，等到重新出现可输入命令的提示符。

```sh
mkdir -p "$HOME/chatgfd-workspace"
docker run -d --pull=always --name chatgfd --restart unless-stopped \
  --user "$(id -u):$(id -g)" -p 127.0.0.1:8517:8517 \
  --mount "type=bind,source=$HOME/chatgfd-workspace,target=/workspace" \
  -e "ASPECT_CHAT_HOST_WORKSPACE=$HOME/chatgfd-workspace" \
  ghcr.io/shaohuiliu-github/aspect-chat:2.0.5
```

3. 在浏览器打开 **[http://127.0.0.1:8517](http://127.0.0.1:8517)**。
4. 点击左下角 **Settings（设置）**，填写你的 API 密钥并保存。然后在对话框输入你想建立的模型，发送即可。

**不用下载本仓库，也不用单独安装 ASPECT、i2vis 或 Python。** 上面的命令也适用于 Linux；[Windows 安装步骤](INSTALL.md#windows)。

## 下次怎么打开

打开 Docker Desktop，在终端复制这一行：

```sh
docker start chatgfd
```

然后打开 **[http://127.0.0.1:8517](http://127.0.0.1:8517)**。第一次安装的长命令不用再执行。

模型和结果保存在用户主文件夹的 **`chatgfd-workspace`** 中。用完想停止，在终端输入 `docker stop chatgfd`。

<details>
<summary>Windows 安装步骤</summary>

<a id="windows"></a>

1. 安装并打开 Docker Desktop，使用 Linux 容器。
2. 在开始菜单搜索 **PowerShell**，打开后复制下面整段命令，按回车，等下载结束。

```powershell
$workspace = Join-Path $HOME 'chatgfd-workspace'
New-Item -ItemType Directory -Force -Path $workspace | Out-Null
docker run -d --pull=always --name chatgfd --restart unless-stopped -p 127.0.0.1:8517:8517 --mount "type=bind,source=$workspace,target=/workspace" -e "ASPECT_CHAT_HOST_WORKSPACE=$workspace" ghcr.io/shaohuiliu-github/aspect-chat:2.0.5
```

3. 打开 **[http://127.0.0.1:8517](http://127.0.0.1:8517)**。
4. 在 **Settings（设置）** 填写 API 密钥并保存，开始对话。

下次只需打开 Docker Desktop，在 PowerShell 输入 `docker start chatgfd`，再打开同一个网址。

</details>

<details>
<summary>已经下载了启动包？</summary>

使用启动包自带的「使用说明.md」，不用再复制上面的 Docker 安装命令。Mac 在终端输入 `bash `（末尾有空格），拖入解压文件夹中的 `start.sh`，按回车；Windows 双击 `Start.bat`。等待启动，打开终端显示的网址，在设置填写 API 密钥。

启动包的模型和结果保存在它自己的 `workspace` 文件夹。下次仍用同样的方法启动。

</details>

<details>
<summary>安装时报名称重复或端口占用？</summary>

- 提示容器名称 `chatgfd` 已存在：说明之前已安装。输入 `docker start chatgfd`，再打开网页。
- 提示端口 8517 已被占用：先关闭占用该端口的旧程序。已有 chatGFD 用户请用原来的启动方式和网址，避免重复安装。

</details>

<details>
<summary>如何升级？</summary>

仅适用于按上方命令安装的 `chatgfd`。在终端依次执行：

```sh
docker stop chatgfd
docker rm chatgfd
```

然后重新复制「第一次使用」中的安装命令。`chatgfd-workspace` 中的文件会保留。启动包用户请使用启动包的更新说明。

</details>

## English

## First time: four steps

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), open it, and wait until it is running.
2. On Mac, press **⌘ + Space**, search for **Terminal**, and open it. Copy the entire block below into Terminal and press Return. The first download takes time; wait until the command prompt returns.

```sh
mkdir -p "$HOME/chatgfd-workspace"
docker run -d --pull=always --name chatgfd --restart unless-stopped \
  --user "$(id -u):$(id -g)" -p 127.0.0.1:8517:8517 \
  --mount "type=bind,source=$HOME/chatgfd-workspace,target=/workspace" \
  -e "ASPECT_CHAT_HOST_WORKSPACE=$HOME/chatgfd-workspace" \
  ghcr.io/shaohuiliu-github/aspect-chat:2.0.5
```

3. Open **[http://127.0.0.1:8517](http://127.0.0.1:8517)** in your browser.
4. Click **Settings** at the lower left, enter your API key, and save. Type the model you want in the chat box and send.

**No repository download or separate ASPECT, i2vis or Python installation is needed.** The commands also work on Linux. [Windows instructions](INSTALL.md#windows-english).

## Open it next time

Open Docker Desktop, then copy this into Terminal:

```sh
docker start chatgfd
```

Open **[http://127.0.0.1:8517](http://127.0.0.1:8517)**. Do not repeat the first-time installation block.

Models and results are saved in **`chatgfd-workspace`** inside your home folder. To stop, enter `docker stop chatgfd` in Terminal.

<details>
<summary>Windows installation</summary>

<a id="windows-english"></a>

1. Install and open Docker Desktop with Linux containers enabled.
2. Search for **PowerShell** in the Start menu. Open it, paste the entire block below, press Enter, and wait for the download to finish.

```powershell
$workspace = Join-Path $HOME 'chatgfd-workspace'
New-Item -ItemType Directory -Force -Path $workspace | Out-Null
docker run -d --pull=always --name chatgfd --restart unless-stopped -p 127.0.0.1:8517:8517 --mount "type=bind,source=$workspace,target=/workspace" -e "ASPECT_CHAT_HOST_WORKSPACE=$workspace" ghcr.io/shaohuiliu-github/aspect-chat:2.0.5
```

3. Open **[http://127.0.0.1:8517](http://127.0.0.1:8517)**.
4. Enter your API key in **Settings**, save, and start chatting.

Next time, open Docker Desktop, enter `docker start chatgfd` in PowerShell, and open the same address.

</details>

<details>
<summary>Already downloaded the launcher ZIP?</summary>

Follow the README-English.md inside the launcher. Do not also run the Docker installation block above. On Mac, type `bash ` in Terminal (including the space), drag in the extracted folder's `start.sh`, and press Return. On Windows, double-click `Start.bat`. Wait for startup, open the address shown in Terminal, and enter your API key in Settings.

Files stay in the launcher's own `workspace` folder. Use the same launcher step next time.

</details>

<details>
<summary>Name already exists or port is occupied?</summary>

- Container name `chatgfd` already exists: it is already installed. Run `docker start chatgfd` and open the browser address.
- Port 8517 is occupied: close the old program using it. Existing chatGFD users should use their original launcher and address instead of installing again.

</details>

<details>
<summary>How to upgrade</summary>

For containers installed with the commands above only, run:

```sh
docker stop chatgfd
docker rm chatgfd
```

Repeat the first-time installation block. Files in `chatgfd-workspace` are retained. Launcher users should follow the launcher's update instructions.

</details>
