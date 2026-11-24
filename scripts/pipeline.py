#!/usr/bin/env python3
"""Store, compile, and search a source-grounded LLM Wiki using Python 3.10+.

The saved content was compiled by an LLM from cited evidence. These commands
replay that content; they do not call a model or download original documents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
RUNTIME = WIKI / "runtime"
DATABASE = WIKI / "knowledge.sqlite3"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def card_hash(card):
    value = json.dumps(card, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def event(action, **details):
    record = {"timestamp": now(), "action": action, **details}
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def source_data():
    manifest = read(ROOT / "sources/manifest.json")
    cards = read(ROOT / "sources/evidence-cards.json")
    if not manifest or not cards:
        raise ValueError("Source manifest and evidence cards must not be empty.")
    ids = [row["id"] for row in manifest]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source IDs.")
    if len(cards) != len({card["id"] for card in cards}):
        raise ValueError("Duplicate evidence card IDs.")
    by_id = {card["id"]: card for card in cards}
    if set(ids) != set(by_id):
        raise ValueError("Source manifest and evidence card IDs differ.")
    for row in manifest:
        if not re.fullmatch(r"S[0-9]+", row["id"]):
            raise ValueError("Invalid source ID.")
        for field in ("title", "url", "publisher", "retrieved_at", "card_sha256"):
            if not row.get(field):
                raise ValueError(f"Missing source field: {row['id']}/{field}")
        if not row["url"].startswith("https://"):
            raise ValueError("Source URLs must use HTTPS.")
        card = by_id[row["id"]]
        if card_hash(card) != row["card_sha256"]:
            raise ValueError(f"Evidence card hash mismatch: {row['id']}")
        if not card.get("summary") or not card.get("claims"):
            raise ValueError(f"Incomplete evidence card: {row['id']}")
        for claim in card["claims"]:
            if not all(claim.get(key) for key in ("id", "text", "locator")):
                raise ValueError(f"Incomplete claim: {row['id']}")
    return manifest, by_id


def connect():
    WIKI.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA secure_delete = ON")
    connection.executescript("""
      CREATE TABLE IF NOT EXISTS sources (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL,
        publisher TEXT NOT NULL, retrieved_at TEXT NOT NULL,
        card_sha256 TEXT NOT NULL, card_json TEXT NOT NULL, ingested_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS pages (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, summary TEXT NOT NULL,
        body TEXT NOT NULL, page_json TEXT NOT NULL, compiled_at TEXT NOT NULL);
    """)
    return connection


def ingest():
    sources, cards = source_data()
    timestamp = now()
    with connect() as connection:
        connection.execute("DELETE FROM sources")
        for row in sources:
            connection.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?)", (
                row["id"], row["title"], row["url"], row["publisher"], row["retrieved_at"],
                row["card_sha256"], json.dumps(cards[row["id"]], ensure_ascii=False), timestamp))
        connection.commit()
        connection.execute("VACUUM")
    return event("ingest", result="pass", source_count=len(sources),
                 input="sources/evidence-cards.json", input_sha256=hash_file(ROOT / "sources/evidence-cards.json"),
                 material="selected_summaries_and_short_quotes", database="wiki/knowledge.sqlite3",
                 note="匯入精選證據卡；不包含完整原文，未重新擷取網站。")


def validate_pages(pages, source_ids):
    ids = [page["id"] for page in pages]
    if not pages or len(ids) != len(set(ids)):
        raise ValueError("Wiki pages are empty or IDs are duplicated.")
    for page in pages:
        if not re.fullmatch(r"W[0-9]+", page["id"]):
            raise ValueError("Invalid Wiki page ID.")
        if not all(page.get(field) for field in ("title", "summary", "body", "source_ids")):
            raise ValueError(f"Incomplete Wiki page: {page['id']}")
        cited = set(page["source_ids"])
        if cited - source_ids:
            raise ValueError(f"Unknown source in page: {page['id']}")
        for section in page["body"]:
            if not all(section.get(field) for field in ("heading", "text", "source_ids", "locator")):
                raise ValueError(f"Incomplete cited section: {page['id']}")
            if set(section["source_ids"]) - cited:
                raise ValueError(f"Section citation not listed by page: {page['id']}")
        if any(target not in ids or target == page["id"] for target in page.get("related", [])):
            raise ValueError(f"Invalid related page: {page['id']}")


def compile_wiki():
    sources, cards = source_data()
    pages = read(WIKI / "pages.json")
    validate_pages(pages, {row["id"] for row in sources})
    by_page = {page["id"]: page for page in pages}
    by_source = {row["id"]: row for row in sources}
    with connect() as connection:
        stored = {row[0]: row[1] for row in connection.execute("SELECT id,card_sha256 FROM sources")}
        if stored != {row["id"]: row["card_sha256"] for row in sources}:
            raise ValueError("Run ingest before compile; source evidence has changed.")
        connection.execute("DELETE FROM pages")
        for page in pages:
            body = "\n\n".join(section["heading"] + "\n" + section["text"] for section in page["body"])
            connection.execute("INSERT INTO pages VALUES (?,?,?,?,?,?)", (
                page["id"], page["title"], page["summary"], body, json.dumps(page, ensure_ascii=False), now()))
            output = [f"# {page['title']}", f"條目：{page['id']}", page["summary"]]
            for section in page["body"]:
                refs = "、".join(f"[{sid}](sources/{sid}.md)" for sid in section["source_ids"])
                output += [f"## {section['heading']}", section["text"], f"來源：{refs}", f"定位：{section['locator']}"]
            output += ["## 相關條目", "、".join(f"[{by_page[pid]['title']}]({pid}.md)" for pid in page.get("related", []))]
            output += ["## 原始文獻", "\n".join(f"- [{sid}｜{by_source[sid]['title']}]({by_source[sid]['url']})" for sid in page["source_ids"])]
            (WIKI / f"{page['id']}.md").write_text("\n\n".join(output) + "\n", encoding="utf-8")
        connection.commit()
        connection.execute("VACUUM")
    (WIKI / "sources").mkdir(exist_ok=True)
    for source in sources:
        card = cards[source["id"]]
        output = [f"# {source['id']}｜{source['title']}",
                  f"機構：{source['publisher']}\n\n文獻：{source['url']}\n\n來源取得時間：{source['retrieved_at']}",
                  "此頁提供精選編纂摘要與短引文，不是完整原文。", "## 摘要", card["summary"], "## 主張與定位"]
        output += [f"- {claim['id']}：{claim['text']}（{claim['locator']}）" for claim in card["claims"]]
        output += ["## 使用限制", "\n".join(f"- {item}" for item in card.get("limitations", []))]
        output += ["## 引用此來源的條目", "\n".join(f"- [{page['id']}｜{page['title']}](../{page['id']}.md)" for page in pages if source["id"] in page["source_ids"])]
        (WIKI / "sources" / f"{source['id']}.md").write_text("\n\n".join(output) + "\n", encoding="utf-8")
    index = ["# 釣魚防護 Wiki", "由LLM依來源編纂的持久知識；每個條目保留引用、定位與相關連結。", "## 知識條目"]
    index += [f"- [{page['id']}｜{page['title']}]({page['id']}.md)：{page['summary']}" for page in pages]
    index += ["## 來源摘要", *[f"- [{row['id']}｜{row['title']}](sources/{row['id']}.md)" for row in sources]]
    (WIKI / "index.md").write_text("\n\n".join(index) + "\n", encoding="utf-8")
    return event("compile", result="pass", page_count=len(pages), input="wiki/pages.json",
                 input_sha256=hash_file(WIKI / "pages.json"), mode="saved_llm_output_replay",
                 note="編譯已保存的LLM產出；此命令不呼叫模型。")


def query(question, limit=5):
    if not DATABASE.is_file():
        raise ValueError("Run ingest and compile before query.")
    lowered = question.strip().casefold()
    if not lowered:
        raise ValueError("Query must not be empty.")
    latin = re.findall(r"[a-z0-9_-]{2,}", lowered)
    chinese = re.findall(r"[\u3400-\u9fff]+", lowered)
    terms = set(latin + [part[i:i+2] for part in chinese for i in range(max(1, len(part)-1))])
    results = []
    with connect() as connection:
        for row in connection.execute("SELECT * FROM pages"):
            title = row["title"].casefold()
            content = (row["title"] + " " + row["summary"] + " " + row["body"]).casefold()
            score = sum(3 if term in title else 1 for term in terms if term in content)
            if lowered in content:
                score += 10
            if score:
                results.append({"score": score, **json.loads(row["page_json"])})
    results.sort(key=lambda page: (-page["score"], page["id"]))
    output = {"timestamp": now(), "question": question, "method": "本機關鍵字及中文二連詞檢索；不是即時模型回答", "results": results[:limit]}
    save(RUNTIME / "last-query.json", output)
    event("query", result="pass" if results else "no_match", matched_ids=[page["id"] for page in output["results"]], output="wiki/runtime/last-query.json")
    return output


def lint():
    sources, _ = source_data()
    pages = read(WIKI / "pages.json")
    slides = read(ROOT / "slides/slides.json")
    source_ids = {row["id"] for row in sources}
    validate_pages(pages, source_ids)
    by_page = {page["id"]: set(page["source_ids"]) for page in pages}
    if source_ids - set().union(*(page["source_ids"] for page in pages)):
        raise ValueError("Some sources are not used by the Wiki.")
    inbound = {target for page in pages for target in page.get("related", [])}
    if set(by_page) - inbound:
        raise ValueError("Some Wiki pages have no inbound related links.")
    if not slides or len(slides) != len({slide["id"] for slide in slides}):
        raise ValueError("Slides are empty or IDs are duplicated.")
    for slide in slides:
        mapped = slide.get("wiki_ids", [])
        if not mapped or set(mapped) - set(by_page):
            raise ValueError(f"Unknown or missing Wiki mapping: {slide['id']}")
        supported = set().union(*(by_page[pid] for pid in mapped))
        if not slide.get("source_ids") or set(slide["source_ids"]) - supported:
            raise ValueError(f"Unsupported source mapping: {slide['id']}")
        if interaction := slide.get("scenario"):
            if not 0 <= interaction["correct"] < len(interaction["options"]):
                raise ValueError(f"Invalid scenario option index: {slide['id']}")
    result = event("lint", result="pass", sources=len(sources), wiki_pages=len(pages), slides=len(slides),
                   limits="結構與引用映射檢查不取代語意核對、可讀性審查或瀏覽器測試。")
    save(RUNTIME / "lint.json", result)
    return result


def rebuild():
    ingest()
    compile_wiki()
    lint()
    renderer = ROOT / "scripts/render_site.py"
    if not renderer.is_file():
        raise ValueError("Missing scripts/render_site.py.")
    process = subprocess.run([sys.executable, str(renderer)], cwd=ROOT, capture_output=True)
    event("render", result="pass" if process.returncode == 0 else "fail", exit_code=process.returncode)
    if process.returncode:
        raise ValueError("Renderer failed; run scripts/render_site.py directly for details.")
    return event("rebuild", result="pass", mode="saved_llm_output_replay", note="已重播證據卡與LLM內容，沒有新的模型推論或網路請求。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("ingest", "compile", "lint", "rebuild"):
        sub.add_parser(name)
    search = sub.add_parser("query")
    search.add_argument("question")
    search.add_argument("--limit", type=int, default=5, choices=range(1, 21), metavar="1-20")
    args = parser.parse_args()
    try:
        result = query(args.question, args.limit) if args.command == "query" else {
            "ingest": ingest, "compile": compile_wiki, "lint": lint, "rebuild": rebuild}[args.command]()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as exc:
        error = str(exc).replace(str(ROOT), ".")
        result = event("failure", command=args.command, error_type=type(exc).__name__, error=error)
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
