# Literature Research Workbench

这是一个可适配不同专业的 Codex 科研工作台插件包，包含 5 个协作角色：主控编排、文献调研与知识库、Idea 与实验设计、ARIS 论文写作、科研绘图与汇报。网络安全与模糊测试只是当前示例方向，首次使用会先询问用户专业和研究目标。

插件默认采用旁挂式 Wiki：setup 会在插件目录下的 `.research-wiki/` 创建结构化文件夹，不会移动、重命名或覆盖现有 Obsidian 笔记。Wiki 架构见 [wiki/README.md](wiki/README.md)；用户也可以在 intake 后把 `wiki_root` 指向一个新建目录。

## 目录

```text
research-workbench-plugin/
├── plugin.json
├── .codex-plugin/plugin.json
├── agents/                         # 五个真正的角色 agent
│   ├── main-orchestrator.md
│   ├── literature-researcher.md
│   ├── idea-architect.md
│   ├── manuscript-writer.md
│   └── visual-presentation.md
├── config.example.yaml
├── dependencies.json
├── install.ps1
├── DEPENDENCIES.md
├── skills/
│   ├── vendor/                    # 已随插件携带的必需 SKILL.md 和资源
│   │   ├── required/               # LaTeX、图、PPT、Zotero 等本插件必需内容
│   │   ├── local-codex/            # 文献检索和本地知识库技能
│   │   ├── local-agents/
│   │   ├── ars/
│   │   └── aris/
│   ├── setup/
│   ├── research-orchestrator/
│   ├── literature-research/
│   ├── idea-architecture/
│   ├── manuscript-writing/
│   └── visual-presentation/
└── wiki/
    ├── README.md
    └── templates/
```

## 环境配置

1. 将 `config.example.yaml` 复制为 `config.yaml`。
2. 先运行 intake，填写专业、子方向、语言、目标 venue、时间范围和输出目录；不能直接沿用示例专业。
3. 在 Codex 中连接 Zotero 和 Undermind。Zotero 用于查重与导入，Undermind 用于补充论文检索。
4. 如果需要周报邮件，把 `smtp.username` 和收件人写入本地 `config.yaml`，把授权码放进 `NETEASE_SMTP_AUTH_CODE` 环境变量；不要把密码、授权码或 token 写入仓库。
5. 可选 API 的入口是 `SEMANTIC_SCHOLAR_API_KEY`、`EXA_API_KEY` 和 `GEMINI_API_KEY` 环境变量。
6. 首次使用先运行插件的 setup skill，检查路径、Wiki 文件夹、连接器和写入权限。

## 新用户安装

用户只需要下载或克隆 `research-workbench-plugin/` 这一目录。`research-workbench-marketplace/` 是开发者用于本地 marketplace 注册的兼容入口，不是第二份需要配置的知识库，也不需要复制到 Obsidian 中。

在 Windows PowerShell 中执行：

```powershell
cd research-workbench-plugin
.\install.ps1
```

脚本会安装 ARS、ARIS、Frontend Slides、Zotero 和 Undermind，并注册本地工作台插件。插件自身已携带本地技能、ARS/ARIS 的技能镜像、LaTeX、图形、PPT 和五个 agent 定义。Undermind 是 app connector，首次使用可能需要登录授权。

安装后重启 Codex，先调用 `literature-research-workbench:setup`。

## 开发者 marketplace 安装

仓库旁附带的 `research-workbench-marketplace/` wrapper 只供开发者测试 marketplace 安装：

```powershell
codex plugin marketplace add .\research-workbench-marketplace
codex plugin add literature-research-workbench --marketplace personal-research-workbench
```

安装后新建一个 Codex 对话，先运行 setup，再使用自然语言调用，例如：

```text
请用文献调研 agent 搜索 ROS 2/DDS 模糊测试相关论文，查重后导入 Zotero，并生成精读报告。
请用 Idea agent 基于现有 Wiki 生成三个顶会论文方案和实验设计，不要运行实验。
请用写作 agent 根据 experiment_plan 和我提供的结果生成 LaTeX 初稿。
```

## 五个 agent

- `main-orchestrator`：分派任务、审核交接和最终质量检查。
- `literature-researcher`：Undermind/GS/arXiv/S2/CNKI 检索、去重、Zotero、精读、Wiki 和周报。
- `idea-architect`：ARS + ARIS 头脑风暴、新颖性检查、论文架构和实验设计。
- `manuscript-writer`：ARIS 优先的计算机安全论文写作、LaTeX、引用审计和 rebuttal。
- `visual-presentation`：可编辑论文图、数据图、架构图和论文转 PPT。

每个 agent 的角色定义位于 `agents/`，每个 agent 使用的具体技能位于 `skills/`，两者是不同层级：agent 负责决策和交接，skill 负责一个可复用动作。

完整的 agent-skill 路由见 [agents/skill-routing.md](agents/skill-routing.md)。`skills/vendor/` 是随包保存的上游实现和资源；为了确保新环境能发现并调用，工作台实际使用的 skill 已复制到 `skills/` 一级目录，而不是只留在 vendor 中。

插件不执行实验，不部署 GPU，不监控运行任务。`experiment-plan` 只负责设计实验，实验结果由研究者提供。

## 外部 skill 的来源

- ARS：`Imbad0202/academic-research-skills`，用于 Idea、novelty 和 review 方法。
- ARIS：`wanshuiyin/Auto-claude-code-research-in-sleep`，用于 Idea、实验设计、论文写作和 rebuttal。
- Frontend Slides：`zarazhangrui/frontend-slides`，用于 HTML 汇报和演示风格。

这些仓库可能有自己的安装方式和版本变化。插件只引用稳定的 skill 名称和工作边界，不把外部仓库的密钥、缓存或私有配置提交进来。

详细的上游版本、许可证、可用性和实验执行边界见 [DEPENDENCIES.md](DEPENDENCIES.md)。

GitHub 上传前请阅读 [SECURITY.md](SECURITY.md) 和 [GITHUB_UPLOAD.md](GITHUB_UPLOAD.md)。推荐上传版本为 `v0.1.3`，只上传本插件目录，不上传整个 Obsidian 知识库。

## Git 提交

本插件目录可以单独提交。提交前确认 `config.yaml`、`.research-wiki/`、`outputs/` 和所有凭据都没有被 Git 跟踪：

```powershell
git status --short
git add research-workbench-plugin
git commit -m "Add literature research workbench plugin"
```

之后由仓库所有者自行添加远程仓库并 push。
