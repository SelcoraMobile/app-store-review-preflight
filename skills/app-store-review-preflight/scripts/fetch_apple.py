#!/usr/bin/env python3
"""Fetch Apple developer sources as plain text for an App Store review preflight.

Read-only and stdlib-only. Every request is an HTTPS GET to an Apple host, so the
output is the primary source itself, not a model-written summary of it.

Subcommands:
  guidelines [--out FILE]
      The App Review Guidelines as text (the whole page, nothing truncated).
      Prints the "Last Updated" date, the section count and the output path.
  news [--since YYYY-MM-DD] [--full] [--out FILE]
      Apple Developer News (RSS) items published on or after --since.
  doc PATH_OR_URL [--out FILE]
      A developer.apple.com/documentation page. Those pages render client-side, so
      a plain fetch returns an empty shell; this reads the same content from the
      DocC JSON that the page itself loads (/tutorials/data/documentation/....json).
  page URL [--out FILE]
      Any https page on an Apple developer host, as text.
  lookup APP_ID [APP_ID ...] [--country CC]
      App Store IDs -> app name, bundle ID and seller (iTunes Lookup API).

Run with: python3 -I fetch_apple.py <subcommand> ...
Output files default to <system temp>/app-store-review-preflight/.
"""
import argparse
import html
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

ALLOWED_HOSTS = {"developer.apple.com", "www.apple.com", "apple.com", "itunes.apple.com", "apps.apple.com"}
GUIDELINES_URL = "https://developer.apple.com/app-store/review/guidelines/"
NEWS_RSS_URL = "https://developer.apple.com/news/rss/news.rss"
DOC_JSON_BASE = "https://developer.apple.com/tutorials/data/documentation/"
LOOKUP_URL = "https://itunes.apple.com/lookup"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"


# ---------------------------------------------------------------- network

