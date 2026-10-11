---
name: start-my-day
description: 每周论文推荐 — 本地手动触发，4 源（arXiv + S2 + GS + CNKI）搜索 → 多源合并 → Zotero 去重 → 本地笔记 → 精读 top_n_detailed 篇 → 邮件推送。自动化周推荐请使用独立的 GitHub Actions 仓库（weekly-papers-bot）。
---

# start-my-day — 每周论文推荐

## 调用

```
/start-my-day                        # 默认：搜索本周，发邮件
/start-my-day --week 2026-W22        # 指定 ISO 周
/start-my-day --no-email             # 不发邮件（调试用）
```

## 共用配置

- 环境变量 `OBSIDIAN_VAULT_PATH`（已设置）
- `$VAULT/99_System/Config/research_interests.yaml`（研究方向与关键词）
- `$VAULT/99_System/Config/academic_agent.yaml`（邮件/Zotero/多源配置）

---

## 执行步骤

### 步骤 0：解析参数

```python
VAULT   = os.environ["OBSIDIAN_VAULT_PATH"]
WEEK    = args.week or None   # 如 "2026-W22"；空则用当前周
NO_EMAIL = args.no_email
```

### 步骤 1：确定搜索窗口

> **⚠️ 严格规定**：搜索窗口的天数**必须**从配置文件读取，**绝对禁止**自行推算或硬编码。
> 读取优先级：`weekly.window_days` → `search.default_days` → 兜底值 7。

```python
import yaml
from datetime import datetime, timedelta
from pathlib import Path

# 1. 读取配置（必读，不得硬编码）
cfg_path = Path(r"E:\obsidian_note\文献管理库\文献知识库\99_System\Config\academic_agent.yaml")
with cfg_path.open("r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

# 优先用 weekly.window_days（周报专用窗口），缺失则回落到 search.default_days
WINDOW_DAYS = (
    cfg.get("weekly", {}).get("window_days")      # 周报专用，如 7
    or cfg.get("search", {}).get("default_days")  # 通用默认，如 30
    or 7                                           # 最终兜底
)

# 2. 计算窗口
if WEEK:
    # --week 模式：只搜该自然周（周一~周日），固定 7 天
    year, w = WEEK.split("-W")
    start = datetime.fromisocalendar(int(year), int(w), 1)
    end   = start + timedelta(days=6)
    label = WEEK
else:
    # 默认模式：今日上推 WINDOW_DAYS 天
    end   = datetime.now()
    start = end - timedelta(days=WINDOW_DAYS)
    label = f"{end.isocalendar().year}-W{end.isocalendar().week:02d}"

print(f"搜索窗口：{start.date()} ~ {end.date()}（共 {(end - start).days} 天，window_days={WINDOW_DAYS}）")
```

**验证**：打印出的天数必须 = `weekly.window_days` 配置值（或 7 天，若使用 `--week`）。
若天数不符，立即停止并报错，不得继续执行后续步骤。

### 步骤 2：聚合研究关键词

从 `research_interests.yaml` 读出所有 `research_domains.*.keywords`（去重），优先使用 priority >= 5 的方向。

### 步骤 3：扫描已有笔记

```bash
python "$SKILL_DIR/scripts/scan_existing_notes.py" \
  --vault "$VAULT" \
  --output "$SKILL_DIR/existing_notes_index.json"
```

### 步骤 4：多源搜索

4 源全开（arxiv + s2 + gs + cnki），需 Chrome DevTools MCP 已连接。

#### 4a. GS 搜索 → 保存 JSON

> **🚨 绝对禁止**：
> - 禁止创建任何手工 `build_merged_final.py` 或类似脚本来硬编码论文列表
> - 禁止手动填写 `published_date`（除非来自论文页面的实际信息）
> - 禁止手动设置 `scores`（必须由 `search_multi_source.py` 计算）
> - 即使 arXiv/S2 全部 429，也必须走 `search_multi_source.py --sources gs` 流程

> **重要**：GS 搜索必须同时带年份过滤 + 按日期排序，否则高引用老论文会混入周报。
> 使用 `as_ylo` + `scisbd=1`（按日期降序）双重过滤：

**正常流程：**
```
1. 导航至 https://scholar.google.com/scholar?q={URL_ENCODED_KEYWORDS}&hl=en&num=20&as_ylo={START_YEAR}&scisbd=1
   其中 START_YEAR = start_date.year（搜索窗口起始年，如 2026）
   scisbd=1 表示按日期降序排（最新优先），确保新论文排前面
2. evaluate_script 返回原始结果对象 {total, resultCount, results:[...]}
3. 保存到 $SKILL_DIR/gs_results.json
```

