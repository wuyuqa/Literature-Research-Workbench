#!/usr/bin/env python3
"""
arXiv API 搜索（独立 cli）

用法：
    python arxiv_search.py --keywords "DDS fuzzing" --days 7 --top 20 --output arxiv.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

ARXIV_API_URL = "http://export.arxiv.org/api/query"


def parse_arxiv_xml(xml_content: str) -> list[dict]:
    """解析 arXiv API 返回的 Atom XML。"""
    papers = []
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.error("XML parse error: %s", e)
        return []

    for entry in root.findall("atom:entry", ARXIV_NS):
        try:
            entry_id = entry.find("atom:id", ARXIV_NS)
            if entry_id is None or not entry_id.text:
                continue
            arxiv_url = entry_id.text.strip()
            m = re.search(r"abs/([\d.]+(?:v\d+)?)", arxiv_url)
            if not m:
                continue
            arxiv_id = m.group(1).split("v")[0]

            title_el = entry.find("atom:title", ARXIV_NS)
            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            title = re.sub(r"\s+", " ", title)

            summary_el = entry.find("atom:summary", ARXIV_NS)
            abstract = summary_el.text.strip() if summary_el is not None and summary_el.text else ""
            abstract = re.sub(r"\s+", " ", abstract)

            authors = []
            for author in entry.findall("atom:author", ARXIV_NS):
                name_el = author.find("atom:name", ARXIV_NS)
                if name_el is not None and name_el.text:
                    authors.append(name_el.text.strip())

            published_el = entry.find("atom:published", ARXIV_NS)
            published_date = ""
            if published_el is not None and published_el.text:
                published_date = published_el.text.strip()[:10]

            categories = []
            for cat in entry.findall("atom:category", ARXIV_NS):
                term = cat.get("term", "")
                if term and term not in categories:
                    categories.append(term)

            primary_cat = entry.find("arxiv:primary_category", ARXIV_NS)
            primary = primary_cat.get("term", "") if primary_cat is not None else (
                categories[0] if categories else ""
            )

            pdf_url = ""
            for link in entry.findall("atom:link", ARXIV_NS):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href", "")
                    break
            if not pdf_url:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

            papers.append({
                "source": "arxiv",
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "published_date": published_date,
                "categories": categories,
                "primary_category": primary,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "pdf_url": pdf_url,
            })
        except (AttributeError, KeyError, ValueError) as e:
            logger.debug("Entry parse failed: %s", e)
            continue

    return papers


def build_query(keywords: list[str], categories: list[str], start: datetime, end: datetime) -> str:
    """构建 arXiv 检索 query。"""
    parts = []

    if categories:
        cat_query = "+OR+".join(f"cat:{c}" for c in categories)
        parts.append(f"({cat_query})")

    if keywords:
        kw_parts = []
        for kw in keywords:
            kw = kw.strip()
            if not kw:
                continue
            if " " in kw:
                kw_parts.append(f'ti:"{kw}"+OR+abs:"{kw}"')
            else:
                kw_parts.append(f"ti:{kw}+OR+abs:{kw}")
        if kw_parts:
            kw_query = "+OR+".join(f"({p})" for p in kw_parts)
            parts.append(f"({kw_query})")

    date_query = (
        f"submittedDate:[{start.strftime('%Y%m%d')}0000+TO+{end.strftime('%Y%m%d')}2359]"
    )
    parts.append(date_query)

    return "+AND+".join(parts)


def search_arxiv(
    keywords: list[str],
    categories: list[str],
    start: datetime,
    end: datetime,
    max_results: int = 200,
    max_retries: int = 3,
    pre_delay: float = 3.0,
) -> list[dict]:
    """搜索 arXiv 论文（含重试 + 退避）。

    pre_delay: 每次请求前强制等待秒数（arXiv 要求 ≥ 3s 间隔，防限流）。
    429/503 时退避 30/60/90s；其他网络错误用 2/4/8s。
    """
    query = build_query(keywords, categories, start, end)
    url = (
        f"{ARXIV_API_URL}?"
        f"search_query={query}&"
        f"max_results={max_results}&"
        f"sortBy=submittedDate&"
        f"sortOrder=descending"
    )
    logger.info("arXiv query: %s", url[:200])

    for attempt in range(max_retries):
        if pre_delay > 0:
            logger.debug("arXiv pre-request delay %.1fs", pre_delay)
            time.sleep(pre_delay)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "academic-agent/1.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                xml_content = resp.read().decode("utf-8")
            return parse_arxiv_xml(xml_content)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                wait = 30 * (attempt + 1)  # 30 / 60 / 90s
                logger.warning("arXiv %d attempt %d — wait %ds", e.code, attempt + 1, wait)
            else:
                wait = (2 ** attempt) * 2
                logger.warning("arXiv HTTP %d attempt %d — wait %ds", e.code, attempt + 1, wait)
            if attempt < max_retries - 1:
                time.sleep(wait)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            wait = (2 ** attempt) * 2
            logger.warning("arXiv attempt %d failed: %s — wait %ds", attempt + 1, e, wait)
            if attempt < max_retries - 1:
                time.sleep(wait)
    logger.error("arXiv failed after %d attempts", max_retries)
    return []


def filter_excluded(papers: list[dict], excluded_keywords: list[str]) -> list[dict]:
    """过滤含排除关键词的论文。"""
    if not excluded_keywords:
        return papers
    excl_lower = [k.lower() for k in excluded_keywords]
    out = []
    for p in papers:
        text = (p["title"] + " " + p["abstract"]).lower()
        if any(ek in text for ek in excl_lower):
            continue
        out.append(p)
    return out


def rank_by_relevance(papers: list[dict], keywords: list[str], top_n: int) -> list[dict]:
    """简单相关性排序：标题命中 +2，摘要命中 +1。"""
    if not keywords:
        return papers[:top_n]
    kw_lower = [k.lower() for k in keywords if k.strip()]
    for p in papers:
        score = 0.0
        title_l = p["title"].lower()
        abs_l = p["abstract"].lower()
        for kw in kw_lower:
            if kw in title_l:
                score += 2.0
            if kw in abs_l:
                score += 1.0
        p["_relevance"] = score
    papers.sort(key=lambda x: (-x["_relevance"], x["published_date"]), reverse=False)
    papers.sort(key=lambda x: x["_relevance"], reverse=True)
    return papers[:top_n]


def main():
    parser = argparse.ArgumentParser(description="arXiv search CLI")
    parser.add_argument("--keywords", default="", help="Comma- or space-separated keywords")
    parser.add_argument(
        "--categories",
        default="cs.CR,cs.SE,cs.RO,cs.AI",
        help="Comma-separated arXiv categories",
    )
    parser.add_argument("--days", type=int, default=30, help="Search past N days")
    parser.add_argument("--top", type=int, default=20, help="Top N to return")
    parser.add_argument("--max-results", type=int, default=200, help="Max raw results from arXiv")
    parser.add_argument("--excluded", default="workshop,survey,tutorial,review",
                        help="Comma-separated excluded keywords")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--end-date", default="", help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--pre-delay", type=float, default=3.0,
                        help="Seconds to wait before each arXiv request (default 3, per arXiv guidelines)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    keywords = [k.strip() for k in re.split(r"[,\s]+", args.keywords) if k.strip()]
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    excluded = [k.strip() for k in args.excluded.split(",") if k.strip()]

    end = datetime.now() if not args.end_date else datetime.strptime(args.end_date, "%Y-%m-%d")
    start = end - timedelta(days=args.days)

    papers = search_arxiv(keywords, categories, start, end, args.max_results, pre_delay=args.pre_delay)
    papers = filter_excluded(papers, excluded)
    top_papers = rank_by_relevance(papers, keywords, args.top)

    result = {
        "source": "arxiv",
        "query": {
            "keywords": keywords,
            "categories": categories,
            "days": args.days,
            "search_window": {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d"),
            },
        },
        "total_found": len(papers),
        "papers": top_papers,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"arXiv search done: {len(papers)} found, top {len(top_papers)} saved to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
