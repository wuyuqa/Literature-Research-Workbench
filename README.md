# Literature Research Workbench

可迁移的 Codex 科研工作台插件，面向不同专业的文献调研、研究 Idea、实验设计、LaTeX 写作、科研绘图和汇报制作。

当前发布版本：`v0.1.4`

## 目录

- [`research-workbench-plugin/`](research-workbench-plugin/)：插件 canonical source。新用户只需要安装这个目录。
- [`research-workbench-marketplace/`](research-workbench-marketplace/)：本地 marketplace 测试入口，供开发者注册和测试安装。

插件包含五个角色 agent：主控编排、文献调研、Idea 架构、论文写作、科研绘图与 PPT。工作台还携带 55 个可直接发现的 skill，包含 GS、arXiv、Semantic Scholar、CNKI、Zotero、ARS、ARIS、LaTeX、Nature Figure、imagegen、Presentations 和 Frontend Slides。

## 安装

下载或克隆仓库后，在 PowerShell 中执行：

```powershell
cd research-workbench-plugin
.\install.ps1
```

脚本会安装 ARS、ARIS、Frontend Slides、Zotero 和 Undermind，并注册工作台插件。LaTeX、图形和 PPT 所需 skill 已随插件携带。

安装后重启 Codex，先运行：

```text
literature-research-workbench:setup
```

首次使用会询问研究领域、子方向、关键词、目标 venue、时间范围、语言和输出位置，不默认限定为网络安全或模糊测试。

## 配置和隐私

复制 `research-workbench-plugin/config.example.yaml` 为本地 `config.yaml`。SMTP 授权码和搜索 API key 通过环境变量配置，不要写入仓库。上传 GitHub 前运行：

```powershell
.\research-workbench-plugin\scripts\github-preflight.ps1
```

详见 [`SECURITY.md`](research-workbench-plugin/SECURITY.md) 和 [`GITHUB_UPLOAD.md`](research-workbench-plugin/GITHUB_UPLOAD.md)。插件只设计实验，不执行 fuzzing、GPU 任务或实验脚本。