**验证码 / sorry 页拦截处理（⚠️ 不得直接跳过，必须按以下流程重试）：**

```
检测条件：URL 包含 "sorry/index" 或页面标题含 "unusual traffic" 或结果为空

第 1 次拦截：
  → 截图当前页面，告知用户：
    「Google Scholar 遇到验证，请在 Chrome 中手动完成验证，完成后告诉我继续。」
  → 等待用户确认（阻塞，直到用户回复）

用户确认后第 1 次重试：
  → 重新导航同一 URL，等待 15 秒页面加载
  → 再次检测是否仍被拦截

若重试后仍被拦截，第 2 次通知：
  → 再次截图，提示用户重新验证
  → 再等待用户确认

用户再次确认后第 2 次重试：
  → 重新导航，等待 15 秒
  → 若仍失败，第 3 次（最终）重试：等待 30 秒后再导航一次

3 次重试全部失败后才跳过：
  → 在笔记中标注「GS：3 次重试后仍被拦截，已跳过」
  → 继续执行后续步骤（不中断整个周报）
```

```python
import json, pathlib
gs_raw = {...}   # evaluate_script 返回的对象
pathlib.Path(r"C:\Users\86159\.Codex\skills\start-my-day\gs_results.json").write_text(
    json.dumps(gs_raw, ensure_ascii=False, indent=2), encoding="utf-8")
```

#### 4b. CNKI 搜索 → 保存 JSON

> **中文关键词来源**（优先级从高到低）：
> 1. `research_interests.yaml` 中各 domain 下的 `keywords_cn` 字段（如有）
> 2. 没有 `keywords_cn` 时，将英文关键词直译为中文（如 "fuzzing" → "模糊测试"，"embodied AI" → "具身智能"）
> 3. 禁止自由发挥、扩展或替换关键词，翻译后的词必须与英文关键词一一对应

```
1. 按上述规则确定中文关键词列表，打印出来供确认
2. 调用 cnki-search skill（中文关键词）
3. 调用 cnki-parse-results 解析结果列表
4. 保存到 $SKILL_DIR/cnki_results.json
```

```python
cnki_results = [...]  # cnki-parse-results 返回的列表
pathlib.Path(r"C:\Users\86159\.Codex\skills\start-my-day\cnki_results.json").write_text(
    json.dumps(cnki_results, ensure_ascii=False, indent=2), encoding="utf-8")
```

#### 4c. Chrome 未连接时的降级

若 `mcp__chrome-devtools__*` 工具不可用，跳过 GS/CNKI，仅以 `--sources arxiv,s2` 运行；在笔记 frontmatter 中标注 `sources: ["arxiv", "s2"]`。

#### 4d. 统一合并

> 所有参数**必须**从 `academic_agent.yaml` 读取，不得硬编码。

```python
# 读取 weekly 配置（步骤 1 已加载 cfg）
weekly_cfg  = cfg.get("weekly", {})
search_cfg  = cfg.get("search", {})

# 搜索源：weekly.sources 优先，缺失则回落到 search.default_sources
SOURCES     = weekly_cfg.get("sources") or search_cfg.get("default_sources", "arxiv,s2,gs,cnki")
# arXiv 分类：search.default_categories
CATEGORIES  = search_cfg.get("default_categories", "cs.CR,cs.SE,cs.RO,cs.AI")
# 推荐总数
TOP_N       = weekly_cfg.get("top_n", 10)
# 每源抓取数
PER_SOURCE  = weekly_cfg.get("per_source_top", 20)
```

```bash
# 变量均来自上方 Python 读取，不得替换为字面量
python "$SKILL_DIR/scripts/search_multi_source.py" \
  --sources      $SOURCES \
  --keywords     "$KEYWORDS_COMMA_SEPARATED" \
  --categories   "$CATEGORIES" \
  --days         $WINDOW_DAYS \
  --end-date     "$END_DATE" \
  --top          $TOP_N \
  --per-source-top $PER_SOURCE \
  --gs-input     "$SKILL_DIR/gs_results.json" \
  --cnki-input   "$SKILL_DIR/cnki_results.json" \
  --output       "$SKILL_DIR/merged.json"
```

### 步骤 5：Zotero 去重

