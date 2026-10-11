#!/usr/bin/env python3
"""
Zotero 去重检查脚本

读取 Better BibTeX 导出的 JSON，按 arxiv_id / doi / 标题归一化匹配，
过滤掉已存在于 Zotero 中的候选论文。

用法：
    python check_zotero.py --bbt-json <path> --input <candidates.json> --output <filtered.json>
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """标题归一化：小写、去标点、合并空格。"""
    if not title:
        return ""
    s = title.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_arxiv_id_from_bbt_item(item: dict) -> str | None:
    """从 BBT item 中提取 arXiv ID。BBT 通常把 arxiv 信息放在 extra 字段或 url 字段。"""
    extra = item.get("extra", "") or ""
    m = re.search(r"arxiv\s*[:\s]\s*(\d{4}\.\d{4,5}(?:v\d+)?)", extra, re.IGNORECASE)
    if m:
        return m.group(1).split("v")[0]
    url = item.get("url", "") or ""
    m = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", url, re.IGNORECASE)
    if m:
        return m.group(1)
    archive_id = item.get("archiveID", "") or ""
    m = re.search(r"(\d{4}\.\d{4,5})", archive_id)
    if m:
        return m.group(1)
    return None


def build_zotero_index(bbt_data: dict) -> dict[str, dict]:
    """构建 Zotero 索引，便于快速查找。"""
    items = bbt_data.get("items", []) if isinstance(bbt_data, dict) else bbt_data
    index = {
        "by_arxiv_id": {},
        "by_doi": {},
        "by_title_normalized": {},
        "all_titles": [],
    }
    for item in items:
        if not isinstance(item, dict):
            continue
        key = item.get("citationKey") or item.get("itemKey") or item.get("key", "")
        title = item.get("title", "") or ""

        arxiv_id = extract_arxiv_id_from_bbt_item(item)
        if arxiv_id:
            index["by_arxiv_id"][arxiv_id] = {"key": key, "title": title}

        doi = (item.get("DOI") or item.get("doi") or "").strip().lower()
        if doi:
            index["by_doi"][doi] = {"key": key, "title": title}

        title_norm = normalize_title(title)
        if title_norm:
            index["by_title_normalized"][title_norm] = {"key": key, "title": title}
            index["all_titles"].append((title_norm, key, title))
    return index


def match_paper(paper: dict, index: dict, threshold: float) -> tuple[bool, str, str]:
    """
    判定一篇论文是否在 Zotero 中。

    返回 (matched, reason, zotero_key)
    """
    arxiv_id = (paper.get("arxiv_id") or "").strip()
    if arxiv_id:
        arxiv_id_clean = arxiv_id.split("v")[0]
        if arxiv_id_clean in index["by_arxiv_id"]:
            entry = index["by_arxiv_id"][arxiv_id_clean]
            return True, f"matched arxiv_id {arxiv_id_clean}", entry["key"]

    doi = (paper.get("doi") or "").strip().lower()
    if doi and doi in index["by_doi"]:
        entry = index["by_doi"][doi]
        return True, f"matched doi {doi}", entry["key"]

    title = paper.get("title", "") or ""
    title_norm = normalize_title(title)
    if title_norm:
        if title_norm in index["by_title_normalized"]:
            entry = index["by_title_normalized"][title_norm]
            return True, "matched title exactly", entry["key"]
        best_ratio = 0.0
        best_key = ""
        best_title = ""
        for cand_norm, cand_key, cand_title in index["all_titles"]:
            ratio = SequenceMatcher(None, title_norm, cand_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_key = cand_key
                best_title = cand_title
        if best_ratio >= threshold:
            return True, f"matched title fuzzy ratio={best_ratio:.2f} ({best_title!r})", best_key

    return False, "", ""


def load_bbt_json(bbt_path: Path) -> dict | None:
    """加载 BBT JSON。支持文件路径或目录（合并目录内所有 .json 的 items）。"""
    if not bbt_path.exists():
        logger.warning("BBT JSON path not found: %s", bbt_path)
        return None

    if bbt_path.is_dir():
        json_files = sorted(bbt_path.glob("*.json"))
        if not json_files:
            logger.warning("No .json files found in directory: %s", bbt_path)
            return None
        merged_items: list = []
        for jf in json_files:
            try:
                with jf.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                items = data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                merged_items.extend(items)
                logger.info("Loaded %d items from %s", len(items), jf.name)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Skipping %s: %s", jf.name, e)
        logger.info("Total merged items from directory: %d", len(merged_items))
        return {"items": merged_items}

    try:
        with bbt_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to parse BBT JSON: %s", e)
        return None


def check_zotero(
    bbt_json_path: str,
    candidates: list[dict],
    threshold: float = 0.85,
) -> dict[str, Any]:
    """主入口：检查候选论文是否在 Zotero 中。"""
    bbt_path = Path(bbt_json_path)
    bbt_data = load_bbt_json(bbt_path)

    if bbt_data is None:
        return {
            "filtered": candidates,
            "skipped": [],
            "stats": {
                "input_count": len(candidates),
                "filtered_count": len(candidates),
                "skipped_count": 0,
                "bbt_json_available": False,
                "bbt_path": str(bbt_path),
                "note": "BBT JSON not available, no dedup performed",
            },
        }

    index = build_zotero_index(bbt_data)
    logger.info(
        "Zotero index built: %d arxiv_ids, %d dois, %d titles",
        len(index["by_arxiv_id"]),
        len(index["by_doi"]),
        len(index["by_title_normalized"]),
    )

    filtered: list[dict] = []
    skipped: list[dict] = []
    for paper in candidates:
        matched, reason, key = match_paper(paper, index, threshold)
        if matched:
            skipped.append({"paper": paper, "reason": reason, "zotero_key": key})
        else:
            filtered.append(paper)

    return {
        "filtered": filtered,
        "skipped": skipped,
        "stats": {
            "input_count": len(candidates),
            "filtered_count": len(filtered),
            "skipped_count": len(skipped),
            "bbt_json_available": True,
            "bbt_path": str(bbt_path),
            "zotero_total_items": len(index["all_titles"]),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Zotero dedup check")
    parser.add_argument("--bbt-json", required=True, help="Path to BBT JSON export")
    parser.add_argument("--input", required=True, help="Input candidates JSON")
    parser.add_argument("--output", required=True, help="Output filtered JSON")
    parser.add_argument("--threshold", type=float, default=0.85, help="Title similarity threshold")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    input_path = Path(args.input)
    with input_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict) and "top_papers" in raw:
        candidates = raw["top_papers"]
    elif isinstance(raw, list):
        candidates = raw
    else:
        candidates = raw.get("papers", []) if isinstance(raw, dict) else []

    result = check_zotero(args.bbt_json, candidates, args.threshold)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    stats = result["stats"]
    print(f"Zotero check done: input={stats['input_count']}, "
          f"filtered={stats['filtered_count']}, "
          f"skipped={stats['skipped_count']}, "
          f"bbt_available={stats['bbt_json_available']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
