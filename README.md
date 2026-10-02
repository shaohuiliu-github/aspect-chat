# ASPECT Chat 1.1.0

通过对话描述、修改和运行本机 ASPECT 模型。界面支持中文/英文、PDF/图片/PRM 上传、参数文件查看、参数扫描、初始密度/温度/黏度预览，以及运行状态和日志。ASPECT 输出实时保存到本机文件夹，可以直接用 ParaView 打开。

[English](README-English.md) · [下载启动包](https://github.com/shaohuiliu-github/aspect-chat/releases/tag/v1.1.0)

## 使用

1. 安装并启动 Docker Desktop；Linux 也可使用 Docker Engine，Windows 使用 Linux containers。
2. 下载 Release 中的 `ASPECT-Chat-1.1.0-online.zip`，解压到本地文件夹。
3. Mac 双击 `Start.command`，Windows 双击 `Start.bat`，Linux 运行 `bash start.sh`。首次自动下载完整运行环境。
4. 在设置中选择服务商，输入自己的 API 密钥；对话顶部选择模型。设置中还可调整单任务核数、总核数和时间上限。
5. 对话生成或导入 PRM，查看参数并提交计算。停止应用用 Stop；结果和聊天保留在自己的 `workspace` 中。

运行环境和知识库已经封装，不需要安装 ASPECT、MPI、Python，也不需要注册容器仓库账号。大型模型仍需要给 Docker 分配足够的 CPU 和内存。使用云端模型对话需要网络和自己的 API 额度。

```sh
docker pull ghcr.io/shaohuiliu-github/aspect-chat:1.1.0
```

结果位置：`workspace/runs/<任务编号>/output`。模型文件：`workspace/cases/<模型编号>/draft.prm`。API 密钥和聊天也是本地保存，请不要把使用过的工作目录发给别人。主机“打开文件夹”按钮依赖启动器窗口保持运行。

## 知识库与源码

内置 ASPECT 3.1.0 完整源码及全部 1,796 个 PRM 文件、293 页官方手册、1,159 页官方 API、1,696 个独立运行时参数条目、辅助脚本和算例输入依赖目录，以及 World Builder 1.1.1 的实际参数定义。开发版源码和 Wiki 导航标为参考资料，默认检索不使用它们。来源、版本和覆盖统计见 [knowledge-manifest.json](knowledge-manifest.json)。

知识库通过检索提供相关内容；模型还须实际验证，并进行科学判断。图片转物理场需要坐标、色标和转换关系。描述预期效果会生成候选模型，当前不进行自动反演优化。FastScape 未启用，需要额外程序或自定义插件的案例须检查依赖。

本仓库提供应用和封装源码。Release 的 `ASPECT-Chat-1.1.0-source.zip` 提供完整构建上下文，包括官方 ASPECT 源码和离线知识库。对应源码也在镜像 `/opt/aspect-chat` 中，可使用 docker cp 导出。离线源码包内 `source/` 目录可按 `packaging/Dockerfile` 重建，需充足的编译内存。

两种架构各通过 35 项测试及 5 个真实 ASPECT 任务。Windows 启动器在 Linux PowerShell 中模拟验证，尚未实测 Windows 桌面；所有算例未逐一运行认证。

应用采用 AGPL-3.0-or-later，ASPECT 采用 GPL-2.0-or-later，见 [LICENSE](LICENSE) 和 [依赖许可](packaging/LICENSE-NOTICES.md)。项目未获上游官方背书。
