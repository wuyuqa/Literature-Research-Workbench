#!/usr/bin/env python3
"""
Semantic Scholar API 搜索（独立 cli）

用法：
    python s2_search.py --keywords "DDS fuzzing" --start-date 2026-05-19 --end-date 2026-05-26 --top 20 --output s2.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

S2_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = (
    "title,abstract,year,publicationDate,citationCount,influentialCitationCount,"
    "venue,authors,externalIds,openAccessPdf,url"
)


def call_s2_api(params: dict, max_retries: int = 3) -> dict | None:
    """调用 S2 API，处理 429 限流。"""
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or os.environ.get("S2_API_KEY")
    headers = {"User-Agent": "academic-agent/1.0"}
    if api_key:
        headers["x-api-key"] = api_key

    query_string = urllib.parse.urlencode(params)
    url = f"{S2_API_URL}?{query_string}"

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 10 * (attempt + 1)
                logger.warning("S2 429 rate limit; wait %ds (attempt %d)", wait, attempt + 1)
                time.sleep(wait)
                continue
            logger.error("S2 HTTP %d: %s", e.code, e.reason)
            return None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            wait = (2 ** attempt) * 2
            logger.warning("S2 attempt %d failed: %s — wait %ds", attempt + 1, e, wait)
            if attempt < max_retries - 1:
                time.sleep(wait)
    logger.error("S2 failed after %d attempts", max_retries)
    return None


def normalize_paper(p: dict) -> dict:
    """把 S2 返回的 paper 字段标准化为我们统一的 schema。"""
    if not p.get("title"):
        return {}
    external = p.get("externalIds") or {}
    arxiv_id = ""
    raw_arxiv = external.get("ArXiv", "") if isinstance(external, dict) else ""
    if raw_arxiv:
        m = re.search(r"(\d{4}\.\d{4,5})", str(raw_arxiv))
        if m:
            arxiv_id = m.group(1)

    doi = (external.get("DOI", "") or "") if isinstance(external, dict) else ""

    authors_raw = p.get("authors") or []
    authors = [a.get("name", "") for a in authors_raw if isinstance(a, dict)]

    oa_pdf = ""
    oa = p.get("openAccessPdf") or {}
    if isinstance(oa, dict):
        oa_pdf = oa.get("url", "") or ""

    return {
        "source": "s2",
        "paper_id": p.get("paperId", ""),
        "title": p.get("title", "").strip(),
        "authors": authors,
        "abstract": (p.get("abstract") or "").strip(),
        "year": p.get("year"),
        "publication_date": p.get("publicationDate", ""),
        "venue": p.get("venue", "") or "",
        "citation_count": p.get("citationCount") or 0,
        "influential_citation_count": p.get("influentialCitationCount") or 0,
        "arxiv_id": arxiv_id,
        "doi": doi,
        "url": p.get("url", "") or "",
        "open_access_pdf": oa_pdf,
    }


def search_s2(
    keywords: str,
    date_range: str | None,
    year: str | None,
    top_n: int,
    raw_limit: int = 100,
) -> tuple[list[dict], int]:
    """主搜索函数：返回 (top_papers, total_found)。"""
    params = {
        "query": keywords,
        "limit": min(raw_limit, 100),
        "fields": S2_FIELDS,
    }
    if date_range:
        params["publicationDateOrYear"] = date_range
    elif year:
        params["year"] = year

    data = call_s2_api(params)
    if not data:
        return [], 0

    raw_papers = data.get("data", []) or []
    papers = []
    for p in raw_papers:
        normalized = normalize_paper(p)
        if normalized:
            papers.append(normalized)

    papers.sort(
        key=lambda x: (
            x["influential_citation_count"],
            x["citation_count"],
            x["publication_date"] or "",
        ),
        reverse=True,
    )
    return papers[:top_n], data.get("total", len(raw_papers))


def main():
    parser = argparse.ArgumentParser(description="Semantic Scholar search CLI")
    parser.add_argument("--keywords", required=True, help="Query string")
    parser.add_argument("--year", default="", help="Year or year range (e.g. 2025 or 2024-2026)")
    parser.add_argument("--start-date", default="", help="YYYY-MM-DD (with --end-date)")
    parser.add_argument("--end-date", default="", help="YYYY-MM-DD")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--raw-limit", type=int, default=100, help="Max raw results from S2")
    parser.add_argument("--output", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    date_range = None
    if args.start_date and args.end_date:
        date_range = f"{args.start_date}:{args.end_date}"
    elif args.start_date:
        date_range = f"{args.start_date}:"
    elif args.end_date:
        date_range = f":{args.end_date}"

    year = args.year or None

    top_papers, total_found = search_s2(
        keywords=args.keywords,
        date_range=date_range,
        year=year,
        top_n=args.top,
        raw_limit=args.raw_limit,
    )

    result = {
        "source": "s2",
        "query": {
            "keywords": args.keywords,
            "date_range": date_range,
            "year": year,
        },
        "total_found": total_found,
        "papers": top_papers,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"S2 search done: {total_found} found, top {len(top_papers)} saved to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
