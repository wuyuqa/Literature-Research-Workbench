# Literature Research Workbench

这是一个面向网络安全与模糊测试研究的 Codex 插件包，包含 5 个协作角色：主控编排、文献调研与知识库、Idea 与实验设计、ARIS 论文写作、科研绘图与汇报。

插件默认采用旁挂式 Wiki：索引、中间报告和结构化实体写入插件目录下的 `.research-wiki/`，不会移动、重命名或覆盖现有 Obsidian 笔记。只有在 `config.yaml` 中把 `wiki_root` 改成已有目录后，文献 agent 才会向该目录写入内容。

## 目录

```text
research-workbench-plugin/
├── plugin.json
├── .codex-plugin/plugin.json
├── config.example.yaml
├── skills/
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
2. 填写 `vault_root`；首次试用建议保留默认的旁挂式 `wiki_root`。
3. 在 Codex 中连接 Zotero 和 Undermind。Zotero 用于查重与导入，Undermind 用于补充论文检索。
4. 如果需要周报邮件，在 163 邮件连接器或本机凭据中配置 SMTP；不要把密码、授权码或 token 写入仓库。
5. 首次使用先运行插件的 setup skill，检查路径、连接器和写入权限。

## 安装到 Codex

目录中附带了 `marketplace.json`，可将它作为本地 marketplace 导入，然后在 Codex 的 Plugins / Sources 中安装 `literature-research-workbench`。也可以使用 Codex CLI 的本地 marketplace 命令（不同版本命令入口可能显示为 `codex plugin marketplace add`），指向该 `marketplace.json`，再从 Plugins Directory 安装。Codex 的本地 marketplace 机制和插件安装入口可能随桌面版本变化；如果 CLI 不接受文件路径，直接在 Plugins Directory 选择本地 marketplace 即可。

安装后新建一个 Codex 对话，先运行 setup，再使用自然语言调用，例如：

```text
请用文献调研 agent 搜索 ROS 2/DDS 模糊测试相关论文，查重后导入 Zotero，并生成精读报告。
请用 Idea agent 基于现有 Wiki 生成三个顶会论文方案和实验设计，不要运行实验。
请用写作 agent 根据 experiment_plan 和我提供的结果生成 LaTeX 初稿。
```

## 角色与边界

- `research-orchestrator`：分派任务、检查产物、审核交接。
- `literature-research`：搜索、查重、Zotero、精读、Wiki、周报。
- `idea-architecture`：ARS + ARIS 的 Idea、新颖性、评审、方法细化和实验设计。
- `manuscript-writing`：ARIS 写作、LaTeX 编译和 rebuttal；不使用 Nature 写作风格。
- `visual-presentation`：Nature figure、imagegen、Python/R 图表、HTML/PPT 汇报。

插件不执行实验，不部署 GPU，不监控运行任务。`experiment-plan` 只负责设计实验，实验结果由研究者提供。

## 外部 skill 的来源

- ARS：`Imbad0202/academic-research-skills`，用于 Idea、novelty 和 review 方法。
- ARIS：`wanshuiyin/Auto-claude-code-research-in-sleep`，用于 Idea、实验设计、论文写作和 rebuttal。
- Frontend Slides：`zarazhangrui/frontend-slides`，用于 HTML 汇报和演示风格。

这些仓库可能有自己的安装方式和版本变化。插件只引用稳定的 skill 名称和工作边界，不把外部仓库的密钥、缓存或私有配置提交进来。

## Git 提交

本插件目录可以单独提交。提交前确认 `config.yaml`、`.research-wiki/`、`outputs/` 和所有凭据都没有被 Git 跟踪：

```powershell
git status --short
git add research-workbench-plugin
git commit -m "Add literature research workbench plugin"
```

之后由仓库所有者自行添加远程仓库并 push。