> **前置检查（必做）**：运行去重前，先检查 BBT JSON 文件是否存在且是最新的：
>
> ```python
> import os, datetime
> bbt_dir = r"E:\obsidian_note\文献管理库\文献知识库\better-bibtex"
> files = [f for f in os.listdir(bbt_dir) if f.endswith(".json")]
> if not files:
>     print("⚠️ BBT JSON 不存在，请在 Zotero 中导出：文件 → 导出文献库 → Better BibTeX JSON → 保存到 better-bibtex/")
> else:
>     mtime = max(os.path.getmtime(os.path.join(bbt_dir, f)) for f in files)
>     age_h = (datetime.datetime.now().timestamp() - mtime) / 3600
>     if age_h > 24:
>         print(f"⚠️ BBT JSON 已 {age_h:.0f} 小时未更新，建议重新导出以确保去重准确")
> ```
>
> 如果 BBT JSON 过期，告知用户：「请在 Zotero 中重新导出 Better BibTeX JSON 到 `better-bibtex/` 目录，然后我继续运行。」

```bash
python "$SKILL_DIR/../zotero-check/scripts/check_zotero.py" \
  --bbt-json "$BBT_JSON_PATH" \
  --input  "$SKILL_DIR/merged.json" \
  --output "$SKILL_DIR/merged_dedupped.json"
```

BBT JSON 路径取自 `academic_agent.yaml → zotero.bbt_json_path`；缺失时跳过，邮件标注「未去重」。

> **去重有效性说明**：
> - arXiv 论文：通过 arxiv_id 精确匹配，最可靠
> - GS/S2 论文（无 arXiv ID）：通过 DOI 匹配（脚本会从 URL 中自动提取 ACM/DOI 链接中的 DOI）
> - 无 DOI 的论文：通过标题模糊匹配（threshold=0.85）
> - 若 BBT JSON 未包含全部 Zotero 条目，去重效果会受限

### 步骤 6：生成 Markdown 周报

写入 `$VAULT/10_Weekly/{label}论文推荐.md`，格式：

```markdown
---
week: "{YYYY-Www}"
search_window: "{start} ~ {end}"
keywords: [...]
sources: [arxiv, s2, gs, cnki]
total_raw: N
total_merged: M
total_skipped_in_zotero: K
tags: ["llm-generated", "weekly-paper-recommend"]
---

# {YYYY-Www} 论文周报

## 本周概览
...

## 推荐论文

### 1. {title}
- **作者**：...
- **来源**：{venue}（{year}）
- **发布日期**：{published_date}
- **引用**：{citation_count}（influential: {influential_citation_count}）
- **链接**：[PDF]({pdf_url}) · [原文]({url})
- **综合评分**：{overall} ｜ 相关性 {relevance} · 新近性 {recency} · 热度 {popularity} · 质量 {quality}

**摘要**：{abstract 前 400 字}
```

### 步骤 7：关键词链接

```bash
python "$SKILL_DIR/scripts/link_keywords.py" \
  --index "$SKILL_DIR/existing_notes_index.json" \
  --input  "$VAULT/10_Weekly/{label}论文推荐.md" \
  --output "$VAULT/10_Weekly/{label}论文推荐.md"
```

### 步骤 8：精读前 N 篇（严格按配置和合并结果执行）

> **⚠️ 重要**：精读的论文列表**必须**来自 `merged_dedupped.json`，不得从生成的 Markdown 周报中自行推断。
> 精读数量**必须**读取 `academic_agent.yaml → weekly.top_n_detailed`，不得硬编码。

#### 8a. 读取精读参数

```python
import json, yaml
from pathlib import Path

# 1. 读取精读数量
cfg_path = Path(r"E:\obsidian_note\文献管理库\文献知识库\99_System\Config\academic_agent.yaml")
with cfg_path.open("r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)
TOP_N_DETAILED = cfg.get("weekly", {}).get("top_n_detailed", 1)  # 默认 1

# 2. 从 merged_dedupped.json 读取已排序的论文列表
# （由步骤 5 Zotero 去重后生成，filtered 列表按 scores.overall 降序）
dedup_path = Path(r"C:\Users\86159\.Codex\skills\start-my-day\merged_dedupped.json")
with dedup_path.open("r", encoding="utf-8") as f:
    dedup = json.load(f)

# filtered 已经是去重后保留的论文（按 overall score 降序）
candidates = dedup.get("filtered", [])

# 3. 按 overall score 降序排，取前 TOP_N_DETAILED 篇用于精读
#    优先取有 arxiv_id 的；若 top 论文无 arxiv_id，退而用 DOI / URL 精读
candidates_sorted = sorted(
    candidates,
    key=lambda p: p.get("scores", {}).get("overall", 0),
    reverse=True,
)

to_analyze = []
for p in candidates_sorted:
    if len(to_analyze) >= TOP_N_DETAILED:
        break
    if p.get("arxiv_id") or p.get("doi") or p.get("url"):
        to_analyze.append(p)

print(f"top_n_detailed={TOP_N_DETAILED}，找到 {len(to_analyze)} 篇论文待精读：")
for i, p in enumerate(to_analyze, 1):
    ident = p.get("arxiv_id") or p.get("doi") or p.get("url", "无ID")
    print(f"  {i}. [{ident}] {p['title'][:60]}")
```

