#!/usr/bin/env python3
"""Check that the app's URLs answer and that hardcoded App Store IDs are the right app.

Read-only (HTTP GET only), stdlib-only.

Usage:
  python3 -I check_links.py --inventory INVENTORY.json [--bundle-id com.example.app] [--country us]
  python3 -I check_links.py --url https://example.com/privacy [--url ...] [--appstore-id 123456789 ...]
  python3 -I check_links.py --text https://example.com/privacy [--max-chars 20000]

--text prints a page as plain text (for reading the app's privacy policy or terms).

With --inventory it checks every literal URL the inventory found in source and
plists, and every App Store ID it found, against the app target's bundle ID.
Template URLs (with interpolation) and private or local hosts are skipped.
"""
import argparse
import concurrent.futures
import ipaddress
import json
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"
SKIP_HOST_SUFFIXES = (".local", ".localhost", ".test", ".invalid", ".example", "example.com", "example.org")
TEMPLATE_MARKERS = ("\\(", "%@", "%d", "{", "}", "$(", "<", ">")


def is_private_host(host):
    if not host or host in ("localhost",) or host.endswith(SKIP_HOST_SUFFIXES):
        return True
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False  # unresolvable: let the request report it
    return any(ipaddress.ip_address(info[4][0]).is_private for info in infos)


class _Text(HTMLParser):
    BLOCK = {"p", "div", "li", "br", "tr", "section", "article", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "dt", "dd"}
    SKIP = {"script", "style", "noscript", "svg", "template", "nav", "footer"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self.buf, self.skip = [], [], 0

    def flush(self, prefix=""):
        text = " ".join("".join(self.buf).split())
        if text:
            self.lines.append(prefix + text)
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.flush()

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self.flush("## " if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} else "")

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)


def page_text(url, max_chars):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or is_private_host(parts.hostname):
        return f"refusing {url}: only public http(s) pages"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read(4_000_000).decode(resp.headers.get_content_charset() or "utf-8", "replace")
    parser = _Text()
    parser.feed(raw)
    parser.flush()
    text = "\n".join(parser.lines)
    return text[:max_chars] + ("\n[…truncated]" if len(text) > max_chars else "")


def is_api_url(url):
    parts = urllib.parse.urlsplit(url)
    host, path = parts.hostname or "", parts.path or ""
    return host.startswith(("api.", "api-")) or re.search(r"/(api|v\d+)(/|$)", path) is not None


def check_url(url, timeout=15):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return url, "skipped (not http/https)", None
    if any(marker in url for marker in TEMPLATE_MARKERS):
        return url, "skipped (template)", None
    if is_private_host(parts.hostname):
        return url, "skipped (private or local host)", None
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(65536)
            return url, str(resp.status), resp.geturl().split("?")[0]
    except urllib.error.HTTPError as err:
        return url, str(err.code), (err.geturl() or url).split("?")[0]
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        return url, f"error: {getattr(err, 'reason', err)}", None


def lookup(app_id, country=None):
    query = {"id": app_id}
    if country:
        query["country"] = country
    url = "https://itunes.apple.com/lookup?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        results = json.loads(resp.read()).get("results", [])
    return results[0] if results else None


def from_inventory(path):
    with open(path, encoding="utf-8") as fh:
        inv = json.load(fh)
    urls = sorted(inv.get("sources", {}).get("urls", {}))
    ids = sorted(inv.get("sources", {}).get("appStoreIds", {}))
    bundle = None
    for proj in inv.get("projects", []):
        for target in proj.get("targets", []):
            if target.get("productType") == "com.apple.product-type.application":
                cfg = target.get("release") or next(iter(target.get("configurations", {})), None)
                bundle = (target.get("configurations", {}).get(cfg, {}) or {}).get("PRODUCT_BUNDLE_IDENTIFIER")
                break
        if bundle:
            break
    return urls, ids, bundle


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check URLs and App Store IDs")
    parser.add_argument("--inventory")
    parser.add_argument("--url", action="append", default=[])
    parser.add_argument("--appstore-id", action="append", default=[])
    parser.add_argument("--bundle-id")
    parser.add_argument("--country")
    parser.add_argument("--text", help="print this page as plain text and exit")
    parser.add_argument("--max-chars", type=int, default=20000)
    args = parser.parse_args(argv)
    if args.text:
        print(page_text(args.text, args.max_chars))
        return 0
    urls, ids, bundle = list(args.url), list(args.appstore_id), args.bundle_id
    if args.inventory:
        inv_urls, inv_ids, inv_bundle = from_inventory(args.inventory)
        urls += inv_urls
        ids += inv_ids
        bundle = bundle or inv_bundle
    urls = sorted(set(u.rstrip(".,;)") for u in urls))
    problems = 0
    if urls:
        print(f"# URLs ({len(urls)})")
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            for url, status, final in pool.map(check_url, urls):
                note = ""
                if final and final.rstrip("/") != url.split("?")[0].rstrip("/"):
                    note = f" -> {final}"
                api = is_api_url(url)
                if status.startswith(("2", "skipped")):
                    flag = ""
                elif api and not status.startswith("error"):
                    flag = "  (API endpoint: any HTTP answer means it is up)"
                else:
                    flag = "  <-- check"
                    problems += 1
                print(f"{status:>8}  {url.split('?')[0]}{note}{flag}")
    if ids:
        print(f"\n# App Store IDs ({len(ids)}), expected bundle: {bundle or 'unknown (pass --bundle-id)'}")
        for app_id in sorted(set(ids)):
            try:
                app = lookup(app_id, args.country)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as err:
                print(f"{app_id}: lookup failed ({err})")
                problems += 1
                continue
            if not app:
                print(f"{app_id}: no app found{'' if args.country else ' in the US storefront (try --country)'}  <-- check")
                problems += 1
                continue
            same = bundle and app.get("bundleId") == bundle
            mark = "OK" if same else ("<-- different app" if bundle else "")
            if bundle and not same:
                problems += 1
            print(f"{app_id}: {app.get('trackName')} | {app.get('bundleId')} | seller {app.get('sellerName')}  {mark}")
    if not urls and not ids:
        print("nothing to check")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
