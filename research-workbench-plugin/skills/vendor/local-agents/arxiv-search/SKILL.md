---
name: arxiv-search
description: 直接调用 arXiv API 搜索论文，支持关键词、分类、日期范围、top N。返回结构化 JSON（标题、作者、摘要、arxiv_id、发布日期、分类、链接）。用于 workflow 2 用户搜索和 workflow 1 周推荐的 API 源。
allowed-tools: Read, Write, Bash
---

# arXiv 搜索

## 目标

通过 arXiv 公开 API（`http://export.arxiv.org/api/query`）搜索论文，无浏览器依赖，可在 schedule 远程 agent 中执行。

## 输入

- `--keywords` 关键词列表（逗号或空格分隔；含空格的短语用引号）
- `--categories` arXiv 分类（默认 `cs.CR,cs.SE,cs.RO,cs.AI`，符合用户研究方向）
- `--days` 搜索过去 N 天（默认 7，对应周推荐）
- `--top` 返回 top N（默认 20）
- `--output` 输出 JSON 路径

## 调用方式

### 命令行

```powershell
python "C:/Users/86159/.Codex/skills/arxiv-search/scripts/arxiv_search.py" `
  --keywords "DDS fuzzing,middleware security" `
  --categories "cs.CR,cs.SE,cs.RO" `
  --days 7 --top 20 `
  --output "arxiv_results.json"
```

### Agent 内

`/arxiv-search {keywords} [--days N] [--top N]`

## 输出格式

```json
{
  "source": "arxiv",
  "query": {
    "keywords": ["DDS fuzzing"],
    "categories": ["cs.CR", "cs.SE"],
    "days": 7,
    "search_window": {"start": "2026-05-19", "end": "2026-05-26"}
  },
  "total_found": 42,
  "papers": [
    {
      "source": "arxiv",
      "arxiv_id": "2505.12345",
      "title": "...",
      "authors": ["Author 1", "Author 2"],
      "abstract": "...",
      "published_date": "2026-05-23",
      "categories": ["cs.CR"],
      "url": "https://arxiv.org/abs/2505.12345",
      "pdf_url": "https://arxiv.org/pdf/2505.12345",
      "primary_category": "cs.CR"
    }
  ]
}
```

## 错误处理

- arXiv API 限流（HTTP 429）→ 重试 3 次，指数退避
- 网络超时（60 秒）→ 同上
- XML 解析失败 → 跳过该 entry，记录日志

## 与其他 skill 的集成

- 被 `start-my-day` 在 schedule 和 manual 模式下都调用
- 被 `search_multi_source.py` 作为 arxiv 源的输入
- 被统一 agent 在 Workflow 2 调用

## 与 start-my-day/scripts/search_arxiv.py 的关系

`arxiv-search` 是 arXiv 部分的独立可调 cli 封装；`start-my-day` 自身仍可保留原 search_arxiv.py（含 S2 部分等综合逻辑），不强制重构原脚本。
