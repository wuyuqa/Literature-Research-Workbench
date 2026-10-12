# Agent 与 skill 路由表

agent 是决策、询问和交接层；skill 是可复用动作层。每次 agent 交付必须在报告中记录实际调用的 skill 名称和产物路径。`vendor/` 只是随包保存的上游实现和资源，真正可发现的入口已复制到 `skills/` 一级目录。

| agent | 必须优先调用的插件内 skill | 外部 connector |
|---|---|---|
| main-orchestrator | `setup`、`research-orchestrator`、`intake` | 无 |
| literature-researcher | `literature-research`、`gs-search`、`arxiv-search`、`s2-search`、`cnki-search`、`zotero-check`、`paper-analyze`、`research-wiki` | Undermind、Zotero |
| idea-architect | `ars-lit-review`、`ars-plan`、`ars-outline`、`ars-reviewer`、`aris-research-lit`、`aris-idea-creator`、`aris-research-refine`、`aris-novelty-check`、`aris-research-review`、`aris-experiment-plan` | 无 |
| manuscript-writer | `aris-paper-plan`、`aris-paper-write`、`aris-paper-compile`、`aris-citation-audit`、`aris-paper-claim-audit`、`aris-rebuttal`、`latex-compile`、`latex-doctor` | 无 |
| visual-presentation | `nature-figure`、`imagegen`、`presentations`、`frontend-slides`、`image-svg-pptx-pro`、`aris-paper-figure`、`aris-paper-slides`、`aris-slides-polish` | 无 |

如果插件内 skill 与外部同名，优先使用 `literature-research-workbench:<skill-name>`；只有插件内文件缺失时才回退到上游插件，并在交接报告中标明回退原因。
