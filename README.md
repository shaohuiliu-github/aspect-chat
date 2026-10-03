# chatGFD

**用对话建立动力学模型，检验地球科学假说，学习数值模拟。**

Geophysical Fluid Dynamics Simulation · 地球流体动力学模拟

[English](README-English.md) · [安装说明](INSTALL.md) · [发布包与检查报告](https://github.com/shaohuiliu-github/chatGFD/releases/tag/v2.0.5)

chatGFD 把自然语言描述变成可编辑、可运行的 ASPECT / i2vis 模型。科研用户可以把地质、地球化学、地震或古地磁问题转成对照实验，检查假说的物理可行性；动力学数值模拟入门者也可以从一个简单案例开始，通过对话更快建立模型，逐步理解材料、边界条件和参数变化的影响。

求解器、Python 环境和离线知识库已封装在 Docker 镜像中，无需下载 GitHub 源码或单独安装求解器。

## 直接在终端启动

先安装并启动 [Docker Desktop](https://docs.docker.com/get-started/get-docker/)。Mac / Linux 在终端复制：

```sh
mkdir -p "$HOME/chatgfd-workspace"
docker run -d --pull=always --name chatgfd --restart unless-stopped \
  --user "$(id -u):$(id -g)" -p 127.0.0.1:8517:8517 \
  --mount "type=bind,source=$HOME/chatgfd-workspace,target=/workspace" \
  -e "ASPECT_CHAT_HOST_WORKSPACE=$HOME/chatgfd-workspace" \
  ghcr.io/shaohuiliu-github/aspect-chat:2.0.5
```

打开 [http://127.0.0.1:8517](http://127.0.0.1:8517)，在左下角 **Settings（设置）** 填写自己的 API 密钥，即可开始使用。首次运行自动下载环境；模型和结果保存在主文件夹中的 `chatgfd-workspace`，可用 ParaView 等软件打开。

以后启动用 `docker start chatgfd`，停止用 `docker stop chatgfd`。已有安装请用启动命令；升级、端口冲突和 Windows PowerShell 方法见 [安装说明](INSTALL.md)。

如果希望文件夹按钮直接打开 Finder / Explorer，可使用小型 [启动包](https://github.com/shaohuiliu-github/chatGFD/releases/download/v2.0.5/chatGFD-2.0.5-online.zip)。Mac 解压后在终端输入 `bash `，拖入 `start.sh` 并回车；Windows 双击 `Start.bat`。

## 科研与入门教学

- **科研验证：** 上传论文或图像，核对物理参数、单位、来源与缺失项，再建立模型、做参数对比。模拟结果帮助判断假说的物理可行性。
- **建模入门：** 点击「第一个模型」或「经典模型示例」，用简短描述开始。助手在对话中解释关键设置；可以继续说「把黏度降低一半」或「先不运行，只修改参数」，逐步学习。

[六个简短案例提示词](DEMO_CASES.md)可直接复制，首页也可点击填入。论文和层析图案例需要上传附件；教学默认参数会在对话中说明，后续可随时修改。

## 2.0.5 的工作流程

- 在对话框上传 PDF、图片、PRM 或 i2vis 输入文件，发送后的附件保留在消息里。中英文界面，新工作区默认英文；可删除对话并保留模型和结果。
- 论文提取先记录物理参数、原单位、PDF 页码、短引文、换算、实际输入值和缺失项。记录随输入版本变化，并随运行快照保存。参数语法通过不代表论文已复现；网格和迭代收敛检查是后续工作。
- 初始密度、温度与参考黏度由独立代码评估输入函数并绘图，不启动模拟。三维函数盒子显示明确标注的中央 x-z 剖面，材料混合排除累计应变等非化学场。不支持的几何、材料与初始场会明确说明。参考黏度不等于非线性求解后的有效黏度。温度为蓝红、黏度为紫黄对数色标、密度为蓝绿黄。
- 图片转换使用明确的色标、坐标、单位和物理关系。ASPECT 简单材料可接入密度组成代理；当前 i2vis 分支可按指定材料与参考压力，把热密度异常转换为初始温度。它会改变温度相关流变，不能仅凭地震波速唯一反演密度。
- 参数检查在后台完成；缺失项和错误在对话中说明。任务完成有提醒，状态保留在对话中。编辑后可以直接再次运行，新任务与结果文件夹按分钟命名；手动操作无需大模型 API。扫描时每个任务使用独立输入快照，限制同时核数与时间。

## 知识库与求解器

ASPECT 为已验证的 3.1.0 发布版，包含全部 1,796 个稳定版 PRM 文件、手册、API、参数条目、World Builder 和工具源代码。开发版与 Wiki 导航明确为参考来源。

已安装 i2vis 是用户提供并确认公开许可的 Gerya / Yang / Faccenda HDF5 分支，固定到 a203df002bf8e41c3a29ad0c4857cef3d1daf0a1；包含对应源码、相图表、源代码参数指南和三个短程教学模板。便携后端以 SuiteSparse UMFPACK 替代 Intel MKL，日志保留线性残差检查；这不等于已证明两个后端的科研结果相同。输入格式不支持任意 I2VIS 分支直接运行。

新增参考：[I2ELVIS planet](https://github.com/FormingWorlds/i2elvis_planet)、[Gou/Liu 论文模型设置](https://github.com/YirenGou/Gou-and-Liu-2026-Dripping-Tectonics)。这些分支的输入和物理公式不同，默认检索排除，需显式选择后核对与迁移。详细来源和覆盖范围见 [知识库清单](knowledge-manifest.json)。

用户上传的论文可在本机提取参数并记录页码、单位与假设。个人整理的论文资料不随公开源码或镜像分发。

## 源码与边界

应用源码为 AGPL-3.0-or-later；ASPECT 与其他参考源码保留各自许可，见 [许可说明](packaging/LICENSE-NOTICES.md)。本地 i2vis 的许可依据尚待提供附档，不能把应用许可当成它的许可。

完整对应源码与构建环境位于 Release 的 source ZIP，也可从镜像导出 /opt/aspect-chat 和 /opt/chatgfd-adapter。在源码包 source 目录运行 `docker build -f packaging/Dockerfile -t chatgfd-local .`。

结果、对话和密钥保存在本机工作区；云端对话需要联网及你的 API 额度。图像标定和论文参数的科学意义需要人工审阅。短程运行测试不替代网格收敛或科研基准验证。直接 Docker 模式可从本机工作目录读取结果；可选启动包支持“打开文件夹”调用主机文件管理器。
