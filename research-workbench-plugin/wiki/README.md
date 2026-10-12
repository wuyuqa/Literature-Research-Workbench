# 旁挂式 Research Wiki

Wiki 用 Markdown 保存结构化研究实体。插件默认镜像现有 Obsidian 顶层布局，不再另造一套平行的顶层目录。setup 会先检查目录是否存在，并在用户确认后只创建缺失的子目录；不会移动、重命名或覆盖已有笔记。

## 当前知识库布局映射

```text
<vault_root>/
├── 10_Weekly/                 # 周报、每周推荐、邮件草稿
├── 20_Research/
│   ├── Papers/                # 论文元数据、精读报告、引用资料
│   └── PaperGraph/            # 论文/主题/方法关系图和索引
├── 30_Synthesis/
│   ├── Gaps/                  # 研究空白、主题综合和 gap 分析
│   └── <project-folders>/     # 已有项目目录保持原样
└── 99_System/
    ├── Config/               # 本地配置和环境说明
    ├── Temp/                 # 可清理的中间产物
    └── tmp/                  # 工具临时文件
```

详细映射见 [vault-layout.md](vault-layout.md)。

## 旁路模式（可选）

如果用户不希望写入现有 vault，可把 `wiki_mode` 改为 `sidecar`，再把 `wiki_root` 指向插件目录下的 `.research-wiki/`。

每个实体使用 front matter、来源链接、创建日期和状态字段。agent 不把 token、SMTP 授权码、Zotero 私密库或实验结果凭据写入 Wiki。

## 实体

- `papers/`：论文元数据、核心主张、方法、限制和可复用组件。
- `ideas/`：研究问题、假设、状态、来源论文和淘汰原因。
- `experiment-plans/`：指标、baseline、ablation、运行顺序和预算；不保存自动执行结果。
- `claims/`：论文中的可验证论断及其证据来源。
- `graph/edges.jsonl`：实体之间的关系。

推荐关系：`idea --inspired_by--> paper`、`paper --addresses_gap--> idea`、`experiment_plan --tests--> claim`、`claim --supported_by--> paper`。

文献 agent 负责写入论文和精读结果；Idea agent 负责写入 idea 和实验设计；主控 agent 负责检查孤立实体、重复记录和缺少来源的 claim。
