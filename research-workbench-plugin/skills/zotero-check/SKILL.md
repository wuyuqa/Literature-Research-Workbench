---
name: zotero-check
description: 检查论文列表中哪些已存在于本地 Zotero 库（通过 Better BibTeX 自动导出的 JSON），用于推荐时的去重过滤。读取 BBT JSON 后按 arxiv_id / doi / 标题归一化匹配。
allowed-tools: Read, Write, Bash
---

# Zotero 去重检查

## 目标

判定一组候选论文中哪些已经被收录到本地 Zotero 库，避免在每周推荐/顶会推荐中重复出现。依赖 Better BibTeX (BBT) 插件的自动导出 JSON。

## 先决条件

1. 用户已在 Zotero 中安装 Better BibTeX 插件
2. BBT 设置了 Automatic Export → JSON 格式，导出到固定路径
3. 该路径在 `99_System/Config/academic_agent.yaml` 的 `zotero.bbt_json_path` 字段中配置

如果 JSON 文件不存在，本 skill 返回所有论文为「未匹配」，并在日志中提示用户开启 BBT 自动导出。

## 输入格式

候选论文 JSON 数组（来自 arxiv-search、s2-search 等的输出）：

```json
[
  {
    "title": "Paper Title",
    "arxiv_id": "2501.12345",    // 可选
    "doi": "10.1145/...",          // 可选
    "authors": ["Author 1"],
    ...其他字段...
  }
]
```

## 输出格式

```json
{
  "filtered": [...],     // 过滤后保留的论文（不在 Zotero）
  "skipped": [
    {
      "paper": {...},
      "reason": "matched arxiv_id 2501.12345 in Zotero",
      "zotero_key": "ABC123"
    }
  ],
  "stats": {
    "input_count": 20,
    "filtered_count": 15,
    "skipped_count": 5,
    "bbt_json_available": true
  }
}
```

## 调用方式

### 命令行（独立测试）

```powershell
python "C:/Users/86159/.Codex/skills/zotero-check/scripts/check_zotero.py" `
  --bbt-json "C:/Users/86159/Zotero/better-bibtex.json" `
  --input "candidates.json" `
  --output "filtered.json" `
  --threshold 0.85
```

### Agent 内调用

`/zotero-check {input_json_path}`

读取 `academic_agent.yaml` 自动定位 BBT JSON。

## 匹配规则

按以下优先级匹配：

1. **arxiv_id 精确匹配**（最高优先级）
   - 在 BBT JSON 的 `items[].extra` 字段中搜索 `arxiv:2501.12345` 或类似形式
   - 也检查 `items[].url` 是否包含 `arxiv.org/abs/2501.12345`

2. **DOI 精确匹配**（次高）
   - 在 `items[].DOI` 字段中匹配

3. **标题归一化模糊匹配**（兜底）
   - 标题归一化：小写、去标点、去多余空格
   - 用 `difflib.SequenceMatcher.ratio()` 计算相似度
   - 超过 `title_similarity_threshold`（默认 0.85）判定为同一论文

## 错误处理

| 场景 | 行为 |
|------|------|
| BBT JSON 路径不存在 | 返回所有论文为「未匹配」，stats 标注 `bbt_json_available: false` |
| BBT JSON 解析失败 | 同上，并记录错误日志 |
| Zotero 库为空 | 所有论文都「未匹配」，正常返回 |
| arxiv_id 格式异常 | 跳过 arxiv_id 匹配，回退到 doi 和标题 |

## 与其他 skill 的集成

- 由 `start-my-day` 在 manual 模式下调用（schedule 模式跳过）
- 由 `conf-papers` 在生成推荐前调用
- 由统一 agent 在 Workflow 2 用户挑选前调用（可选展示「这篇已在 Zotero」标记）

## 输出在邮件正文中的呈现

如果做了 Zotero 去重，邮件正文顶部增加一行：

> 本周共搜到 N 篇，过滤掉 M 篇已收录到 Zotero 的论文，最终推荐 top {top_n} 篇。

如果跳过了去重：

> ⚠️ 本次未做 Zotero 去重（BBT JSON 不可用），可能包含已收录论文。
