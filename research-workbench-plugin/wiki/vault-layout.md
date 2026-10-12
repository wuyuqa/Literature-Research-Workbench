# Vault layout contract

这是插件和当前 Obsidian 知识库之间的路径契约。路径相对于 `vault_root`，由 `config.example.yaml` 的 `vault_layout` 覆盖。

| 内容 | 默认目录 | 写入者 |
|---|---|---|
| 本周论文推荐、周报草稿 | `10_Weekly/` | literature-researcher |
| 论文元数据、精读报告、PDF 关联笔记 | `20_Research/Papers/` | literature-researcher |
| 论文关系图、主题索引、方法图谱 | `20_Research/PaperGraph/` | literature-researcher / main-orchestrator |
| Idea、研究现状、综合结论 | `30_Synthesis/` | idea-architect / main-orchestrator |
| gap 和研究空白 | `30_Synthesis/Gaps/` | idea-architect |
| 本地配置快照 | `99_System/Config/` | setup（只写用户确认的非秘密配置） |
| 可清理中间文件 | `99_System/Temp/` | all agents |
| 工具临时文件 | `99_System/tmp/` | scripts |

现有 `30_Synthesis` 项目文件夹、`20_Research/PaperGraph` 内容和 `99_System` 配置由用户拥有，agent 只能追加经过确认的内容。任何 token、SMTP 授权码、私有 Zotero 导出和原始凭据都留在环境变量或 connector 中，不进入这些目录。
