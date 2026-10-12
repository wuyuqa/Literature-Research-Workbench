# 旁挂式 Research Wiki

Wiki 用 Markdown 保存结构化研究实体。首次运行 setup 会在 `wiki_root` 下建立下面的文件夹架构；默认使用插件旁路目录 `.research-wiki/`，因此不会移动或重命名现有笔记。用户也可以在 intake 后把 `wiki_root` 指向一个新建的知识库目录。

## 文件夹架构

```text
<wiki_root>/
├── 00_System/          # index、配置快照、agent 交接和审计记录
├── 01_Literature/      # papers、阅读报告、来源和引用关系
├── 02_Themes/          # 主题、方法谱系、研究现状和 gap
├── 03_Ideas/           # idea、proposal、淘汰记录
├── 04_ExperimentPlans/ # 只保存实验设计，不执行实验
├── 05_Manuscripts/     # LaTeX 项目、章节草稿、审稿回复
├── 06_Figures/         # 图形规格、源数据、SVG/HTML/PPTX
├── 07_Presentations/   # 汇报 PPT 和 HTML slides
└── 90_Reports/         # 周报、任务报告和交接摘要
```

每个实体使用 front matter、来源链接、创建日期和状态字段。agent 不把 token、SMTP 授权码、Zotero 私密库或实验结果凭据写入 Wiki。

## 实体

- `papers/`：论文元数据、核心主张、方法、限制和可复用组件。
- `ideas/`：研究问题、假设、状态、来源论文和淘汰原因。
- `experiment-plans/`：指标、baseline、ablation、运行顺序和预算；不保存自动执行结果。
- `claims/`：论文中的可验证论断及其证据来源。
- `graph/edges.jsonl`：实体之间的关系。

推荐关系：`idea --inspired_by--> paper`、`paper --addresses_gap--> idea`、`experiment_plan --tests--> claim`、`claim --supported_by--> paper`。

文献 agent 负责写入论文和精读结果；Idea agent 负责写入 idea 和实验设计；主控 agent 负责检查孤立实体、重复记录和缺少来源的 claim。