def fetch(url, retries=2, timeout=30):
    """GET an https URL on an allowed Apple host and return bytes."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise SystemExit(f"refusing to fetch {url}: only https URLs on {sorted(ALLOWED_HOSTS)}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.8"})
    last = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as err:
            if err.code in (404, 410):
                raise SystemExit(f"{err.code} for {url}")
            last = err
        except (urllib.error.URLError, TimeoutError) as err:
            last = err
        time.sleep(1.5 * (attempt + 1))
    raise SystemExit(f"could not fetch {url}: {last}")


def default_out(name):
    folder = os.path.join(tempfile.gettempdir(), "app-store-review-preflight")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, name)


def write_out(text, out, default_name):
    path = out or default_out(default_name)
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


# ---------------------------------------------------------------- HTML -> text

class _TextParser(HTMLParser):
    BLOCK = {"p", "div", "li", "br", "tr", "section", "article", "ul", "ol", "table", "h1", "h2", "h3",
             "h4", "h5", "h6", "dt", "dd", "blockquote", "pre", "header", "footer", "main", "nav"}
    SKIP = {"script", "style", "noscript", "svg", "template"}
    HEAD = {"h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self.buf, self.skip = [], [], 0

    def _flush(self, prefix=""):
        text = " ".join("".join(self.buf).split())
        if text:
            self.lines.append(prefix + text)
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self._flush()
            if tag == "li":
                self.buf.append("• ")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self._flush("## " if tag in self.HEAD else "")

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)


def html_to_text(raw_html):
    parser = _TextParser()
    parser.feed(raw_html)
    parser.close()
    parser._flush()
    return "\n".join(parser.lines) + "\n"


# ---------------------------------------------------------------- DocC JSON -> text

def docc_to_text(doc):
    refs = doc.get("references", {})
    out = []

    def inline(items):
        parts = []
        for it in items or []:
            kind = it.get("type")
            if kind == "text":
                parts.append(it.get("text", ""))
            elif kind == "codeVoice":
                parts.append("`" + it.get("code", "") + "`")
            elif kind == "reference":
                ref = refs.get(it.get("identifier", ""), {})
                parts.append(ref.get("title") or it.get("identifier", "").rsplit("/", 1)[-1])
            elif kind == "link":
                parts.append(it.get("title") or it.get("destination", ""))
            elif kind == "image":
                continue
            elif "inlineContent" in it:
                parts.append(inline(it.get("inlineContent")))
            else:
                parts.append(it.get("text", ""))
        return "".join(parts)

    def blocks(items, indent=""):
        for blk in items or []:
            kind = blk.get("type")
            if kind == "heading":
                out.append("")
                out.append(indent + "## " + blk.get("text", ""))
            elif kind == "paragraph":
                out.append(indent + inline(blk.get("inlineContent")))
            elif kind in ("unorderedList", "orderedList"):
                for n, item in enumerate(blk.get("items", []), 1):
                    bullet = f"{n}. " if kind == "orderedList" else "• "
                    start = len(out)
                    blocks(item.get("content"), indent + "  ")
                    if len(out) > start:
                        out[start] = indent + bullet + out[start].lstrip()
            elif kind == "termList":
                # Each item is {"term": {...}, "definition": {...}}. JSON key order varies,
                # so always read by key: term first, then its own definition.
                for item in blk.get("items", []):
                    out.append(indent + "- " + inline(item.get("term", {}).get("inlineContent")))
                    blocks(item.get("definition", {}).get("content"), indent + "    ")
            elif kind == "aside":
                label = blk.get("name") or blk.get("style", "note").title()
                out.append(indent + label + ":")
                blocks(blk.get("content"), indent + "  ")
            elif kind == "codeListing":
                out.extend(indent + "    " + line for line in blk.get("code", []))
            elif kind == "table":
                for row in blk.get("rows", []):
                    cells = []
                    for cell in row:
                        sub = []
                        for cblk in cell:
                            if cblk.get("type") == "paragraph":
                                sub.append(inline(cblk.get("inlineContent")))
                        cells.append(" ".join(sub))
                    out.append(indent + " | ".join(cells))
            elif "content" in blk:
                blocks(blk.get("content"), indent)

    meta = doc.get("metadata", {})
    out.append("# " + meta.get("title", ""))
    abstract = inline(doc.get("abstract"))
    if abstract:
        out.append(abstract)
    for section in doc.get("primaryContentSections", []):
        kind = section.get("kind")
        if kind == "content":
            blocks(section.get("content"))
        elif kind in ("properties", "attributes", "parameters", "possibleValues"):
            out.append("")
            out.append("## " + (section.get("title") or kind))
            for item in section.get("items", section.get("values", [])):
                out.append("- " + item.get("name", ""))
                blocks(item.get("content"), "    ")
    topics = doc.get("topicSections", [])
    if topics:
        out.append("")
        out.append("## Topics")
        for section in topics:
            out.append("### " + section.get("title", ""))
            for ident in section.get("identifiers", []):
                ref = refs.get(ident, {})
                out.append(f"- {ref.get('title', ident)}  ({ref.get('url', '')})")
    return "\n".join(line.rstrip() for line in out) + "\n"


def doc_json_url(path_or_url):
    value = path_or_url.strip()
    if value.startswith("http"):
        parts = urllib.parse.urlsplit(value)
        path = parts.path
    else:
        path = "/" + value.lstrip("/")
    path = path.split("#")[0].rstrip("/")
    if path.startswith("/tutorials/data/documentation/"):
        path = path[len("/tutorials/data/documentation/"):]
    elif path.startswith("/documentation/"):
        path = path[len("/documentation/"):]
    else:
        path = path.lstrip("/")
    if path.endswith(".json"):
        path = path[:-5]
    return DOC_JSON_BASE + path.lower() + ".json"


# ---------------------------------------------------------------- news

def parse_rss(raw, since=None):
    root = ET.fromstring(raw)
    items = []
    for item in root.findall(".//item"):
        when = parsedate_to_datetime(item.findtext("pubDate") or "")
        if since and when.date() < since:
            continue
        desc = item.findtext("description") or ""
        text = " ".join(re.sub(r"<[^>]+>", " ", html.unescape(desc)).split())
        items.append({
            "date": when.date().isoformat(),
            "title": (item.findtext("title") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
            "text": text,
        })
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


# ---------------------------------------------------------------- commands

def cmd_guidelines(args):
    text = html_to_text(fetch(GUIDELINES_URL).decode("utf-8", "replace"))
    updated = re.search(r"Last Updated:\s*([^\n]+)", text)
    sections = re.findall(r"(?m)^(?:• )?(\d+\.\d+(?:\.\d+)?(?:\([a-z]+\))?)(?=\s|$)", text)
    path = write_out(text, args.out, "guidelines.txt")
    print(f"guidelines: {path}")
    print(f"last updated: {updated.group(1).strip() if updated else 'NOT FOUND (check the page)'}")
    print(f"numbered sections: {len(sections)}; first {sections[:1]}, last {sections[-1:]}")
    print(f"characters: {len(text)}")


def cmd_news(args):
    since = date.fromisoformat(args.since) if args.since else None
    items = parse_rss(fetch(NEWS_RSS_URL), since)
    lines = []
    for it in items:
        lines.append(f"{it['date']} | {it['title']} | {it['link']}")
        body = it["text"] if args.full else it["text"][:400] + ("…" if len(it["text"]) > 400 else "")
        lines.append("    " + body)
    text = "\n".join(lines) + "\n"
    if args.out:
        print(f"news: {write_out(text, args.out, 'news.txt')} ({len(items)} items)")
    else:
        sys.stdout.write(text if items else "no items in that range\n")


def cmd_doc(args):
    url = doc_json_url(args.path)
    doc = json.loads(fetch(url))
    text = docc_to_text(doc)
    if args.out:
        print(f"doc: {write_out(text, args.out, 'doc.txt')} ({len(text)} chars) from {url}")
    else:
        sys.stdout.write(text)


def cmd_page(args):
    text = html_to_text(fetch(args.url).decode("utf-8", "replace"))
    if args.out:
        print(f"page: {write_out(text, args.out, 'page.txt')} ({len(text)} chars)")
    else:
        sys.stdout.write(text)


def cmd_lookup(args):
    for app_id in args.ids:
        if not re.fullmatch(r"\d{6,12}", app_id):
            print(f"{app_id}: not a numeric App Store ID")
            continue
        query = {"id": app_id}
        if args.country:
            query["country"] = args.country
        raw = fetch(LOOKUP_URL + "?" + urllib.parse.urlencode(query))
        results = json.loads(raw).get("results", [])
        if not results:
            hint = "" if args.country else " (try --country with a storefront where the app is sold)"
            print(f"{app_id}: no app found{hint}")
            continue
        app = results[0]
        page = (app.get("trackViewUrl") or "").split("?")[0]
        print(f"{app_id}: {app.get('trackName')} | bundle {app.get('bundleId')} | seller {app.get('sellerName')} | {page}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("guidelines")
    p.add_argument("--out")
    p.set_defaults(func=cmd_guidelines)
    p = sub.add_parser("news")
    p.add_argument("--since", help="YYYY-MM-DD")
    p.add_argument("--full", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_news)
    p = sub.add_parser("doc")
    p.add_argument("path")
    p.add_argument("--out")
    p.set_defaults(func=cmd_doc)
    p = sub.add_parser("page")
    p.add_argument("url")
    p.add_argument("--out")
    p.set_defaults(func=cmd_page)
    p = sub.add_parser("lookup")
    p.add_argument("ids", nargs="+")
    p.add_argument("--country")
    p.set_defaults(func=cmd_lookup)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
