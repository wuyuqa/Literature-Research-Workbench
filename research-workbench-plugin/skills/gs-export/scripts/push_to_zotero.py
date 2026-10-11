#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Push papers (metadata + PDF) to the running Zotero desktop via the local
Connector API (http://127.0.0.1:23119/connector).

Usage:
    python push_to_zotero.py papers.json [TARGET_COLLECTION_ID]

papers.json: a JSON array. Each element:
{
  "itemType": "conferencePaper" | "journalArticle" | "book" | ...,  # optional, default conferencePaper
  "title": "...",                       # required
  "authors": [{"lastName":"Doe","firstName":"Jane"}],
  "journal": "USENIX Security 2024",    # -> proceedingsTitle/publicationTitle
  "pubdate": "2024",
  "volume": "", "issue": "", "pages": "",
  "doi": "", "url": "", "abstract": "",
  "pdfUrl": "https://.../paper.pdf"     # optional; if missing/unreachable -> metadata only
}

TARGET_COLLECTION_ID: optional Zotero collection target id (e.g. "C10").
If omitted, items go to whatever collection is currently selected in Zotero.

Behaviour contract (matches user instruction):
- If a PDF cannot be downloaded (paywall/403/redirect/timeout), SKIP the PDF,
  keep the metadata item, and report it. NEVER hang or retry-loop.
"""
import sys, json, uuid, urllib.request, urllib.error
from pathlib import Path

ZOT = "http://127.0.0.1:23119/connector"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
DL_TIMEOUT = 45          # seconds per PDF download
MAX_PDF_BYTES = 80 * 1024 * 1024


def _post(path, data=None, raw=None, headers=None, timeout=60):
    h = {"User-Agent": UA, "Zotero-Allowed-Request": "true",
         "X-Zotero-Connector-API-Version": "3"}
    if headers:
        h.update(headers)
    if raw is not None:
        body = raw
    else:
        body = json.dumps(data).encode("utf-8")
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(ZOT + path, data=body, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return -1, str(e).encode()


def ping():
    st, _ = _post("/ping", data={})
    return st == 200


def download_pdf(source):
    """Return pdf bytes or None. Never raises, never hangs past DL_TIMEOUT."""
    if not source:
        return None
    try:
        local = Path(source).expanduser()
        if local.is_file():
            data = local.read_bytes()
            return data if len(data) <= MAX_PDF_BYTES and data[:5] == b"%PDF-" else None
        req = urllib.request.Request(source, headers={"User-Agent": UA,
                                                   "Accept": "application/pdf,*/*"})
        with urllib.request.urlopen(req, timeout=DL_TIMEOUT) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            data = r.read(MAX_PDF_BYTES + 1)
        if len(data) > MAX_PDF_BYTES:
            return None
        # accept if looks like a PDF (magic) or declared pdf
        if data[:5] == b"%PDF-" or "application/pdf" in ctype:
            return data
        return None
    except Exception:
        return None


def push_one(p, target):
    title = p.get("title", "").strip()
    if not title:
        return {"title": "(no title)", "item": False, "pdf": "skip-no-title"}

    sid = uuid.uuid4().hex
    att_id = uuid.uuid4().hex
    item = {
        "itemType": p.get("itemType", "conferencePaper"),
        "title": title,
        "creators": [{"firstName": a.get("firstName", ""),
                      "lastName": a.get("lastName", ""),
                      "creatorType": "author"} for a in p.get("authors", [])],
        "date": str(p.get("pubdate", "")),
        "DOI": p.get("doi", ""),
        "url": p.get("url", ""),
        "abstractNote": p.get("abstract", ""),
        "volume": str(p.get("volume", "")),
        "issue": str(p.get("issue", "")),
        "pages": str(p.get("pages", "")),
    }
    venue = p.get("journal", "")
    if item["itemType"] == "conferencePaper":
        item["proceedingsTitle"] = venue
    elif item["itemType"] == "report":
        item["reportType"] = venue
    else:
        item["publicationTitle"] = venue

    pdf_source = p.get("pdfPath") or p.get("pdfUrl", "")
    pdf_bytes = download_pdf(pdf_source)
    if p.get("pdfPath"):
        try:
            attachment_url = Path(p["pdfPath"]).resolve().as_uri()
        except Exception:
            attachment_url = p.get("url", "")
    else:
        attachment_url = p.get("pdfUrl", "")
    if pdf_bytes:
        item["attachments"] = [{"id": att_id, "title": "Full Text PDF",
                                "mimeType": "application/pdf",
                                "url": attachment_url}]

    payload = {"sessionID": sid, "uri": p.get("url", "https://scholar.google.com"),
               "items": [item]}
    if target:
        payload["target"] = target
    st, body = _post("/saveItems", payload)
    item_ok = st in (200, 201)
    res = {"title": title, "item": item_ok, "pdf": "none",
           "session_id": sid, "attachment_id": att_id}
    try:
        res["item_response"] = json.loads(body.decode("utf-8"))
    except Exception:
        res["item_response"] = body.decode("utf-8", "ignore")[:500]
    if not item_ok:
        res["pdf"] = "skip-item-failed"
        res["err"] = body.decode("utf-8", "ignore")[:200]
        return res

    if not pdf_bytes:
        res["pdf"] = "skip-no-pdf" if pdf_source else "skip-no-url"
        return res

    # upload the PDF bytes as a child attachment.
    # NOTE: metadata must be exactly {sessionID, id, url, title}; including a
    # null parentItemID makes Zotero return HTTP 500 (verified empirically).
    meta = {"sessionID": sid, "id": att_id, "url": attachment_url,
            "title": "Full Text PDF"}
    st2, body2 = _post("/saveAttachment", raw=pdf_bytes,
                       headers={"Content-Type": "application/pdf",
                                "X-Metadata": json.dumps(meta)}, timeout=90)
    res["pdf"] = "ok" if st2 in (200, 201, 204) else "upload-failed:%s" % st2
    try:
        res["attachment_response"] = json.loads(body2.decode("utf-8"))
    except Exception:
        res["attachment_response"] = body2.decode("utf-8", "ignore")[:500]
    return res


def list_collections():
    st, body = _post("/getSelectedCollection", data={})
    if st != 200:
        print("ZOTERO_NOT_RUNNING")
        sys.exit(3)
    info = json.loads(body.decode("utf-8"))
    print("Selected:", info.get("name"), "(library:", info.get("libraryName"), ")")
    for t in info.get("targets", []):
        print("  %-4s %s%s" % (t.get("id"), "  " * t.get("level", 0), t.get("name")))


def main():
    if len(sys.argv) < 2:
        print("usage: push_to_zotero.py papers.json [TARGET_COLLECTION_ID]")
        print("       push_to_zotero.py --list")
        sys.exit(2)
    if sys.argv[1] == "--list":
        list_collections()
        return
    target = sys.argv[2] if len(sys.argv) > 2 else None
    if not ping():
        print("ZOTERO_NOT_RUNNING")
        sys.exit(3)
    papers = json.load(open(sys.argv[1], encoding="utf-8"))
    results = [push_one(p, target) for p in papers]
    ok_item = sum(1 for r in results if r["item"])
    ok_pdf = sum(1 for r in results if r["pdf"] == "ok")
    print(json.dumps({"summary": {"items_ok": ok_item, "pdf_ok": ok_pdf,
                                  "total": len(papers)},
                      "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
