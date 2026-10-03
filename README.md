# chatGFD

**用对话建立模型，用模拟探索地球科学想法。**

Geophysical Fluid Dynamics Simulation · 地球流体动力学模拟

[English](README-English.md) · [观看 4 分钟 Demo](https://youtu.be/BNjAN6mV1Xs) · [安装说明](INSTALL.md) · [下载与发布记录](https://github.com/shaohuiliu-github/chatGFD/releases/tag/v2.0.5)

chatGFD 是一个早期 demo 产品，让地球科学想法更容易建模、教学和讨论。描述你的想法，用 **ASPECT 或 i2vis** 建立简单模型，检查输入参数和初始场，修改参数，再查看模型如何演化。

对话助手协助组织输入与解释设置，数值求解由实际的动力学程序完成。输入文件可以手动编辑，结果保存在本机，可以继续用 ParaView 等软件查看。

### “你是什么模型？”

这段演示对话说明了所选语言模型与实际求解器的区别。语言模型负责对话；ASPECT / i2vis 负责数值计算。

![chatGFD 对话：What model are you?，说明语言模型与 ASPECT 求解器](docs/screenshots/chatgfd-model-identity.png)

## 为什么做 chatGFD

- **地球科学教育：** 用小型数值实验把浮力、黏度、温度和边界条件变成看得见的过程，帮助教师与学生讨论“哪些假设导致了这样的结果”。
- **学科交叉：** 为地质、地球化学、地震、古地磁等领域提供讨论物理机制的起点。概念图、论文或经过标定的图像可以成为初始模型的依据，参数与假设便于共同检查和修改。
- **动力学入门：** 更快建立第一个可运行模型，逐步理解几何、材料、初始场和边界条件怎样配合，并继续编辑输入文件学习。
- **地质假说的初步探索：** 把一个可能的机制转成简单实验，对比不同假设，在模型明确的适用范围内探索物理可行性。
- **专业动力学家的新想法：** 协助建立初始几何、初始场和参数文件，作为进一步完善物理、分辨率和实现的起点。

目标是让建模的第一步更容易，让教学与合作更直观，同时让科学假设始终可以被检查。

**当前局限：** 知识库覆盖范围和作者可投入的开发时间有限，目前适合简单模型，还不太适用于复杂科研模型。物理参数对齐是首要工作：数值、单位、材料定律、边界条件、缺失项和假设都需要审阅；随后还需评估网格与求解器收敛。运行成功本身不能证明地质假说正确，也不能证明论文模型已被复现。

求解器、Python 环境和离线知识库已封装在 Docker 镜像中，无需下载 GitHub 源码或单独安装求解器。

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

## 从对话到结果

**1. 检查初始场，编辑参数，查看运行状态。** 温度、密度和参考黏度预览直接来自支持的输入设置。右侧任务栏显示时间命名的任务、成功或失败状态、结果文件夹入口和日志。需要修改时，可以点击 **Edit parameters**，再点 **Run again**。

![ASPECT 初始温度预览、编辑与再次运行按钮，以及右侧任务成功与失败状态](docs/screenshots/chatgfd-preview-and-tasks.png)

**2. 把层析图转成模型输入，并与原图对比。** 坐标、色标、单位和转换关系需要明确。这里保留原图配色以便比较，密度转换是教学代理关系，不能仅凭地震波速唯一反演密度。图像由 ASPECT 官方案例中的 LLNL-G3D-JPS 数据重绘，见 [图像来源](docs/screenshots/README.md)。

![上传层析图与转换后参考密度的并排对比，采用相同配色和明确的教学转换关系](docs/screenshots/tomography-to-density.png)

**3. ASPECT：比较三个 Rayleigh 数。** 相同的二维热对流设置，只改变黏度以改变 Ra；下图来自实际求解器输出，在 ParaView 中显示。可以打开保存的 `solution.pvd` 播放演化；这些粗分辨率演示不代表已完成收敛验证。

![ASPECT 实际温度结果：Ra 为 1e4、1e5 和 1e6 的二维地幔对流对比](docs/screenshots/aspect-rayleigh-comparison.png)

**4. i2vis：查看热异常的早期演化。** 下图来自实际保存的 i2vis 输出，展示全模型与局部放大，以及初始和当前温度等值线。动画、密度对比和 ParaView 操作见 [完整 Demo](https://youtu.be/BNjAN6mV1Xs)。

![i2vis 实际输出：2 Myr 时的热异常，全模型、局部放大及初始和当前 1700 K 等值线](docs/screenshots/i2vis-hot-anomaly-evolution.png)

[六个简短案例提示词](DEMO_CASES.md)可直接复制，首页也可点击填入。论文和层析图案例需要上传附件；教学默认参数会在对话中说明，后续可随时修改。

Demo 视频为缩短等待而经过剪辑，部分已保存回复逐步回放；演化图来自实际求解器输出。论文示例是明确简化的二维教学近似。

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

## 致谢与相关项目

特别感谢 **Taras Gerya 教授** 对本项目的支持。感谢 ASPECT、i2vis 的开发者以及地球动力学社区。

- [ASPECT 官方网站](https://aspect.geodynamics.org/) · [ASPECT 源码](https://github.com/geodynamics/aspect)
- [i2vis 方法：Gerya & Yuen (2003)](https://doi.org/10.1016/j.pepi.2003.09.006)
- [I2ELVIS planet 公开参考代码](https://github.com/FormingWorlds/i2elvis_planet)：与本 demo 的 i2vis 运行分支不同。
