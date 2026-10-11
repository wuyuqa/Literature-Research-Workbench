---
name: s2-search
description: 调用 Semantic Scholar Graph API 搜索论文，按相关性 + 引用数排序。返回标题、摘要、作者、引用数、influentialCitationCount、venue、年份、arxiv_id/doi。用于 workflow 1 周推荐补充 arXiv 缺失的高引论文（含会议论文），以及 workflow 2 用户搜索的另一个 API 源。
allowed-tools: Read, Write, Bash
---

# Semantic Scholar 搜索

## 目标

Semantic Scholar (S2) 收录范围比 arXiv 更广（含会议论文、期刊论文、跨学科），且自带引用数与影响力数据。本 skill 独立调用 S2 Graph API 的 `/paper/search` 端点，作为周推荐和 workflow 2 的另一个 API 源。

## 输入

- `--keywords` 关键词（必填，单一查询字符串；S2 不接受多关键词数组，需合并）
- `--year` 年份范围（如 `2024-2026` 或单年 `2025`；可选）
- `--start-date` `--end-date` YYYY-MM-DD（与 year 互斥；更精确的日期范围）
- `--top` 返回 top N（默认 20）
- `--output` 输出 JSON

## 调用方式

```powershell
python "C:/Users/86159/.Codex/skills/s2-search/scripts/s2_search.py" `
  --keywords "DDS fuzzing middleware security" `
  --start-date "2026-05-19" --end-date "2026-05-26" `
  --top 20 `
  --output "s2_results.json"
```

## 输出格式

```json
{
  "source": "s2",
  "query": {"keywords": "...", "date_range": "2026-05-19:2026-05-26"},
  "total_found": 35,
  "papers": [
    {
      "source": "s2",
      "paper_id": "abc123",
      "title": "...",
      "authors": ["..."],
      "abstract": "...",
      "year": 2026,
      "publication_date": "2026-05-23",
      "venue": "USENIX Security 2026",
      "citation_count": 12,
      "influential_citation_count": 3,
      "arxiv_id": "2505.12345",
      "doi": "10.1145/...",
      "url": "https://www.semanticscholar.org/paper/...",
      "open_access_pdf": "..."
    }
  ]
}
```

## API 速率限制

- 未认证：100 请求/5分钟
- 加 API key（环境变量 `SEMANTIC_SCHOLAR_API_KEY` 或 yaml 配置）：1 请求/秒
- 遇 429 等待 10 秒后重试

## 与其他 skill 集成

- 被 `start-my-day`（schedule 和 manual）调用
- 被 `search_multi_source.py` 作为 s2 源
- 被统一 agent 在 Workflow 2 调用

## 与 arxiv-search 的互补

| skill | 强项 | 弱项 |
|-------|------|------|
| arxiv-search | 最新预印本，日期精准 | 无引用数，覆盖范围仅 arXiv |
| s2-search | 覆盖会议+期刊+arXiv，自带引用 | 索引滞后（论文发布后 1-2 周才录入） |

两者合并可以同时拿到最新预印本 + 高引论文。
