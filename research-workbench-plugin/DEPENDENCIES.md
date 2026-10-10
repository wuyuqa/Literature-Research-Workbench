# External dependencies and provenance

The packaged role skills refer to real skills and apps by name. This plugin does not copy large upstream repositories into the package; it keeps the workbench small and avoids silently replacing upstream updates.

## Skills

| Dependency | Used by | Source | License / note |
|---|---|---|---|
| ARIS | idea-architecture, manuscript-writing | https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep | MIT; use `research-lit`, `idea-creator`, `novelty-check`, `research-review`, `research-refine`, `experiment-plan`, `research-wiki`, `paper-writing`, and `rebuttal`. Do not enable execution skills. |
| ARS | idea-architecture | https://github.com/Imbad0202/academic-research-skills | CC BY-NC 4.0; use `research-lit`, `idea-creator`, `novelty-check`, `research-review`, and `research-refine-pipeline`. Keep attribution and do not use for commercial distribution without checking the license. |
| Frontend Slides | visual-presentation | https://github.com/zarazhangrui/frontend-slides | MIT; use the core frontend-slides skill for HTML presentations. |
| Codex LaTeX | manuscript-writing | bundled `latex` plugin | Use `latex-compile` and `latex-doctor`; no additional TeX installation is assumed. |
| Nature Figures | visual-presentation | installed `nature-skills` plugin | Use only the figure workflow; do not route manuscript prose through Nature-style writing. |

## Connected apps

- Zotero is an installed Codex plugin and is used for lookup, duplicate checks, export, and citation insertion.
- Undermind is an optional dependency. It was not present in the available plugin search when this package was built; connect it later if it becomes available in your workspace.

## Execution boundary

The package may design experiments and record user-supplied results. It deliberately does not include or call ARIS `experiment-bridge`, `run-experiment`, `monitor-experiment`, `analyze-results`, or `auto-review-loop`.
