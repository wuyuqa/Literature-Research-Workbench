#!/usr/bin/env python3
"""
多源论文搜索 + 合并 + 综合评分

读取每个源（arxiv / s2 / gs / cnki）的搜索结果 JSON，去重合并后按统一评分维度
（相关性、新近性、热门度、质量）排序，输出 top N。

GS 和 CNKI 的搜索由 agent 在浏览器中触发后导出 JSON；本脚本只做"合并"。
arXiv 和 S2 由本脚本自动调用对应 cli 脚本完成。

用法（schedule 模式：仅 arxiv + s2）：
    python search_multi_source.py \
      --sources arxiv,s2 \
      --keywords "DDS fuzzing" \
      --categories "cs.CR,cs.SE,cs.RO" \
      --days 7 --top 10 \
      --output merged.json

用法（manual 模式：4 源齐全，GS/CNKI 由 agent 预先生成 json）：
    python search_multi_source.py \
      --sources arxiv,s2,gs,cnki \
      --keywords "DDS fuzzing" \
      --gs-input gs_results.json \
      --cnki-input cnki_results.json \
      --top 10 \
      --output merged.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCORING_WEIGHTS_DEFAULT = {
    "relevance": 0.35,
    "recency": 0.25,
    "popularity": 0.25,
    "quality": 0.15,
}

SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR.parent.parent  # ...\.claude\skills


def normalize_title(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_paper(p: dict) -> dict:
    """把不同源的 paper 字段统一为通用 schema。"""
    source = p.get("source", "unknown")
    out = {
        "source": source,
        "sources": [source],
        "title": (p.get("title") or "").strip(),
        "authors": p.get("authors") or [],
        "abstract": (p.get("abstract") or "").strip(),
        "arxiv_id": (p.get("arxiv_id") or "").strip(),
        "doi": (p.get("doi") or "").strip().lower(),
        "url": p.get("url") or "",
        "pdf_url": p.get("pdf_url") or p.get("open_access_pdf") or "",
        "published_date": p.get("published_date") or p.get("publication_date") or "",
        "year": p.get("year"),
        "venue": p.get("venue") or p.get("journal") or "",
        "citation_count": p.get("citation_count") or p.get("cited_by") or 0,
        "influential_citation_count": p.get("influential_citation_count") or 0,
        "categories": p.get("categories") or [],
        "_raw": p,
    }
    if not out["year"] and out["published_date"]:
        try:
            out["year"] = int(out["published_date"][:4])
        except (ValueError, TypeError):
            pass
    return out


def papers_match(a: dict, b: dict, title_threshold: float = 0.85) -> bool:
    """判断两篇论文是否同一篇。"""
    if a["arxiv_id"] and b["arxiv_id"] and a["arxiv_id"] == b["arxiv_id"]:
        return True
    if a["doi"] and b["doi"] and a["doi"] == b["doi"]:
        return True
    ta = normalize_title(a["title"])
    tb = normalize_title(b["title"])
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    return SequenceMatcher(None, ta, tb).ratio() >= title_threshold


def merge_papers(all_papers: list[dict], title_threshold: float = 0.85) -> list[dict]:
    """合并重复论文，保留最优字段。"""
    merged: list[dict] = []
    for p in all_papers:
        np = normalize_paper(p)
        if not np["title"]:
            continue
        found_match = False
        for existing in merged:
            if papers_match(existing, np, title_threshold):
                if np["source"] not in existing["sources"]:
                    existing["sources"].append(np["source"])
                if not existing["arxiv_id"] and np["arxiv_id"]:
                    existing["arxiv_id"] = np["arxiv_id"]
                if not existing["doi"] and np["doi"]:
                    existing["doi"] = np["doi"]
                if not existing["abstract"] and np["abstract"]:
                    existing["abstract"] = np["abstract"]
                if np["citation_count"] > existing["citation_count"]:
                    existing["citation_count"] = np["citation_count"]
                if np["influential_citation_count"] > existing["influential_citation_count"]:
                    existing["influential_citation_count"] = np["influential_citation_count"]
                if not existing["pdf_url"] and np["pdf_url"]:
                    existing["pdf_url"] = np["pdf_url"]
                if not existing["venue"] and np["venue"]:
                    existing["venue"] = np["venue"]
                found_match = True
                break
        if not found_match:
            merged.append(np)
    return merged


def filter_by_date_window(
    papers: list[dict],
    start_date: datetime,
    end_date: datetime,
    year_only_policy: str = "lenient",
) -> tuple[list[dict], list[dict]]:
    """过滤超出搜索窗口的论文。

    规则：
    - 精确日期（YYYY-MM-DD 且非 01-01）：严格过滤，要求 start_date <= date <= end_date
    - 年份估算日期（YYYY-01-01，来自 GS 等只有年份信息的源）：
        - year_only_policy="lenient"（默认）：只剔除 year < start_date.year 的论文
        - year_only_policy="strict"：要求 start_date.year <= year <= end_date.year
    - 无日期：保留

    year_only_policy 由 academic_agent.yaml → search.date_filter.year_only_policy 控制。

    返回 (kept, filtered_out)
    """
    kept: list[dict] = []
    removed: list[dict] = []

    for paper in papers:
        pub_str = (paper.get("published_date") or "").strip()
        if not pub_str:
            kept.append(paper)
            continue

        try:
            pub_date = datetime.strptime(pub_str[:10], "%Y-%m-%d")
        except ValueError:
            kept.append(paper)
            continue

        pub_year = pub_date.year
        # 判断是否为"年份估算"（month=day=1，来自 GS 等源）
        is_year_only = (pub_date.month == 1 and pub_date.day == 1) or \
                       paper.get("_date_is_year_only", False)

        if is_year_only:
            # 年份估算论文过滤策略（由 year_only_policy 参数控制）：
            #   "lenient"  — 只剔除 year < start_date.year（宽松，防误杀近期论文）
            #   "strict"   — 要求 start_date.year <= year <= end_date.year
            #
            # 注意：GS 只有年份精度，无法精确过滤月份；
            # 过滤后的新近性仍由 score_recency 评分函数进一步惩罚。
            in_window: bool
            if year_only_policy == "strict":
                in_window = start_date.year <= pub_year <= end_date.year
            else:  # lenient
                in_window = pub_year >= start_date.year and pub_year <= end_date.year

            if not in_window:
                logger.debug(
                    "Date-filter (year-only, policy=%s) removed: %s (year=%d, window=[%d,%d])",
                    year_only_policy, paper.get("title", "")[:50],
                    pub_year, start_date.year, end_date.year,
                )
                removed.append(paper)
            else:
                kept.append(paper)
        else:
            # 精确日期：严格过滤
            if pub_date < start_date or pub_date > end_date:
                logger.debug(
                    "Date-filter (precise) removed: %s (%s not in [%s, %s])",
                    paper.get("title", "")[:50], pub_str,
                    start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
                )
                removed.append(paper)
            else:
                kept.append(paper)

    return kept, removed


def score_relevance(paper: dict, keywords: list[str]) -> float:
    """0-3 分。标题命中关键词 +0.5 each；摘要命中 +0.3 each；多源加成 +0.3。"""
    score = 0.0
    kws = [k.lower() for k in keywords if k.strip()]
    title_l = paper["title"].lower()
    abs_l = paper["abstract"].lower()
    for kw in kws:
        if kw in title_l:
            score += 0.5
        if kw in abs_l:
            score += 0.3
    if len(paper["sources"]) > 1:
        score += 0.3 * (len(paper["sources"]) - 1)
    return min(score, 3.0)


_DEFAULT_RECENCY_TIERS = [
    {"days": 7,  "score": 3.0},
    {"days": 14, "score": 2.0},
    {"days": 30, "score": 1.0},
    {"days": 90, "score": 0.5},
]


def score_recency(
    paper: dict,
    reference_date: datetime,
    tiers: list | None = None,
    year_only_score: float = 1.0,
) -> float:
    """0-3 分。

    精确日期论文：按 tiers 阶梯打分（由 academic_agent.yaml scoring.recency_tiers 配置）。
    year-only 论文（GS/CNKI 等只有年份精度，_date_is_year_only=True）：
        - 当年 → year_only_score（固定保守分，默认 1.0）
        - 跨年 → 0.0
    无日期 → 0.0
    """
    pub_str = (paper.get("published_date") or "").strip()
    if not pub_str:
        return 0.0

    try:
        pub_date = datetime.strptime(pub_str[:10], "%Y-%m-%d")
    except ValueError:
        return 0.0

    # year-only 论文（GS 等精度只到年份）
    is_year_only = paper.get("_date_is_year_only", False)
    if is_year_only:
        year_diff = reference_date.year - pub_date.year
        return year_only_score if year_diff == 0 else 0.0

    # 精确日期：按阶梯打分
    days = (reference_date - pub_date).days
    if days < 0:
        return 3.0
    used_tiers = tiers if tiers is not None else _DEFAULT_RECENCY_TIERS
    for tier in sorted(used_tiers, key=lambda t: t["days"]):
        if days <= tier["days"]:
            return float(tier["score"])
    return 0.0


def score_popularity(paper: dict) -> float:
    """0-3 分。influential 优先；普通 citation 次之。"""
    inf = paper.get("influential_citation_count") or 0
    cit = paper.get("citation_count") or 0
    if inf >= 50:
        return 3.0
    if inf >= 10:
        return 2.5
    if inf >= 3:
        return 2.0
    if inf >= 1:
        return 1.5
    if cit >= 100:
        return 2.0
    if cit >= 30:
        return 1.5
    if cit >= 10:
        return 1.0
    if cit >= 1:
        return 0.5
    return 0.0


QUALITY_STRONG_WORDS = {
    "novel", "state-of-the-art", "sota", "breakthrough", "first", "significantly",
    "outperform", "surpass", "new framework", "新颖", "突破", "首次",
}
QUALITY_METHOD_WORDS = {
    "framework", "architecture", "algorithm", "method", "approach", "system",
    "benchmark", "dataset", "方法", "框架", "算法",
}


# 顶级会议/期刊清单（CCF-A 为主，覆盖安全/软工/系统/网络/PL/ML/机器人/NLP/数据库）
TOP_VENUES_A = {
    # 安全（CCF-A）
    "usenix security", "ccs", "ndss", "ieee s&p", "s&p", "oakland",
    # 安全顶刊
    "ieee tifs", "ieee transactions on information forensics and security",
    "ieee tdsc", "ieee transactions on dependable and secure computing",
    "journal of cryptology",
    # 软件工程（CCF-A）
    "icse", "fse", "esec/fse", "ase", "issta",
    "tosem", "acm transactions on software engineering",
    "tse", "ieee transactions on software engineering",
    # 系统（CCF-A）
    "sosp", "osdi", "eurosys", "asplos", "fast", "usenix atc",
    # 网络（CCF-A）
    "sigcomm", "infocom", "nsdi", "mobicom",
    # PL（CCF-A）
    "pldi", "popl", "oopsla",
    # ML/AI（CCF-A）
    "neurips", "icml", "iclr", "aaai", "ijcai",
    "cvpr", "iccv", "eccv",
    # 机器人（顶会/顶刊）
    "icra", "iros", "rss", "ieee t-ro", "ieee transactions on robotics", "ijrr",
    # NLP（CCF-A/B 顶会）
    "acl", "emnlp", "naacl",
    # 数据库（CCF-A）
    "sigmod", "vldb", "icde",
    # 顶级综合期刊
    "nature", "science", "nature machine intelligence",
    "communications of the acm", "ieee tpami",
}

# CCF-B 级会议（少量加分，0.5）
TOP_VENUES_B = {
    "raid", "esorics", "dsn", "acsac",                       # 安全 B
    "icst", "icsme", "msr",                                  # 软工 B
    "icnp", "ifip networking",                               # 网络 B
    "ecai", "uai",                                           # AI B
    "iet information security",
}


def _venue_match(venue_l: str, venue_set: set) -> bool:
    """检查 venue 字符串是否命中清单（处理缩写和全名）。"""
    return any(v in venue_l for v in venue_set)


def score_quality(paper: dict) -> float:
    """0-3 分。从摘要语义粗略推断创新性 + venue 加分。"""
    score = 0.0
    abs_l = paper["abstract"].lower()
    strong_hits = sum(1 for w in QUALITY_STRONG_WORDS if w in abs_l)
    method_hits = sum(1 for w in QUALITY_METHOD_WORDS if w in abs_l)
    score += min(strong_hits * 0.5, 1.5)
    score += min(method_hits * 0.2, 0.5)

    venue_l = (paper["venue"] or "").lower()
    if _venue_match(venue_l, TOP_VENUES_A):
        score += 1.0
    elif _venue_match(venue_l, TOP_VENUES_B):
        score += 0.5

    return min(score, 3.0)


def compute_overall_score(
    paper: dict,
    keywords: list[str],
    ref_date: datetime,
    weights: dict,
    recency_tiers: list | None = None,
    year_only_score: float = 1.0,
) -> dict:
    rel = score_relevance(paper, keywords)
    rec = score_recency(paper, ref_date, tiers=recency_tiers, year_only_score=year_only_score)
    pop = score_popularity(paper)
    qua = score_quality(paper)
    overall = (
        weights["relevance"] * rel
        + weights["recency"] * rec
        + weights["popularity"] * pop
        + weights["quality"] * qua
    )
    paper["scores"] = {
        "relevance": round(rel, 3),
        "recency": round(rec, 3),
        "popularity": round(pop, 3),
        "quality": round(qua, 3),
        "overall": round(overall, 3),
    }
    return paper


def run_arxiv_source(keywords: str, categories: str, days: int, top: int) -> dict:
    out = Path(tempfile.gettempdir()) / f"arxiv_tmp_{datetime.now().timestamp():.0f}.json"
    cmd = [
        sys.executable,
        str(SKILLS_DIR / "arxiv-search" / "scripts" / "arxiv_search.py"),
        "--keywords", keywords,
        "--categories", categories,
        "--days", str(days),
        "--top", str(top),
        "--output", str(out),
    ]
    logger.info("Running arxiv-search: %s", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, timeout=180)
        with out.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
        logger.error("arxiv-search subprocess failed: %s", e)
        return {"source": "arxiv", "papers": [], "total_found": 0, "error": str(e)}


def _load_s2_api_key() -> str:
    """从 research_interests.yaml 读取 S2 API key（容忍缺失）。"""
    try:
        import yaml  # type: ignore
        ri_path = Path(
            r"<vault_root>/99_System/Config/research_interests.yaml"
        )
        if not ri_path.exists():
            return os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
        with ri_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return str(cfg.get("semantic_scholar_api_key") or "").strip()
    except Exception:
        return os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")


def run_s2_source(keywords: str, start_date: str, end_date: str, top: int) -> dict:
    out = Path(tempfile.gettempdir()) / f"s2_tmp_{datetime.now().timestamp():.0f}.json"
    cmd = [
        sys.executable,
        str(SKILLS_DIR / "s2-search" / "scripts" / "s2_search.py"),
        "--keywords", keywords,
        "--start-date", start_date,
        "--end-date", end_date,
        "--top", str(top),
        "--output", str(out),
    ]
    env = os.environ.copy()
    api_key = _load_s2_api_key()
    if api_key:
        env["SEMANTIC_SCHOLAR_API_KEY"] = api_key
        logger.info("S2 API key loaded from research_interests.yaml")
    else:
        logger.warning("No S2 API key found — unauthenticated requests may be rate-limited")
    logger.info("Running s2-search: %s", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, timeout=180, env=env)
        with out.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
        logger.error("s2-search subprocess failed: %s", e)
        return {"source": "s2", "papers": [], "total_found": 0, "error": str(e)}


def _extract_doi_from_url(url: str) -> str:
    """从常见学术论文 URL 中提取 DOI（用于 Zotero 去重）。

    支持：
      https://dl.acm.org/doi/abs/10.1145/3691620.3695073
      https://doi.org/10.1145/3634737.3656288
      https://link.springer.com/article/10.1007/s00453-023-01091-7
    """
    if not url:
        return ""
    # DOI 格式：10.NNNN/任意字符串（含 /），直到遇到 URL 参数 ?/# 或空格
    # 模式1：doi.org 直接含 DOI，或 /doi/abs|full|pdf 后跟 DOI
    m = re.search(
        r"(?:doi\.org|/doi(?:/abs|/full|/pdf|/epdf)?)/\s*(10\.\d{4,}[^\s?#]+)",
        url, re.IGNORECASE
    )
    if m:
        doi = m.group(1).rstrip("/")
        return doi.lower()
    # 模式2：Springer /article/10.xxx/... 或类似形式（非 doi.org 路径）
    m = re.search(r"/article/(10\.\d{4,}[^\s?#]+)", url, re.IGNORECASE)
    if m:
        doi = m.group(1).rstrip("/")
        return doi.lower()
    return ""


def _extract_arxiv_id_from_url(url: str) -> str:
    """从 URL 提取 arXiv ID。"""
    if not url:
        return ""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?", url, re.IGNORECASE)
    if m:
        return m.group(1)
    return ""


_GS_REL_DATE_RE = re.compile(
    r"\b(\d+)\s*(day|days|week|weeks|month|months|year|years|hour|hours)\s*ago\b",
    re.IGNORECASE,
)


def _parse_gs_relative_date(text: str, ref_date: datetime | None = None) -> str:
    """从 GS snippet 中提取 "X days/weeks/months ago" 并转为 YYYY-MM-DD。

    GS 页面的 snippet 通常以相对时间开头（"3 days ago - ..."）。
    若解析成功返回精确日期字符串，否则返回空串。
    """
    if not text:
        return ""
    ref = ref_date or datetime.now()
    m = _GS_REL_DATE_RE.search(text)
    if not m:
        return ""
    n = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("hour"):
        delta_days = 0
    elif unit.startswith("day"):
        delta_days = n
    elif unit.startswith("week"):
        delta_days = n * 7
    elif unit.startswith("month"):
        delta_days = n * 30
    elif unit.startswith("year"):
        delta_days = n * 365
    else:
        return ""
    return (ref - timedelta(days=delta_days)).strftime("%Y-%m-%d")


def _convert_gs_raw(results: list) -> list[dict]:
    """把 GS evaluate_script 原始结果转换为统一 schema。

    修复：从 href URL 自动提取 DOI 和 arXiv ID，避免 Zotero 去重失效。
    增强：从 snippet 中解析 "X days ago" 得到精确日期，提升新近性评分准确度。
    """
    papers = []
    for r in results:
        if not isinstance(r, dict) or not r.get("title"):
            continue
        # GS 的 authorsText 格式："{authors} - {venue}, {year} - {site}"
        # 例："G Xu, T Chen - IEEE Trans. on Information Forensics and Security, 2026"
        # 用 rsplit 从最后一个 " - " 切，避免作者名中连字符干扰
        authors_text = r.get("authorsText") or ""
        if r.get("journalYear"):
            venue_year_part = r.get("journalYear")
            authors_part = authors_text
        elif " - " in authors_text:
            parts = authors_text.rsplit(" - ", 2)  # 最多切两次，去掉末尾 site
            # 形如 ["G Xu, T Chen", "IEEE Trans..., 2026", "ieeexplore.ieee.org"]
            if len(parts) >= 2:
                authors_part = parts[0]
                venue_year_part = parts[1] if len(parts) == 3 else parts[1]
            else:
                authors_part = authors_text
                venue_year_part = ""
        else:
            authors_part = authors_text
            venue_year_part = ""

        year_m = re.search(r"\b(20\d{2})\b", venue_year_part)
        year = int(year_m.group(1)) if year_m else None
        # 去掉末尾的 ", 2026" 得到纯 venue
        venue = re.split(r",\s*20\d{2}", venue_year_part)[0].strip()
        # 兜底：若 venue 来自 URL 域名（如 "researchgate.net"）则清空
        if venue and re.fullmatch(r"[\w.-]+\.(net|com|org|edu|gov)", venue):
            venue = ""

        # 若结构化 authors 字段存在则优先；否则用 authors_part
        raw_authors = r.get("authors") or authors_part
        if isinstance(raw_authors, list):
            authors = raw_authors
        else:
            authors = [a.strip() for a in re.split(r"[,;]", raw_authors) if a.strip()]
        full_text = r.get("fullTextUrl") or r.get("pdfUrl") or ""
        href = r.get("href") or r.get("url") or ""
        pdf_url = full_text if any(x in full_text for x in ("arxiv.org", ".pdf")) else ""

        # 从 href 提取 DOI 和 arXiv ID（解决 Zotero 去重 DOI 为空的问题）
        doi = _extract_doi_from_url(href)
        arxiv_id = _extract_arxiv_id_from_url(full_text or href)

        # arXiv PDF URL 补全
        if arxiv_id and not pdf_url:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

        # 从 snippet（GS 页面相对时间）解析精确日期
        snippet = r.get("snippet") or ""
        precise_date = _parse_gs_relative_date(snippet)
        if precise_date:
            published_date = precise_date
            date_is_year_only = False
        elif year:
            published_date = f"{year}-01-01"
            date_is_year_only = True
        else:
            published_date = ""
            date_is_year_only = False

        papers.append({
            "source": "gs",
            "title": r.get("title", "").strip(),
            "authors": authors,
            "abstract": snippet,
            "arxiv_id": arxiv_id,
            "doi": doi,
            "url": href,
            "pdf_url": pdf_url,
            "published_date": published_date,
            "year": year or (datetime.strptime(precise_date, "%Y-%m-%d").year if precise_date else None),
            "venue": venue,
            "citation_count": int(r.get("citedBy") or 0),
            "influential_citation_count": 0,
            "categories": [],
            "_date_is_year_only": date_is_year_only,
        })
    return papers


def _convert_cnki_raw(items: list) -> list[dict]:
    """把 cnki-parse-results 原始列表转换为统一 schema。"""
    papers = []
    for r in items:
        if not isinstance(r, dict) or not r.get("title"):
            continue
        raw_date = r.get("date") or r.get("published_date") or ""
        year = None
        y_m = re.search(r"\b(20\d{2})\b", raw_date)
        if y_m:
            year = int(y_m.group(1))
        raw_authors = r.get("authors") or []
        if isinstance(raw_authors, str):
            raw_authors = [a.strip() for a in re.split(r"[;；,，]", raw_authors) if a.strip()]
        papers.append({
            "source": "cnki",
            "title": r.get("title", "").strip(),
            "authors": raw_authors,
            "abstract": r.get("abstract") or r.get("snippet") or "",
            "arxiv_id": "",
            "doi": r.get("doi") or "",
            "url": r.get("url") or r.get("link") or "",
            "pdf_url": "",
            "published_date": raw_date[:10] if raw_date else "",
            "year": year,
            "venue": r.get("journal") or r.get("venue") or "",
            "citation_count": int(r.get("citations") or r.get("citation_count") or 0),
            "influential_citation_count": 0,
            "categories": [],
        })
    return papers


def load_external_json(path: str, source_tag: str) -> dict:
    """加载 agent 预生成的 GS/CNKI JSON。支持标准格式和原始格式自动转换。"""
    p = Path(path)
    if not p.exists():
        logger.warning("%s input not found: %s", source_tag, path)
        return {"source": source_tag, "papers": [], "total_found": 0, "error": "input not found"}
    with p.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    # 标准格式：{"papers": [...]}
    if isinstance(raw, dict) and "papers" in raw:
        for p_ in raw["papers"]:
            p_.setdefault("source", source_tag)
        return raw

    # GS evaluate_script 原始格式：{"results": [...], "total": "..."}
    if isinstance(raw, dict) and "results" in raw:
        papers = _convert_gs_raw(raw["results"])
        logger.info("Converted GS raw format: %d papers", len(papers))
        return {"source": "gs", "papers": papers, "total_found": len(papers)}

    # 列表格式（CNKI parse-results 或已标准化列表）
    if isinstance(raw, list):
        if source_tag == "cnki" and raw and "journal" in (raw[0] if raw else {}):
            papers = _convert_cnki_raw(raw)
            logger.info("Converted CNKI raw format: %d papers", len(papers))
        else:
            papers = raw
            for p_ in papers:
                p_.setdefault("source", source_tag)
        return {"source": source_tag, "papers": papers, "total_found": len(papers)}

    return {"source": source_tag, "papers": [], "total_found": 0}


ACADEMIC_AGENT_CONFIG_PATH = Path(
    r"<vault_root>/config/academic_agent.yaml"
)


def _load_agent_config() -> dict:
    """从 academic_agent.yaml 读取配置，缺失时返回空字典（不报错）。"""
    try:
        import yaml  # type: ignore
        if ACADEMIC_AGENT_CONFIG_PATH.exists():
            with ACADEMIC_AGENT_CONFIG_PATH.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Failed to load academic_agent.yaml: %s", e)
    return {}


def _load_scoring_config() -> tuple[dict, list, float]:
    """从 academic_agent.yaml 读取评分权重、recency_tiers、year_only_score。

    返回 (weights, tiers, year_only_score)，配置缺失时返回默认值。
    """
    weights = dict(SCORING_WEIGHTS_DEFAULT)
    tiers = list(_DEFAULT_RECENCY_TIERS)
    year_only_score = 1.0
    try:
        cfg = _load_agent_config()
        scoring = cfg.get("scoring", {})
        if scoring.get("weights"):
            w = scoring["weights"]
            weights = {
                "relevance":  float(w.get("relevance",  weights["relevance"])),
                "recency":    float(w.get("recency",    weights["recency"])),
                "popularity": float(w.get("popularity", weights["popularity"])),
                "quality":    float(w.get("quality",    weights["quality"])),
            }
        if scoring.get("recency_tiers"):
            tiers = [{"days": int(t["days"]), "score": float(t["score"])}
                     for t in scoring["recency_tiers"]]
        if "year_only_score" in scoring:
            year_only_score = float(scoring["year_only_score"])
        logger.info("Scoring config loaded: weights=%s, year_only_score=%.1f", weights, year_only_score)
    except Exception as e:
        logger.warning("Failed to load scoring config, using defaults: %s", e)
    return weights, tiers, year_only_score


def main():
    parser = argparse.ArgumentParser(description="Multi-source search and merge")
    parser.add_argument("--sources", default="arxiv,s2",
                        help="Comma-separated: arxiv, s2, gs, cnki")
    parser.add_argument("--keywords", required=True, help="Search keywords")
    parser.add_argument("--categories", default="cs.CR,cs.SE,cs.RO,cs.AI",
                        help="arXiv categories")
    parser.add_argument("--days", type=int, default=7,
                        help="搜索窗口天数（由调用方从 academic_agent.yaml weekly.window_days 传入）")
    parser.add_argument("--end-date", default="", help="YYYY-MM-DD (default: today)")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--per-source-top", type=int, default=20)
    parser.add_argument("--gs-input", default="", help="Pre-generated GS results JSON")
    parser.add_argument("--cnki-input", default="", help="Pre-generated CNKI results JSON")
    parser.add_argument("--title-threshold", type=float, default=0.85)
    parser.add_argument(
        "--no-date-filter", action="store_true",
        help="跳过日期过滤（精确日期论文严格过滤，year-only 论文按年份范围过滤）",
    )
    parser.add_argument(
        "--year-only-policy", default="lenient",
        choices=["lenient", "strict"],
        help="year-only 论文（GS 等只有年份精度）的日期过滤策略",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    ref_date = (datetime.now() if not args.end_date
                else datetime.strptime(args.end_date, "%Y-%m-%d"))
    start_date_str = (ref_date - timedelta(days=args.days)).strftime("%Y-%m-%d")
    end_date_str = ref_date.strftime("%Y-%m-%d")
    keywords_list = [k.strip() for k in re.split(r"[,]+", args.keywords) if k.strip()]
    keywords_query = " ".join(keywords_list)

    all_papers: list[dict] = []
    source_stats: dict[str, dict] = {}

    if "arxiv" in sources:
        res = run_arxiv_source(args.keywords, args.categories, args.days, args.per_source_top)
        source_stats["arxiv"] = {"total_found": res.get("total_found", 0),
                                  "returned": len(res.get("papers", []))}
        all_papers.extend(res.get("papers", []))

    if "s2" in sources:
        res = run_s2_source(keywords_query, start_date_str, end_date_str, args.per_source_top)
        source_stats["s2"] = {"total_found": res.get("total_found", 0),
                               "returned": len(res.get("papers", []))}
        all_papers.extend(res.get("papers", []))

    if "gs" in sources:
        res = load_external_json(args.gs_input, "gs") if args.gs_input else {
            "source": "gs", "papers": [], "total_found": 0,
            "error": "gs source requested but no --gs-input provided"}
        source_stats["gs"] = {"total_found": res.get("total_found", 0),
                               "returned": len(res.get("papers", [])),
                               "error": res.get("error")}
        all_papers.extend(res.get("papers", []))

    if "cnki" in sources:
        res = load_external_json(args.cnki_input, "cnki") if args.cnki_input else {
            "source": "cnki", "papers": [], "total_found": 0,
            "error": "cnki source requested but no --cnki-input provided"}
        source_stats["cnki"] = {"total_found": res.get("total_found", 0),
                                 "returned": len(res.get("papers", [])),
                                 "error": res.get("error")}
        all_papers.extend(res.get("papers", []))

    merged = merge_papers(all_papers, args.title_threshold)
    logger.info("Merged %d raw papers into %d unique", len(all_papers), len(merged))

    # ── 日期过滤：剔除超出搜索窗口的旧论文 ──────────────────────────────
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    date_filtered_out: list[dict] = []
    if not args.no_date_filter:
        merged, date_filtered_out = filter_by_date_window(
            merged, start_date, end_date_dt,
            year_only_policy=args.year_only_policy,
        )
        if date_filtered_out:
            logger.info(
                "Date-filter removed %d papers outside [%s, %s]",
                len(date_filtered_out), start_date_str, end_date_str,
            )
    # ────────────────────────────────────────────────────────────────────

    weights, recency_tiers, year_only_score = _load_scoring_config()
    for p in merged:
        compute_overall_score(
            p, keywords_list, ref_date, weights,
            recency_tiers=recency_tiers,
            year_only_score=year_only_score,
        )
    merged.sort(key=lambda x: x["scores"]["overall"], reverse=True)
    top_papers = merged[:args.top]

    for p in top_papers:
        p.pop("_raw", None)
        p.pop("_date_is_year_only", None)

    result = {
        "query": {
            "keywords": keywords_list,
            "categories": args.categories.split(","),
            "days": args.days,
            "end_date": end_date_str,
            "start_date": start_date_str,
        },
        "sources_used": sources,
        "source_stats": source_stats,
        "scoring_weights": SCORING_WEIGHTS_DEFAULT,
        "total_raw": len(all_papers),
        "total_merged_before_date_filter": len(merged) + len(date_filtered_out),
        "total_date_filtered_out": len(date_filtered_out),
        "total_merged": len(merged),
        "top_papers": top_papers,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(
        f"Multi-source done: raw={len(all_papers)}, "
        f"merged={len(merged)}, top={len(top_papers)} -> {output_path}"
    )
    print(f"Source stats: {json.dumps(source_stats, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
