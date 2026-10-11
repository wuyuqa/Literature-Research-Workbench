#!/usr/bin/env python3
"""生成 2026-W22 周报 Markdown"""
import json
from pathlib import Path
from datetime import datetime

VAULT = r"E:\obsidian_note\文献管理库\文献知识库"
SKILL_DIR = r"C:\Users\86159\.claude\skills\start-my-day"

with open(f"{SKILL_DIR}/merged_dedupped.json", encoding="utf-8") as f:
    data = json.load(f)

papers = data["filtered"]
week_label = data.get("week", "2026-W22")
search_window = data.get("search_window", "2026-04-27 ~ 2026-05-27")
sources_used = data.get("sources_used", ["gs"])
note_api = data.get("note", "")

# 按综合评分排序（已排好）
papers_sorted = sorted(papers, key=lambda p: p["scores"]["overall"], reverse=True)

# 构建周报
lines = []
lines.append("---")
lines.append(f'week: "{week_label}"')
lines.append(f'search_window: "{search_window}"')
lines.append(f"keywords:")
for kw in ["DDS", "fuzzing", "protocol security", "embodied AI security", "ROS2", "VLA", "robot security"]:
    lines.append(f"  - {kw}")
lines.append(f"sources: {json.dumps(sources_used, ensure_ascii=False)}")
lines.append(f"total_raw: {data.get('total_raw', len(papers_sorted))}")
lines.append(f"total_merged: {data.get('total_merged', len(papers_sorted))}")
lines.append(f"total_skipped_in_zotero: 0")
lines.append('tags: ["llm-generated", "weekly-paper-recommend"]')
lines.append("---")
lines.append("")
lines.append(f"# {week_label} 论文周报")
lines.append("")
lines.append("## 本周概览")
lines.append("")
lines.append(f"- **搜索窗口**：{search_window}")
lines.append(f"- **搜索来源**：Google Scholar (arXiv 和 Semantic Scholar API 因限流暂不可用)")
if note_api:
    lines.append(f"- **备注**：{note_api}")
lines.append(f"- **搜索方向**：DDS协议安全与模糊测试 / 模糊测试技术 / 具身智能系统安全 / 具身智能前沿")
lines.append(f"- **原始结果数**：{data.get('total_raw', 16)} 篇")
lines.append(f"- **去重后**：{data.get('total_merged', 16)} 篇（Zotero 中未发现重复条目）")
lines.append(f"- **精选推荐**：{len(papers_sorted)} 篇")
lines.append("")
lines.append("**本周亮点**：")
lines.append("1. 具身智能安全进入爆发期，多篇论文聚焦 VLA 模型安全和机器人攻击面")
lines.append("2. 协议模糊测试与 LLM 的结合成为新方向（LIPFuzzer、APFuzz）")
lines.append("3. ROS2/DDS 中间件安全有新突破（ROS2 反序列化类型混淆漏洞检测）")
lines.append("4. 工业控制系统协议模糊测试引入扩散模型（SD-Fuzz）")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 推荐论文")
lines.append("")

for i, p in enumerate(papers_sorted, 1):
    title = p["title"]
    authors = p["authors"]
    authors_str = ", ".join(authors[:4])
    if len(authors) > 4:
        authors_str += " et al."
    venue = p.get("venue", "--")
    year = p.get("year", "--")
    pub_date = p.get("published_date", "--")
    cit = p.get("citation_count", 0)
    arxiv_id = p.get("arxiv_id", "")
    url = p.get("url", "")
    pdf_url = p.get("pdf_url", "")
    domain = p.get("matched_domain", "--")
    scores = p["scores"]
    abstract = p.get("abstract", "")[:400]

    lines.append(f"### {i}. {title}")
    lines.append("")
    lines.append(f"- **作者**：{authors_str}")
    lines.append(f"- **来源**：{venue}")
    lines.append(f"- **发布日期**：{pub_date}")
    lines.append(f"- **引用**：{cit}")
    lines.append(f"- **研究方向**：{domain}")
    lines.append(f"- **Zotero**：未收录")

    # 链接
    link_parts = []
    if arxiv_id:
        link_parts.append(f"[arXiv](https://arxiv.org/abs/{arxiv_id})")
        link_parts.append(f"[PDF](https://arxiv.org/pdf/{arxiv_id})")
    elif url:
        link_parts.append(f"[论文链接]({url})")
    if pdf_url and pdf_url != url and not arxiv_id:
        link_parts.append(f"[PDF]({pdf_url})")
    lines.append(f"- **链接**：{' | '.join(link_parts) if link_parts else '--'}")

    # 评分
    overall = scores.get("overall", "--")
    rel = scores.get("relevance", "--")
    rec = scores.get("recency", "--")
    pop = scores.get("popularity", "--")
    qual = scores.get("quality", "--")
    lines.append(f"- **综合评分**：{overall}（相关 {rel} · 新近 {rec} · 热门 {pop} · 质量 {qual}）")
    lines.append("")
    lines.append(f"**摘要**：{abstract}")
    lines.append("")
    lines.append("---")
    lines.append("")

# 精读笔记占位
lines.append("## 精读笔记（Top 1）")
lines.append("")
lines.append("| 论文 | 笔记链接 | 评分 |")
lines.append("|------|---------|------|")
top1 = papers_sorted[0]
lines.append(f"| {top1['title'][:50]}... | 待生成 | -- |")
lines.append("")
lines.append("> arXiv ID: 2405.14093 — 将通过 paper-analyze skill 精读")
lines.append("")

report = "\n".join(lines)

# 写入 vault
out_dir = Path(VAULT) / "10_Weekly"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / f"{week_label}论文推荐.md"
out_path.write_text(report, encoding="utf-8")
print(f"Weekly report saved to: {out_path}")
print(f"Total papers: {len(papers_sorted)}")