#### 8b. 逐篇精读

对 `to_analyze` 列表中的每篇论文：

1. **检查已有笔记**：在 `$VAULT/20_Research/Papers/` 下按 arxiv_id 或标题搜索
   - **已有** → 在周报精读表中填入 wikilink，跳过分析
   - **没有** → 执行下面的精读流程

2. **精读流程**（按 ID 类型选对应命令）：
   ```
   # 有 arxiv_id（优先）
   /extract-paper-images {arxiv_id}
   /paper-analyze {arxiv_id}

   # 只有 DOI（无 arxiv_id）
   /paper-analyze {doi}

   # 只有 URL（无 arxiv_id / doi）
   /paper-analyze {url}
   ```

3. **精读完成后**，在周报 Markdown 中更新 `## 精读笔记` 表格：
   ```markdown
   ## 精读笔记（Top {TOP_N_DETAILED}）

   | 论文 | 笔记链接 | 评分 |
   |------|---------|------|
   | {title_short} | [[{note_filename}|笔记]] | {quality_score}/10 |
   ```
   > 表格中的论文必须与 `to_analyze` 列表一一对应，不得添加不在该列表中的论文。

#### 8c. 若所有候选均无任何可用 ID

当 `to_analyze` 为空时（无 arxiv_id / doi / url 均缺失），在周报中写：

```markdown
## 精读笔记

> 本期推荐论文元数据不完整，无法自动精读。Top 3 可手动精读：

| 排名 | 论文 | 手动精读命令 |
|------|------|------------|
| 1 | {title_1} | `/paper-analyze "{title_1}"` |
| 2 | {title_2} | `/paper-analyze "{title_2}"` |
| 3 | {title_3} | `/paper-analyze "{title_3}"` |
```

### 步骤 9：发送邮件

发送条件（两者满足其一才发）：
- `academic_agent.yaml → weekly.send_email: true`，且未传 `--no-email` 参数
- 或传了 `--email` 参数强制发送（覆盖配置）

```python
# 读取发送意图（步骤 1 已加载 cfg）
SEND_EMAIL_CFG = cfg.get("weekly", {}).get("send_email", True)
# --no-email 参数优先级最高，可临时覆盖配置
should_send = SEND_EMAIL_CFG and not NO_EMAIL
```

```bash
# 仅当 should_send == True 时执行
python "$SKILL_DIR/../send-email/scripts/send_email.py" \
  --config  "$VAULT/99_System/Config/academic_agent.yaml" \
  --subject "[周报 {label}] 论文推荐 Top $TOP_N" \
  --md-file "$VAULT/10_Weekly/{label}论文推荐.md"
```

若 `should_send == False`，在笔记末尾追加：
```
> 📧 邮件未发送（weekly.send_email=false 或传入了 --no-email）
```

---

## 错误处理

| 场景 | 行为 |
|------|------|
| arXiv API 超时 | 重试 3 次后跳过，笔记标注「arXiv 未运行」 |
| S2 429 | 等 30 秒重试，最多 3 次 |
| GS captcha | 截图提示用户验证 → 等待确认 → 最多重试 3 次（间隔 15/15/30 秒）→ 3 次全败才跳过 |
| CNKI 滑块 | 同上 |
| Chrome 未连接 | 降级到 arxiv + s2，笔记标注 |
| BBT JSON 缺失 | 跳过去重，邮件正文标注「未去重」 |
| SMTP 失败 | 笔记仍写本地，仅警告邮件失败 |

---

## 与其他 skill 的区别

| skill | 用途 |
|-------|------|
| start-my-day | **每周**手动推荐，多源，本地笔记 + 邮件 |
| conf-papers | **顶级会议**论文按年份推荐 |
| paper-analyze | 用户指定单篇论文的深度分析 |
| paper-search | 在已有 obsidian 笔记中搜索 |

> **自动化周推荐**（每周一 8:00 无人值守）：使用独立的 GitHub Actions 仓库 `weekly-papers-bot`，
> 运行 `scripts/weekly_papers.py`，仅 arXiv + S2，只发邮件，与本 skill 无关。

---

## 临时文件

`$SKILL_DIR/{merged,merged_dedupped,gs_results,cnki_results,existing_notes_index}.json` 均为临时文件，跑完可清理。

## 复用脚本

- `scripts/search_multi_source.py` — 多源合并评分器
- `scripts/scan_existing_notes.py` — 已有笔记索引
- `scripts/link_keywords.py` — 关键词链接为 wikilink
- `scripts/common_words.py` — 通用词过滤
