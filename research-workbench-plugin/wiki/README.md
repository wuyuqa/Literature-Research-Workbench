# 旁挂式 Research Wiki

Wiki 用 Markdown 保存结构化研究实体，不改变现有笔记目录。默认目录由 `config.yaml` 的 `wiki_root` 指定。

## 实体

- `papers/`：论文元数据、核心主张、方法、限制和可复用组件。
- `ideas/`：研究问题、假设、状态、来源论文和淘汰原因。
- `experiment-plans/`：指标、baseline、ablation、运行顺序和预算；不保存自动执行结果。
- `claims/`：论文中的可验证论断及其证据来源。
- `graph/edges.jsonl`：实体之间的关系。

推荐关系：`idea --inspired_by--> paper`、`paper --addresses_gap--> idea`、`experiment_plan --tests--> claim`、`claim --supported_by--> paper`。

文献 agent 负责写入论文和精读结果；Idea agent 负责写入 idea 和实验设计；主控 agent 负责检查孤立实体、重复记录和缺少来源的 claim。
