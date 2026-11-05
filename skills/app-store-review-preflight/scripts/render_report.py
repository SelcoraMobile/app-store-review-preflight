#!/usr/bin/env python3
"""Render the preflight report (markdown) as one self-contained, interactive HTML page.

Read-only, stdlib-only, offline. It reads the markdown report and writes only the
--out file.

Usage:
  python3 -I render_report.py APP_REVIEW_PREFLIGHT.md [--out APP_REVIEW_PREFLIGHT.html]
                              [--lang en|tr|<code>] [--labels labels.json]

The page shows counts per confidence level, the findings table and one card per
finding, with filters (confidence, needs a new build, text search). The submission
checklist becomes checkboxes whose ticks stay in the browser's local storage. There is
a table of contents, light and dark themes, a copy button per finding and a print
layout.

Safety: all report text is HTML-escaped (the report quotes web pages and App Store
Connect fields), links work only for http, https and mailto, and a
Content-Security-Policy that allows only the page's own style and script (by hash)
blocks every network request.

The renderer keys on the structure in references/report-template.md, not on the
report's language:
  - a finding is a `### [guideline] title` heading;
  - its fields are `- **Label:** value` items (plain `Label: value` lines also work);
  - its confidence is validator-certain, review-risk or judgment-call, kept verbatim;
  - "needs a new build" is the last column of the findings table (yes/no, or the
    same words in the report's language), or "New build: yes" inside the finding;
  - `- [ ]` and `- [x]` items become checkboxes.
--lang sets the language of the page's own controls (en and tr are built in);
--labels overrides any of them from a JSON object, for other languages.
"""
import argparse
import base64
import hashlib
import html
import json
import os
import re
import sys
import unicodedata

CONFIDENCE = ("validator-certain", "review-risk", "judgment-call")
CONF_CLASS = {"validator-certain": "vc", "review-risk": "rr", "judgment-call": "jc"}
CONF_RE = re.compile(r"(?<![\w-])(validator-certain|review-risk|judgment-call)(?![\w-])", re.I)

YES = {"yes", "y", "true", "evet", "ja", "oui", "sí", "si", "sì", "sim", "да", "tak", "ano",
       "kyllä", "igen", "是", "是的", "はい", "要", "필요", "예", "네", "✓", "✔"}
NO = {"no", "n", "false", "hayır", "hayir", "nein", "non", "não", "nao", "нет", "nie", "ne",
      "ei", "nem", "否", "不", "いいえ", "不要", "아니요", "아니오", "불필요", "✗", "✘", "—", "-"}
NEW_BUILD_RE = re.compile(
    r"(?:needs?\s+(?:a\s+)?new\s+build|new\s+build|yeni\s+build|yeni\s+derleme|neuer\s+build|"
    r"nouveau\s+build|nueva\s+compilación|novo\s+build|nuova\s+build)\s*\**\s*[:：]\s*\**\s*([^\s.,;)*]+)",
    re.I)

# Field labels in the languages reports are most often written in. Unknown labels still
# work when they are bold, or when they start a line right after another field.
KNOWN_FIELDS = {
    "confidence": "confidence", "güven": "confidence", "güven düzeyi": "confidence",
    "kesinlik": "confidence", "konfidenz": "confidence", "sicherheit": "confidence",
    "confiance": "confidence", "confianza": "confidence", "confiança": "confidence",
    "affidabilità": "confidence", "fiducia": "confidence",
    "evidence": "evidence", "kanıt": "evidence", "kanıtlar": "evidence", "delil": "evidence",
    "nachweis": "evidence", "belege": "evidence", "beleg": "evidence", "preuve": "evidence",
    "preuves": "evidence", "evidencia": "evidence", "evidência": "evidence", "prova": "evidence",
    "prove": "evidence",
    "why it matters": "why", "neden önemli": "why", "neden önemli?": "why", "önemi": "why",
    "warum es wichtig ist": "why", "warum wichtig": "why", "pourquoi c'est important": "why",
    "por qué importa": "why", "por que importa": "why", "perché è importante": "why",
    "fix": "fix", "düzeltme": "fix", "çözüm": "fix", "behebung": "fix", "lösung": "fix",
    "correction": "fix", "correctif": "fix", "corrección": "fix", "solución": "fix",
    "correção": "fix", "solução": "fix", "correzione": "fix", "soluzione": "fix",
}

LABELS = {
    "en": {
        "eyebrow": "App Store review preflight",
        "contents": "Contents",
        "tile_findings": "Findings",
        "tile_build": "Need a new build",
        "tile_checklist": "Checklist",
        "badge_build": "New build",
        "filter_all": "All",
        "filter_build": "Needs a new build",
        "search": "Search findings",
        "expand": "Expand all",
        "collapse": "Collapse all",
        "print": "Print",
        "showing": "{shown} of {total} findings",
        "none_match": "No findings match these filters.",
        "no_findings": "No findings in this report.",
        "done": "{done} of {total} done",
        "reset": "Reset ticks",
        "copy": "Copy as markdown",
        "copied": "Copied",
        "theme": "Theme",
        "theme_auto": "Auto",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "validator-certain": "Upload validation or App Store Connect blocks this deterministically.",
        "review-risk": "A pattern reviewers reject repeatedly, backed by the live guideline text.",
        "judgment-call": "An assessment a reasonable reviewer could make either way.",
        "footer": "Rendered from {source} by app-store-review-preflight {version}. "
                  "A risk assessment, not a guarantee of approval.",
    },
    "tr": {
        "eyebrow": "App Store inceleme ön kontrolü",
        "contents": "İçindekiler",
        "tile_findings": "Bulgu",
        "tile_build": "Yeni build gerektiren",
        "tile_checklist": "Kontrol listesi",
        "badge_build": "Yeni build",
        "filter_all": "Tümü",
        "filter_build": "Yeni build gerektirenler",
        "search": "Bulgularda ara",
        "expand": "Tümünü aç",
        "collapse": "Tümünü kapat",
        "print": "Yazdır",
        "showing": "{total} bulgudan {shown} tanesi gösteriliyor",
        "none_match": "Bu filtrelere uyan bulgu yok.",
        "no_findings": "Bu raporda bulgu yok.",
        "done": "{done}/{total} tamamlandı",
        "reset": "İşaretleri sıfırla",
        "copy": "Markdown olarak kopyala",
        "copied": "Kopyalandı",
        "theme": "Tema",
        "theme_auto": "Otomatik",
        "theme_light": "Açık",
        "theme_dark": "Koyu",
        "validator-certain": "Yükleme doğrulaması veya App Store Connect bunu kesin olarak engeller.",
        "review-risk": "İncelemede sık reddedilen, güncel yönerge metnine dayanan bir durum.",
        "judgment-call": "Makul bir inceleyicinin iki yönde de değerlendirebileceği bir konu.",
        "footer": "{source} dosyasından app-store-review-preflight {version} ile oluşturuldu. "
                  "Bu bir risk değerlendirmesidir, onay garantisi değildir.",
    },
}

# ---------------------------------------------------------------------------
# Markdown: a deliberately small subset (what the report template uses). Raw HTML in
# the markdown is never passed through; it is shown as text.

FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})[ \t]*([^`\s]*)[^`]*$")
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
HR_RE = re.compile(r"^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
LIST_RE = re.compile(r"^([ ]*)([-*+]|\d{1,9}[.)])(?:([ \t]+)(.*))?$")
QUOTE_RE = re.compile(r"^ {0,3}>[ ]?(.*)$")
TABLE_SEP_RE = re.compile(r"^ {0,3}\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$")
TASK_RE = re.compile(r"^\[([ xX])\][ \t]+(.*)$")

INLINE_RE = re.compile(
    r"\\(?P<esc>[\\`*_{}\[\]()#+\-.!|<>~])"
    r"|(?P<ticks>`+)(?P<code>.+?)(?P=ticks)"
    r"|\[(?P<ltext>[^\]\n]+)\]\((?P<lurl>[^()\s]+)(?:[ \t]+\"[^\"]*\")?\)"
    r"|<(?P<aurl>https?://[^\s<>]+)>"
    r"|(?P<url>https?://[^\s<>\"'`]*[^\s<>\"'`.,;:!?)\]])"
)
BOLD_RE = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
ITALIC_RE = re.compile(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])")
PLACEHOLDER_RE = re.compile("\x00(\\d+)\x00")


def esc(text):
    return html.escape(text, quote=True)


def safe_href(url):
    """The URL if it is http, https, mailto or relative; None for anything else."""
    raw = url.strip()
    if raw.startswith("//"):
        return None
    scheme = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*):", raw)
    if scheme and scheme.group(1).lower() not in ("http", "https", "mailto"):
        return None
    return raw


def anchor(href, inner):
    external = re.match(r"^https?:", href, re.I)
    extra = ' target="_blank" rel="noopener noreferrer"' if external else ""
    return f'<a href="{esc(href)}"{extra}>{inner}</a>'


def render_inline(text, links=True):
    text = text.replace("\x00", "")
    kept, out, pos = [], [], 0

    def keep(fragment):
        kept.append(fragment)
        return f"\x00{len(kept) - 1}\x00"

    for m in INLINE_RE.finditer(text):
        out.append(html.escape(text[pos:m.start()], quote=False))
        pos = m.end()
        if m.group("esc") is not None:
            out.append(keep(esc(m.group("esc"))))
        elif m.group("code") is not None:
            code = m.group("code")
            if len(code) > 1 and code.startswith(" ") and code.endswith(" "):
                code = code[1:-1]
            out.append(keep(f"<code>{html.escape(code, quote=False)}</code>"))
        elif m.group("ltext") is not None:
            inner = render_inline(m.group("ltext"), links=False)
            href = safe_href(m.group("lurl"))
            out.append(keep(anchor(href, inner) if links and href else inner))
        else:
            url = m.group("aurl") or m.group("url")
            href = safe_href(url)
            shown = html.escape(url, quote=False)
            out.append(keep(anchor(href, shown) if links and href else shown))
    out.append(html.escape(text[pos:], quote=False))
    joined = BOLD_RE.sub(r"<strong>\1</strong>", "".join(out))
    joined = ITALIC_RE.sub(r"<em>\1</em>", joined)
    return PLACEHOLDER_RE.sub(lambda m: kept[int(m.group(1))], joined)


def plain(text):
    """Markdown inline text without its markup, for ids, titles and matching."""
    text = re.sub(r"\[([^\]\n]+)\]\([^)\s]+\)", r"\1", text)
    text = re.sub(r"[`*]", "", text)
    return re.sub(r"\\(.)", r"\1", text).strip()


def indent_of(line):
    return len(line) - len(line.lstrip(" "))


def split_row(line):
    """Cells of a pipe-table row; pipes inside code spans or escaped stay in the cell."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, buf, ticks, i = [], [], 0, 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            buf.append("|")
            i += 2
            continue
        if ch == "`":
            run = len(s[i:]) - len(s[i:].lstrip("`"))
            ticks = 0 if ticks == run else (run if ticks == 0 else ticks)
            buf.append("`" * run)
            i += run
            continue
        if ch == "|" and not ticks:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf).strip())
    return cells


def is_table_start(lines, i):
    return ("|" in lines[i] and i + 1 < len(lines) and "|" in lines[i + 1]
            and "-" in lines[i + 1] and bool(TABLE_SEP_RE.match(lines[i + 1])))


def starts_block(lines, i):
    line = lines[i]
    return bool(HEADING_RE.match(line) or FENCE_RE.match(line) or HR_RE.match(line)
                or QUOTE_RE.match(line) or LIST_RE.match(line) or is_table_start(lines, i))


def parse_blocks(lines):
    blocks, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        start = i
        m = FENCE_RE.match(line)
        if m:
            fence, pad = m.group(2), len(m.group(1))
            close = re.compile(r"^ {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*$")
            body, i = [], i + 1
            while i < n and not close.match(lines[i]):
                body.append(lines[i][min(pad, indent_of(lines[i])):])
                i += 1
            i += 1
            blocks.append({"t": "code", "lang": m.group(3), "text": "\n".join(body), "span": (start, i)})
            continue
        m = HEADING_RE.match(line)
        if m:
            i += 1
            blocks.append({"t": "h", "level": len(m.group(1)), "text": (m.group(2) or "").strip(), "span": (start, i)})
            continue
        if HR_RE.match(line):
            i += 1
            blocks.append({"t": "hr", "span": (start, i)})
            continue
        if is_table_start(lines, i):
            header = split_row(lines[i])
            aligns = []
            for cell in split_row(lines[i + 1]):
                cell = cell.strip()
                aligns.append("c" if cell.startswith(":") and cell.endswith(":") else "r" if cell.endswith(":") else "")
            rows, i = [], i + 2
            while i < n and lines[i].strip() and "|" in lines[i]:
                row = split_row(lines[i])
                row = (row + [""] * len(header))[:len(header)]
                rows.append(row)
                i += 1
            blocks.append({"t": "table", "header": header, "aligns": aligns, "rows": rows, "span": (start, i)})
            continue
        if QUOTE_RE.match(line):
            inner = []
            while i < n and lines[i].strip():
                q = QUOTE_RE.match(lines[i])
                if q:
                    inner.append(q.group(1))
                elif inner and not starts_block(lines, i):
                    inner.append(lines[i].strip())
                else:
                    break
                i += 1
            blocks.append({"t": "quote", "blocks": parse_blocks(inner), "span": (start, i)})
            continue
        m = LIST_RE.match(line)
        if m:
            block, i = parse_list(lines, i)
            block["span"] = (start, i)
            blocks.append(block)
            continue
        para = []
        while i < n and lines[i].strip() and (not para or not starts_block(lines, i)):
            para.append(lines[i].strip() if not lines[i].endswith("  ") else lines[i].strip() + "  ")
            i += 1
        blocks.append({"t": "p", "lines": para, "span": (start, i)})
    return blocks


def parse_list(lines, i):
    n = len(lines)
    first = LIST_RE.match(lines[i])
    ordered = first.group(2)[0].isdigit()
    start_no = int(first.group(2)[:-1]) if ordered else 1
    base = len(first.group(1))
    items = []
    while i < n:
        m = LIST_RE.match(lines[i])
        if not m or HR_RE.match(lines[i]) or len(m.group(1)) != base or m.group(2)[0].isdigit() != ordered:
            break
        spaces = m.group(3) or " "
        content_indent = base + len(m.group(2)) + (len(spaces) if len(spaces) <= 4 else 1)
        body = [m.group(4) or ""]
        i += 1
        while i < n:
            line = lines[i]
            if not line.strip():
                j = i
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and indent_of(lines[j]) >= content_indent:
                    body.extend([""] * (j - i))
                    i = j
                    continue
                nxt = LIST_RE.match(lines[j]) if j < n else None
                if nxt and len(nxt.group(1)) == base and nxt.group(2)[0].isdigit() == ordered:
                    i = j  # loose list: the next item follows a blank line
                break
            lead = indent_of(line)
            if lead >= content_indent:
                body.append(line[content_indent:])
            elif LIST_RE.match(line) and lead > base:
                body.append(line[lead:])
            elif LIST_RE.match(line) or starts_block(lines, i) or not body[-1].strip():
                break
            else:
                body.append(line.strip())  # lazy continuation of the item's paragraph
            i += 1
        task = None
        t = TASK_RE.match(body[0])
        if t:
            task = t.group(1).lower() == "x"
            body[0] = t.group(2)
        items.append({"task": task, "blocks": parse_blocks(body)})
    return {"t": "list", "ordered": ordered, "start": start_no, "items": items}, i


class Ctx:
    def __init__(self):
        self.task_ids = 0
        self.tasks = []  # (section id, checked)
        self.section = ""


def render_para(lines):
    parts = []
    for k, line in enumerate(lines):
        hard = line.endswith("  ") or line.endswith("\\")
        text = line.rstrip()
        if text.endswith("\\"):
            text = text[:-1]
        parts.append(render_inline(text))
        if k < len(lines) - 1:
            parts.append("<br>" if hard else "\n")
    return "".join(parts)


def render_blocks(blocks, ctx, heading_ids=None):
    out = []
    for b in blocks:
        t = b["t"]
        if t == "p":
            out.append(f"<p>{render_para(b['lines'])}</p>")
        elif t == "h":
            level = min(max(b["level"], 3), 6)
            hid = f' id="{heading_ids(b["text"])}"' if heading_ids else ""
            out.append(f"<h{level}{hid}>{render_inline(b['text'])}</h{level}>")
        elif t == "code":
            lang = f' data-lang="{esc(b["lang"])}"' if b["lang"] else ""
            out.append(f"<pre{lang}><code>{html.escape(b['text'], quote=False)}</code></pre>")
        elif t == "hr":
            out.append("<hr>")
        elif t == "quote":
            out.append(f"<blockquote>{render_blocks(b['blocks'], ctx)}</blockquote>")
        elif t == "table":
            out.append(render_table(b))
        elif t == "list":
            out.append(render_list(b, ctx))
    return "\n".join(out)


def align_class(aligns, k):
    a = aligns[k] if k < len(aligns) else ""
    return f' class="al-{a}"' if a else ""


def render_table(b, row_attrs=None, cell_fn=None):
    head = "".join(f"<th{align_class(b['aligns'], k)}>{render_inline(c)}</th>" for k, c in enumerate(b["header"]))
    body = []
    for r, row in enumerate(b["rows"]):
        cells = []
        for k, c in enumerate(row):
            inner = cell_fn(r, k, c) if cell_fn else None
            cells.append(f"<td{align_class(b['aligns'], k)}>{inner if inner is not None else render_inline(c)}</td>")
        attrs = row_attrs(r) if row_attrs else ""
        body.append(f"<tr{attrs}>{''.join(cells)}</tr>")
    cls = ' class="overview"' if row_attrs else ""
    return (f'<div class="table-wrap"><table{cls}><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def render_list(b, ctx):
    tag = "ol" if b["ordered"] else "ul"
    start = f' start="{b["start"]}"' if b["ordered"] and b["start"] != 1 else ""
    items = []
    for item in b["items"]:
        blocks = item["blocks"]
        if item["task"] is None:
            items.append(f"<li>{render_blocks(blocks, ctx)}</li>")
            continue
        ctx.task_ids += 1
        tid = f"t-{ctx.task_ids}"
        first = blocks[0] if blocks and blocks[0]["t"] == "p" else None
        label_text = " ".join(first["lines"]) if first else ""
        key = hashlib.sha1(" ".join(plain(label_text).split()).lower().encode("utf-8")).hexdigest()[:12]
        ctx.tasks.append((ctx.section, item["task"]))
        checked = " checked" if item["task"] else ""
        rest = render_blocks(blocks[1:] if first else blocks, ctx)
        items.append(
            f'<li class="task"><input type="checkbox" id="{tid}" data-task="{key}" '
            f'data-section="{esc(ctx.section)}" data-default="{1 if item["task"] else 0}"{checked}>'
            f'<div class="tb"><label for="{tid}">{render_para(first["lines"]) if first else ""}</label>{rest}</div></li>')
    cls = ' class="tasks"' if any(it["task"] is not None for it in b["items"]) else ""
    return f"<{tag}{start}{cls}>{''.join(items)}</{tag}>"


# ---------------------------------------------------------------------------
# Report structure

BOLD_FIELD_RE = re.compile(r"^\*\*(?P<label>[^*\n]{1,48}?)\*\*[ \t]*(?P<rest>.*)$")
PLAIN_FIELD_RE = re.compile(r"^(?P<label>[^\W\d_][^:*`\[\]|<>\n]{0,40}?)[ \t]*[:：](?:[ \t]+(?P<rest>.*))?$")
SENTENCE_END = tuple(".!?)\"'”’`。！？")


def field_kind(label):
    return KNOWN_FIELDS.get(" ".join(label.lower().split()).rstrip(":："))


def bold_field(line):
    m = BOLD_FIELD_RE.match(line.strip())
    if not m:
        return None
    label, rest = m.group("label").strip(), m.group("rest")
    if label.endswith((":", "：")):
        label = label[:-1].strip()
    elif rest.startswith((":", "：")):
        rest = rest[1:]
    else:
        return None
    if not label or len(label.split()) > 6:
        return None
    return label, rest.strip()


def plain_field(line, prev):
    m = PLAIN_FIELD_RE.match(line.strip())
    if not m or "://" in line[:m.end("label") + 3]:
        return None
    label = m.group("label").strip()
    if len(label.split()) > 4:
        return None
    if not field_kind(label):
        p = (prev or "").rstrip()
        if p and not (p.endswith(SENTENCE_END) or CONF_RE.search(p)):
            return None
    return label, (m.group("rest") or "").strip()


def extract_fields(blocks):
    """Split a finding's blocks into labelled fields and the blocks around them."""
    fields, loose = [], []

    def add(block):
        (fields[-1]["blocks"] if fields else loose).append(block)

    for b in blocks:
        if b["t"] == "list" and not b["ordered"] and b["items"]:
            head = b["items"][0]["blocks"]
            if head and head[0]["t"] == "p" and bold_field(head[0]["lines"][0]):
                for item in b["items"]:
                    ib = item["blocks"]
                    found = bold_field(ib[0]["lines"][0]) if ib and ib[0]["t"] == "p" else None
                    if not found:
                        add({"t": "list", "ordered": False, "start": 1, "items": [item]})
                        continue
                    label, rest = found
                    para_lines = ([rest] if rest else []) + ib[0]["lines"][1:]
                    value = ([{"t": "p", "lines": para_lines}] if para_lines else []) + ib[1:]
                    fields.append({"label": label, "blocks": value})
                continue
        if b["t"] == "p":
            groups, pre, prev = [], [], None
            for line in b["lines"]:
                found = bold_field(line) or plain_field(line, prev if groups else None)
                if found:
                    groups.append([found[0], [found[1]] if found[1] else []])
                elif groups:
                    groups[-1][1].append(line)
                else:
                    pre.append(line)
                prev = line
            if groups:
                if pre:
                    add({"t": "p", "lines": pre})
                for label, value in groups:
                    fields.append({"label": label, "blocks": [{"t": "p", "lines": value}] if value else []})
                continue
        add(b)
    return fields, loose


def blocks_text(blocks):
    out = []
    for b in blocks:
        if b["t"] == "p":
            out.extend(b["lines"])
        elif b["t"] in ("h",):
            out.append(b["text"])
        elif b["t"] == "code":
            out.append(b["text"])
        elif b["t"] == "quote":
            out.append(blocks_text(b["blocks"]))
        elif b["t"] == "list":
            out.extend(blocks_text(it["blocks"]) for it in b["items"])
        elif b["t"] == "table":
            out.extend(" ".join(r) for r in [b["header"]] + b["rows"])
    return "\n".join(out)


def classify_build(text):
    words = re.findall(r"[^\W_]+|[✓✔✗✘—-]", plain(text).lower())
    if not words:
        return ""
    return "yes" if words[0] in YES else "no" if words[0] in NO else ""


def slugger():
    used = set()

    def slug(text):
        s = unicodedata.normalize("NFKC", plain(text)).lower()
        s = re.sub(r"[^\w]+", "-", s).strip("-") or "section"
        base, k = s, 2
        while s in used:
            s, k = f"{base}-{k}", k + 1
        used.add(s)
        return s
    return slug


def parse_report(text):
    lines = [l.expandtabs(4) for l in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    blocks = parse_blocks(lines)
    doc = {"title": "", "meta": [], "sections": [], "cards": []}
    section = None
    for b in blocks:
        if b["t"] == "h" and b["level"] == 1 and not doc["title"] and section is None:
            doc["title"] = b["text"]
            continue
        if b["t"] == "h" and b["level"] <= 2:
            section = {"title": b["text"], "items": []}
            doc["sections"].append(section)
            continue
        if b["t"] == "h" and b["level"] == 3:
            m = re.match(r"^\[([^\]]+)\]\s*(.*)$", b["text"])
            if m:
                card = {"guideline": m.group(1).strip(), "title": m.group(2).strip(), "blocks": [],
                        "span": list(b["span"]), "section": section}
                doc["cards"].append(card)
                if section is None:
                    section = {"title": "", "items": []}
                    doc["sections"].append(section)
                section["items"].append(("card", card))
                continue
        target = section["items"] if section else None
        if target is not None and target and target[-1][0] == "card" and not (b["t"] == "h" and b["level"] <= 3):
            card = target[-1][1]
            card["blocks"].append(b)
            card["span"][1] = b["span"][1]
            continue
        if target is None:
            doc["meta"].append(b)
        else:
            target.append(("block", b))
    for k, card in enumerate(doc["cards"], 1):
        card["n"] = k
        card["id"] = f"f-{k}"
        card["raw"] = "\n".join(lines[card["span"][0]:card["span"][1]]).strip()
        card["fields"], card["loose"] = extract_fields(card["blocks"])
        card["conf"], card["qualifier"], card["build"] = "", "", ""
        for f in card["fields"]:
            kind = field_kind(f["label"])
            value = blocks_text(f["blocks"])
            m = CONF_RE.search(value)
            if m and (kind == "confidence" or value.strip().lower().startswith(m.group(1).lower())):
                f["kind"] = "confidence"
                card["conf"] = m.group(1).lower()
                qualifier = " ".join((value[:m.start()] + value[m.end():]).split()).strip(" ;,.")
                if qualifier.startswith("(") and qualifier.endswith(")"):
                    qualifier = qualifier[1:-1].strip()
                card["qualifier"] = qualifier
                break
        if not card["conf"]:
            m = CONF_RE.search(card["raw"])
            card["conf"] = m.group(1).lower() if m else ""
        for f in card["fields"]:
            f.setdefault("kind", field_kind(f["label"]) or "other")
    link_overview(doc)
    for card in doc["cards"]:
        if not card["build"]:
            m = NEW_BUILD_RE.search(card["raw"])
            card["build"] = classify_build(m.group(1)) if m else ""
    return doc


def link_overview(doc):
    """Find the findings table and map its rows to the finding cards."""
    doc["overview"] = None
    cards = doc["cards"]
    if not cards:
        return
    section = cards[0]["section"]
    if section is None:
        return
    for kind, b in section["items"]:
        if kind == "card":
            break
        if b["t"] != "table" or not b["rows"]:
            continue
        ncol = len(b["header"])
        counts = [sum(1 for r in b["rows"] if CONF_RE.search(r[c])) for c in range(ncol)]
        conf_col = max(range(ncol), key=lambda c: counts[c]) if max(counts) else None
        last = ncol - 1
        build_col = last if last != conf_col and any(classify_build(r[last]) for r in b["rows"]) else None
        numbered = all(re.fullmatch(r"#?\d+\.?", plain(r[0])) for r in b["rows"])
        mapping = []
        for idx, row in enumerate(b["rows"]):
            target = None
            if numbered:
                k = int(re.sub(r"\D", "", plain(row[0])))
                target = k - 1 if 1 <= k <= len(cards) else None
            elif len(b["rows"]) == len(cards):
                target = idx
            mapping.append(target)
            if target is not None and build_col is not None:
                cards[target]["build"] = classify_build(row[build_col])
        doc["overview"] = {"block": b, "conf_col": conf_col, "build_col": build_col,
                           "num_col": 0 if numbered else None, "mapping": mapping}
        return


# ---------------------------------------------------------------------------
# Page

ICON_CHECK = ('<svg viewBox="0 0 20 20" aria-hidden="true"><path fill="currentColor" d="M10 1.5a8.5 8.5 0 1 0 '
              '0 17 8.5 8.5 0 0 0 0-17Zm4.03 6.28-4.75 5.5a.75.75 0 0 1-1.1.04l-2.25-2.25a.75.75 0 1 1 1.06-1.06'
              'l1.68 1.68 4.22-4.89a.75.75 0 1 1 1.14.98Z"/></svg>')
ICON_SEARCH = ('<svg viewBox="0 0 20 20" aria-hidden="true"><path fill="currentColor" d="M8.5 3a5.5 5.5 0 1 0 '
               '3.4 9.82l3.64 3.64a.75.75 0 1 0 1.06-1.06l-3.64-3.64A5.5 5.5 0 0 0 8.5 3Zm-4 5.5a4 4 0 1 1 8 0 '
               '4 4 0 0 1-8 0Z"/></svg>')
ICON_CHEVRON = ('<svg class="chev" viewBox="0 0 20 20" aria-hidden="true"><path fill="currentColor" d="M7.2 '
                '4.7a.75.75 0 0 1 1.06.03l4.5 4.75a.75.75 0 0 1 0 1.04l-4.5 4.75a.75.75 0 1 1-1.09-1.03L11.15 10 '
                '7.17 5.76a.75.75 0 0 1 .03-1.06Z"/></svg>')

CSS = r"""
:root{--bg:#f5f6f8;--surface:#fff;--surface-2:#f0f2f5;--border:#e3e6eb;--border-strong:#cdd2da;
--text:#15181d;--muted:#5b6370;--faint:#8b93a1;--accent:#2457d6;--accent-soft:#e8eefc;
--vc:#cf3a33;--vc-soft:#fdeceb;--vc-ink:#9f211c;--rr:#d27a06;--rr-soft:#fff2df;--rr-ink:#8a4b00;
--jc:#5560d6;--jc-soft:#eceefd;--jc-ink:#3940a6;--nb:#11806f;--nb-soft:#e2f4f0;--nb-ink:#0a5d51;
--ok:#1f8a4c;--shadow:0 1px 2px rgba(16,24,40,.04),0 1px 3px rgba(16,24,40,.06);
--mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,Roboto,"Helvetica Neue",Arial,sans-serif;
color-scheme:light}
@media screen and (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0e1013;--surface:#16191e;
--surface-2:#1e2229;--border:#282d36;--border-strong:#383e4a;--text:#e7e9ee;--muted:#a1a9b7;--faint:#6f7787;
--accent:#7ea4ff;--accent-soft:#1c2741;--vc:#f26a61;--vc-soft:#3b1d1c;--vc-ink:#ffb3ad;--rr:#f0a23f;
--rr-soft:#38290f;--rr-ink:#ffd089;--jc:#8f97f6;--jc-soft:#24274b;--jc-ink:#c5caff;--nb:#3cc4ad;
--nb-soft:#0f2f2a;--nb-ink:#95e7d7;--ok:#46c37b;--shadow:none;color-scheme:dark}}
@media screen{:root[data-theme="dark"]{--bg:#0e1013;--surface:#16191e;--surface-2:#1e2229;--border:#282d36;
--border-strong:#383e4a;--text:#e7e9ee;--muted:#a1a9b7;--faint:#6f7787;--accent:#7ea4ff;--accent-soft:#1c2741;
--vc:#f26a61;--vc-soft:#3b1d1c;--vc-ink:#ffb3ad;--rr:#f0a23f;--rr-soft:#38290f;--rr-ink:#ffd089;--jc:#8f97f6;
--jc-soft:#24274b;--jc-ink:#c5caff;--nb:#3cc4ad;--nb-soft:#0f2f2a;--nb-ink:#95e7d7;--ok:#46c37b;--shadow:none;
color-scheme:dark}}
*,*::before,*::after{box-sizing:border-box}
[hidden]{display:none!important}
html{-webkit-text-size-adjust:100%;scroll-padding-top:136px}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.6 var(--sans);-webkit-font-smoothing:antialiased;
text-rendering:optimizeLegibility}
a{color:var(--accent);text-underline-offset:2px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.wrap{max-width:1200px;margin:0 auto;padding:0 24px}
.k-vc{--c:var(--vc);--soft:var(--vc-soft);--ink:var(--vc-ink)}
.k-rr{--c:var(--rr);--soft:var(--rr-soft);--ink:var(--rr-ink)}
.k-jc{--c:var(--jc);--soft:var(--jc-soft);--ink:var(--jc-ink)}
.k-nb{--c:var(--nb);--soft:var(--nb-soft);--ink:var(--nb-ink)}
.k-none{--c:var(--faint);--soft:var(--surface-2);--ink:var(--muted)}
.k-all{--c:var(--accent);--soft:var(--accent-soft);--ink:var(--accent)}
.masthead{background:var(--surface);border-bottom:1px solid var(--border)}
.masthead .wrap{padding-top:22px;padding-bottom:22px}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.eyebrow{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:650;letter-spacing:.08em;
text-transform:uppercase;color:var(--muted)}
.eyebrow svg{width:16px;height:16px;color:var(--accent)}
.actions{display:flex;gap:4px}
h1{font-size:clamp(24px,3.4vw,34px);line-height:1.15;letter-spacing:-.022em;margin:14px 0 8px;font-weight:720}
.meta{color:var(--muted);font-size:14px;max-width:88ch}
.meta p{margin:4px 0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:20px}
.tile{font:inherit;color:inherit;text-align:left;background:var(--surface-2);border:1px solid var(--border);
border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:2px;min-width:0}
button.tile{cursor:pointer;transition:border-color .15s,box-shadow .15s,background .15s}
button.tile:hover{border-color:var(--border-strong)}
.tile[aria-pressed="true"]{border-color:var(--c);box-shadow:inset 0 0 0 1px var(--c);background:var(--soft)}
.tile .n{font-size:28px;font-weight:720;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.1}
.tile .l{font-size:12.5px;color:var(--muted);display:flex;align-items:center;gap:6px;min-width:0}
.tile .l span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dot{width:8px;height:8px;border-radius:50%;background:var(--c);flex:none}
.dist{margin-top:14px;height:6px;border-radius:99px;overflow:hidden;background:var(--surface-2)}
.dist svg{display:block;width:100%;height:100%}
.dist .vc{fill:var(--vc)}.dist .rr{fill:var(--rr)}.dist .jc{fill:var(--jc)}.dist .none{fill:var(--faint)}
.layout{display:grid;grid-template-columns:210px minmax(0,1fr);gap:44px}
.toc{position:sticky;top:0;align-self:start;max-height:100vh;overflow:auto;padding:28px 0}
.toc-title{font-size:12px;font-weight:650;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
margin:0 0 8px 10px}
.toc ol{list-style:none;margin:0;padding:0}
.toc a{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 10px;border-radius:8px;
color:var(--text);text-decoration:none;font-size:14px;line-height:1.35}
.toc a:hover{background:var(--surface-2)}
.toc a.active{background:var(--accent-soft);color:var(--accent);font-weight:600}
.pill{font-size:12px;font-weight:600;color:var(--muted);background:var(--surface-2);border-radius:99px;
padding:1px 8px;font-variant-numeric:tabular-nums;white-space:nowrap}
.toc a.active .pill{background:var(--surface)}
main{min-width:0;padding-bottom:40px}
main>section{padding:28px 0;border-bottom:1px solid var(--border)}
main>section:last-child{border-bottom:0}
main h2{font-size:21px;letter-spacing:-.012em;line-height:1.3;margin:0 0 12px;display:flex;align-items:center;
gap:10px;flex-wrap:wrap}
main h3{font-size:16.5px;margin:22px 0 8px}
main h4,main h5,main h6{font-size:15px;margin:18px 0 6px}
p{margin:8px 0}
ul,ol{padding-left:1.4em;margin:8px 0}
li{margin:3px 0}
li>p{margin:0}
blockquote{margin:12px 0;padding:8px 14px;border-left:3px solid var(--border-strong);background:var(--surface-2);
border-radius:0 8px 8px 0;color:var(--muted)}
code{font-family:var(--mono);font-size:.86em;background:var(--surface-2);border:1px solid var(--border);
border-radius:5px;padding:.06em .36em;overflow-wrap:anywhere}
pre{background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:12px 14px;
overflow:auto;font:13px/1.55 var(--mono)}
pre code{background:none;border:0;padding:0;font-size:inherit;overflow-wrap:normal}
hr{border:0;border-top:1px solid var(--border);margin:20px 0}
.table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:12px;background:var(--surface);
margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:9px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--border)}
tbody tr:last-child td{border-bottom:0}
th{font-size:12px;font-weight:650;color:var(--muted);background:var(--surface-2);letter-spacing:.03em;
white-space:nowrap}
.al-c{text-align:center}.al-r{text-align:right}
.overview tbody tr{cursor:pointer}
.overview tbody tr:hover td{background:var(--surface-2)}
.overview td:first-child a{font:600 12.5px var(--mono);text-decoration:none}
.toolbar{position:sticky;top:0;z-index:5;background:var(--bg);padding:12px 0;display:flex;flex-wrap:wrap;gap:8px;
align-items:center;border-bottom:1px solid var(--border);margin-bottom:4px}
.search{position:relative;flex:1 1 220px;min-width:0}
.search svg{position:absolute;left:10px;top:50%;width:16px;height:16px;margin-top:-8px;color:var(--faint)}
.search input{width:100%;font:inherit;font-size:14px;color:var(--text);background:var(--surface);
border:1px solid var(--border-strong);border-radius:10px;padding:7px 12px 7px 32px}
.search input::placeholder{color:var(--faint)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font:inherit;font-size:13px;font-weight:560;color:var(--text);background:var(--surface);
border:1px solid var(--border-strong);border-radius:999px;padding:5px 11px;cursor:pointer;display:inline-flex;
align-items:center;gap:6px;white-space:nowrap}
.chip:hover{border-color:var(--c)}
.chip[aria-pressed="true"]{background:var(--soft);border-color:var(--c);color:var(--ink)}
.btn{font:inherit;font-size:13px;color:var(--muted);background:transparent;border:1px solid transparent;
border-radius:8px;padding:5px 10px;cursor:pointer;white-space:nowrap}
.btn:hover{background:var(--surface-2);color:var(--text)}
.count{font-size:13px;color:var(--muted);margin:10px 0 0}
.empty{padding:28px;text-align:center;color:var(--muted);border:1px dashed var(--border-strong);
border-radius:12px;margin-top:12px}
.cards{display:flex;flex-direction:column;gap:12px;margin-top:12px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:14px;box-shadow:var(--shadow);
overflow:hidden;position:relative}
.card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--c)}
.card.flash{outline:2px solid var(--accent);outline-offset:2px}
.card>summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:auto auto minmax(0,1fr) auto auto;
grid-template-areas:"num gls ttl badges chev";gap:8px 12px;align-items:center;padding:14px 16px 14px 20px}
.card>summary::-webkit-details-marker{display:none}
.card>summary:hover{background:var(--surface-2)}
.num{grid-area:num;font:600 12px/1 var(--mono);color:var(--muted);background:var(--surface-2);border-radius:6px;
padding:5px 7px;font-variant-numeric:tabular-nums}
.gls{grid-area:gls;display:flex;gap:4px;flex-wrap:wrap}
.gl{font:650 12.5px/1 var(--mono);color:var(--ink);background:var(--soft);border-radius:6px;padding:5px 8px;
white-space:nowrap}
.ttl{grid-area:ttl;font-weight:620;font-size:15.5px;line-height:1.4;min-width:0}
.badges{grid-area:badges;display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.chev{grid-area:chev;width:18px;height:18px;color:var(--faint);transition:transform .15s}
.card[open] .chev{transform:rotate(90deg)}
.badge{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:620;line-height:1;
padding:5px 9px;border-radius:999px;background:var(--soft);color:var(--ink);white-space:nowrap}
.badge::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--c)}
.card-body{padding:4px 20px 16px 24px;border-top:1px solid var(--border)}
.qual{margin:12px 0 0;font-size:13px;color:var(--ink);background:var(--soft);border-radius:8px;padding:6px 10px;
display:inline-block}
.fields{display:grid;grid-template-columns:minmax(110px,170px) minmax(0,1fr);column-gap:18px;margin-top:4px}
.field{display:contents}
.fl{font-size:13px;font-weight:650;color:var(--muted);
padding-top:15px;overflow-wrap:anywhere}
.fv{padding-top:12px;min-width:0;overflow-wrap:break-word}
.fv>:first-child{margin-top:0}.fv>:last-child{margin-bottom:0}
.f-why .fv,.f-fix .fv{margin-top:12px;padding:10px 12px;border-radius:10px}
.f-why .fv{background:var(--surface-2);border-left:3px solid var(--border-strong);border-radius:0 10px 10px 0}
.f-fix .fv{background:var(--nb-soft)}
.f-why .fl,.f-fix .fl{padding-top:25px}
.card-foot{display:flex;justify-content:flex-end;margin-top:12px}
ul.tasks{padding-left:0}
li.task{list-style:none;display:flex;gap:10px;align-items:flex-start;padding:6px 10px;margin:2px 0;
border-radius:8px}
li.task:hover{background:var(--surface)}
li.task input{width:18px;height:18px;margin:3px 0 0;accent-color:var(--ok);flex:none;cursor:pointer}
li.task .tb{min-width:0}
li.task label{cursor:pointer}
li.task input:checked+.tb label{color:var(--muted);text-decoration:line-through;text-decoration-color:var(--faint)}
.progress{display:inline-flex;align-items:center;gap:10px;font-size:13px;font-weight:500;color:var(--muted)}
progress{-webkit-appearance:none;appearance:none;width:120px;height:6px;border:0;border-radius:99px;
background:var(--border);overflow:hidden;vertical-align:middle}
progress::-webkit-progress-bar{background:var(--border);border-radius:99px}
progress::-webkit-progress-value{background:var(--ok);border-radius:99px}
progress::-moz-progress-bar{background:var(--ok);border-radius:99px}
.offscreen{position:fixed;left:-9999px;top:0;opacity:0}
footer{border-top:1px solid var(--border);color:var(--faint);font-size:12.5px;padding:18px 0 32px}
@media (max-width:960px){.layout{grid-template-columns:minmax(0,1fr);gap:0}
.toc{position:static;max-height:none;overflow:visible;padding:14px 0 0}
.toc-title{display:none}
.toc ol{display:flex;gap:6px;overflow-x:auto;padding-bottom:4px;scrollbar-width:none}
.toc a{white-space:nowrap;border:1px solid var(--border);background:var(--surface)}}
@media (max-width:640px){html{scroll-padding-top:16px}.wrap{padding:0 16px}
.toolbar{position:static}
.card>summary{grid-template-columns:auto minmax(0,1fr) auto;grid-template-areas:"num gls chev" "ttl ttl ttl"
"badges badges badges";padding:12px 12px 12px 16px}
.badges{justify-content:flex-start}
.card-body{padding:2px 14px 14px 16px}
.fields{grid-template-columns:minmax(0,1fr)}
.fl,.f-why .fl,.f-fix .fl{padding-top:14px}
.fv{padding-top:4px}.f-why .fv,.f-fix .fv{margin-top:6px}
.tiles{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media print{:root,:root[data-theme]{--bg:#fff;--surface:#fff;--surface-2:#f3f4f6;--border:#d9dde3;
--border-strong:#c5cad3;--text:#000;--muted:#444;--faint:#666;--shadow:none;color-scheme:light}
.toc,.toolbar,.actions,.card-foot,.btn,.chev{display:none!important}
.layout{display:block}.masthead{border:0}
.card{break-inside:avoid}
a{color:inherit}}
"""

JS = r"""
(function () {
  "use strict";
  var L = __LABELS__;
  var root = document.documentElement;
  var KEY = root.getAttribute("data-key");
  function $$(sel, el) { return Array.prototype.slice.call((el || document).querySelectorAll(sel)); }
  function get(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
  function put(k, v) { try { window.localStorage.setItem(k, v); } catch (e) {} }
  function drop(k) { try { window.localStorage.removeItem(k); } catch (e) {} }
  function fmt(s, o) { return s.replace(/\{(\w+)\}/g, function (m, k) { return o[k] != null ? o[k] : m; }); }

  // Theme: auto -> light -> dark
  var themeBtn = document.getElementById("theme");
  var modes = ["auto", "light", "dark"];
  var mode = get("aspf-theme");
  if (modes.indexOf(mode) < 0) mode = "auto";
  function applyTheme() {
    if (mode === "auto") root.removeAttribute("data-theme"); else root.setAttribute("data-theme", mode);
    themeBtn.textContent = L.theme + ": " + L["theme_" + mode];
  }
  applyTheme();
  themeBtn.addEventListener("click", function () {
    mode = modes[(modes.indexOf(mode) + 1) % modes.length];
    put("aspf-theme", mode);
    applyTheme();
  });
  document.getElementById("print").addEventListener("click", function () { window.print(); });

  // Findings: filters and search
  var cards = $$(".card");
  var rows = $$(".overview tbody tr");
  var toggles = $$("[data-filter]");
  var search = document.getElementById("search");
  var count = document.getElementById("count");
  var empty = document.getElementById("empty");
  var active = {};
  var buildOnly = false;
  function anyActive() { for (var k in active) if (active[k]) return true; return false; }
  function visible(el, q) {
    if (anyActive() && !active[el.getAttribute("data-conf")]) return false;
    if (buildOnly && el.getAttribute("data-build") !== "yes") return false;
    if (q && el.textContent.toLowerCase().indexOf(q) < 0) return false;
    return true;
  }
  function apply() {
    var q = search ? search.value.trim().toLowerCase() : "";
    var shown = 0;
    cards.forEach(function (c) { var ok = visible(c, q); c.hidden = !ok; if (ok) shown++; });
    rows.forEach(function (r) {
      var card = document.getElementById(r.getAttribute("data-card") || "");
      r.hidden = card ? card.hidden : !visible(r, q);
    });
    toggles.forEach(function (t) {
      var f = t.getAttribute("data-filter");
      var on = f === "all" ? !anyActive() && !buildOnly : f === "build" ? buildOnly : !!active[f];
      t.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (count) count.textContent = fmt(L.showing, { shown: shown, total: cards.length });
    if (empty) empty.hidden = shown !== 0 || cards.length === 0;
  }
  function toFindings() {
    var s = document.querySelector("[data-findings]");
    if (s) s.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  toggles.forEach(function (t) {
    t.addEventListener("click", function () {
      var f = t.getAttribute("data-filter");
      var tile = t.classList.contains("tile");
      if (f === "all") { active = {}; buildOnly = false; }
      else if (f === "build") { buildOnly = !buildOnly; if (tile && buildOnly) active = {}; }
      else if (tile) { var on = !active[f]; active = {}; if (on) active[f] = true; buildOnly = false; }
      else { active[f] = !active[f]; }
      apply();
      if (tile) toFindings();
    });
  });
  if (search) {
    search.addEventListener("input", apply);
    document.addEventListener("keydown", function (e) {
      var tag = (e.target && e.target.tagName) || "";
      if (e.key === "/" && !/INPUT|TEXTAREA|SELECT/.test(tag)) { e.preventDefault(); search.focus(); }
      if (e.key === "Escape" && e.target === search) { search.value = ""; apply(); search.blur(); }
    });
  }
  function openCard(id, scroll) {
    var card = document.getElementById(id);
    if (!card || !card.classList.contains("card")) return;
    card.open = true;
    if (scroll) card.scrollIntoView({ behavior: "smooth", block: "start" });
    card.classList.add("flash");
    setTimeout(function () { card.classList.remove("flash"); }, 1200);
  }
  rows.forEach(function (r) {
    r.addEventListener("click", function (e) {
      if (e.target.closest("a") && !e.target.closest("td:first-child")) return;
      e.preventDefault();
      var id = r.getAttribute("data-card");
      if (id) { history.replaceState(null, "", "#" + id); openCard(id, true); }
    });
  });
  window.addEventListener("hashchange", function () { openCard(location.hash.slice(1), false); });
  if (location.hash) openCard(location.hash.slice(1), false);
  var ex = document.getElementById("expand"), co = document.getElementById("collapse");
  if (ex) ex.addEventListener("click", function () { cards.forEach(function (c) { c.open = true; }); });
  if (co) co.addEventListener("click", function () { cards.forEach(function (c) { c.open = false; }); });
  apply();

  // Copy a finding as markdown
  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text; ta.setAttribute("readonly", ""); ta.className = "offscreen";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-copy]");
    if (!b) return;
    var tpl = document.getElementById(b.getAttribute("data-copy"));
    var text = tpl ? tpl.content.textContent : "";
    var done = function () {
      b.textContent = L.copied;
      setTimeout(function () { b.textContent = L.copy; }, 1400);
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
    } else { fallbackCopy(text); done(); }
  });

  // Checklist: ticks persist per report title
  var tasks = $$("input[data-task]");
  var saved = {};
  try { saved = JSON.parse(get(KEY) || "{}") || {}; } catch (e) { saved = {}; }
  function progress() {
    $$("[data-progress]").forEach(function (p) {
      var sec = p.getAttribute("data-progress");
      var mine = tasks.filter(function (t) { return !sec || t.getAttribute("data-section") === sec; });
      var done = mine.filter(function (t) { return t.checked; }).length;
      var bar = p.querySelector("progress");
      if (bar) { bar.max = mine.length || 1; bar.value = done; }
      var txt = p.querySelector("[data-progress-text]");
      if (txt) txt.textContent = txt.hasAttribute("data-short") ? done + "/" + mine.length : fmt(L.done, { done: done, total: mine.length });
    });
  }
  tasks.forEach(function (t) {
    var k = t.getAttribute("data-task");
    if (Object.prototype.hasOwnProperty.call(saved, k)) t.checked = !!saved[k];
    t.addEventListener("change", function () { saved[k] = t.checked; put(KEY, JSON.stringify(saved)); progress(); });
  });
  $$("[data-reset]").forEach(function (b) {
    b.addEventListener("click", function () {
      saved = {}; drop(KEY);
      tasks.forEach(function (t) { t.checked = t.getAttribute("data-default") === "1"; });
      progress();
    });
  });
  progress();

  // Print every card open; restore afterwards
  var closed = [];
  window.addEventListener("beforeprint", function () {
    closed = cards.filter(function (c) { return !c.open; });
    closed.forEach(function (c) { c.open = true; });
  });
  window.addEventListener("afterprint", function () { closed.forEach(function (c) { c.open = false; }); closed = []; });

  // Table of contents: highlight the section in view
  var links = $$(".toc a");
  if ("IntersectionObserver" in window && links.length) {
    var byId = {};
    links.forEach(function (a) { byId[a.getAttribute("href").slice(1)] = a; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        links.forEach(function (a) { a.classList.remove("active"); });
        var a = byId[en.target.id];
        if (a) a.classList.add("active");
      });
    }, { rootMargin: "-20% 0px -70% 0px" });
    $$("main > section[id]").forEach(function (s) { io.observe(s); });
  }
})();
"""


def csp_hash(text):
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii") + "'"


def skill_version():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "SKILL.md")
    try:
        with open(path, encoding="utf-8") as fh:
            m = re.search(r'^\s*version:\s*"?([\w.\-]+)"?\s*$', fh.read(), re.M)
            return m.group(1) if m else ""
    except OSError:
        return ""


def conf_class(conf):
    return CONF_CLASS.get(conf, "none")


def render_card(card, L, ctx):
    k = conf_class(card["conf"])
    gls = "".join(f'<span class="gl">{render_inline(g.strip())}</span>'
                  for g in re.split(r"\s*[,;]\s*", card["guideline"]) if g.strip())
    badges = []
    if card["conf"]:
        badges.append(f'<span class="badge k-{k}" title="{esc(L.get(card["conf"], ""))}">{esc(card["conf"])}</span>')
    if card["build"] == "yes":
        badges.append(f'<span class="badge k-nb">{esc(L["badge_build"])}</span>')
    body = []
    if card["qualifier"]:
        body.append(f'<p class="qual">{render_inline(card["qualifier"])}</p>')
    fields = []
    for f in card["fields"]:
        if f["kind"] == "confidence":
            continue
        fields.append(f'<div class="field f-{esc(f["kind"])}"><div class="fl">{render_inline(f["label"])}</div>'
                      f'<div class="fv">{render_blocks(f["blocks"], ctx)}</div></div>')
    if fields:
        body.append(f'<div class="fields">{"".join(fields)}</div>')
    if card["loose"]:
        body.append(render_blocks(card["loose"], ctx))
    tpl_id = f'md-{card["id"]}'
    body.append(f'<div class="card-foot"><button class="btn" type="button" data-copy="{tpl_id}">'
                f'{esc(L["copy"])}</button></div><template id="{tpl_id}">{html.escape(card["raw"], quote=False)}</template>')
    return (f'<details class="card k-{k}" id="{card["id"]}" data-conf="{esc(card["conf"])}" '
            f'data-build="{esc(card["build"])}" open><summary><span class="num">{card["n"]}</span>'
            f'<span class="gls">{gls}</span><span class="ttl">{render_inline(card["title"])}</span>'
            f'<span class="badges">{"".join(badges)}</span>{ICON_CHEVRON}</summary>'
            f'<div class="card-body">{"".join(body)}</div></details>')


def render_overview(doc, L):
    ov = doc["overview"]
    b, cards = ov["block"], doc["cards"]

    def row_attrs(r):
        target = ov["mapping"][r]
        if target is None:
            row = b["rows"][r]
            conf = CONF_RE.search(row[ov["conf_col"]]) if ov["conf_col"] is not None else None
            build = classify_build(row[ov["build_col"]]) if ov["build_col"] is not None else ""
            return f' data-conf="{conf.group(1).lower() if conf else ""}" data-build="{build}"'
        card = cards[target]
        return f' data-card="{card["id"]}" data-conf="{esc(card["conf"])}" data-build="{esc(card["build"])}"'

    def cell(r, k, text):
        target = ov["mapping"][r]
        if k == ov["num_col"] and target is not None:
            return f'<a href="#{cards[target]["id"]}">{esc(plain(text))}</a>'
        if k == ov["conf_col"]:
            m = CONF_RE.search(text)
            if m:
                conf = m.group(1).lower()
                rest = (text[:m.start()] + text[m.end():]).strip()
                extra = f" {render_inline(rest)}" if rest else ""
                return f'<span class="badge k-{conf_class(conf)}">{esc(conf)}</span>{extra}'
        if k == ov["build_col"] and classify_build(text) == "yes":
            return f'<span class="badge k-nb">{render_inline(text)}</span>'
        return None

    return render_table(b, row_attrs=row_attrs, cell_fn=cell)


def render_page(doc, L, lang, source, version):
    ctx = Ctx()
    slug = slugger()
    cards = doc["cards"]
    title_text = plain(doc["title"]) or os.path.splitext(source)[0]
    shown_title = doc["title"] or title_text
    for suffix in {L["eyebrow"], LABELS["en"]["eyebrow"]}:
        m = re.match(r"^(.*\S)\s*[:：–—-]\s*" + re.escape(suffix) + r"\s*$", shown_title, re.I)
        if m:
            shown_title = m.group(1)
            break

    by_conf = {c: sum(1 for card in cards if card["conf"] == c) for c in CONFIDENCE}
    unknown = sum(1 for card in cards if card["conf"] not in CONFIDENCE)
    builds = sum(1 for card in cards if card["build"] == "yes")
    build_known = any(card["build"] for card in cards)

    # Sections first, so the checklist count is known for the header tiles.
    sections_html, toc = [], []
    findings_done = False
    for sec in doc["sections"]:
        sid = slug(sec["title"] or "findings")
        ctx.section = sid
        has_cards = any(kind == "card" for kind, _ in sec["items"])
        tasks_before = len(ctx.tasks)
        parts, run = [], []

        def flush_cards():
            if run:
                parts.append(f'<div class="cards">{"".join(run)}</div>')
                run.clear()

        toolbar_done = False
        for kind, item in sec["items"]:
            if kind == "card":
                if has_cards and not findings_done and not toolbar_done:
                    toolbar_done = True
                    parts.append(render_toolbar(L, by_conf, unknown, build_known))
                run.append(render_card(item, L, ctx))
                continue
            flush_cards()
            if doc.get("overview") and item is doc["overview"]["block"]:
                parts.append(render_overview(doc, L))
            else:
                parts.append(render_blocks([item], ctx, heading_ids=slug))
        flush_cards()
        if toolbar_done:
            parts.append(f'<p class="empty" id="empty" hidden>{esc(L["none_match"])}</p>')
            findings_done = True
        n_tasks = len(ctx.tasks) - tasks_before
        heading_extra, pill = "", ""
        if has_cards:
            pill = f'<span class="pill">{sum(1 for k, _ in sec["items"] if k == "card")}</span>'
            heading_extra = pill
        if n_tasks:
            heading_extra += (f'<span class="progress" data-progress="{sid}"><progress max="{n_tasks}" value="0">'
                              f'</progress><span data-progress-text></span></span>'
                              f'<button class="btn" type="button" data-reset>{esc(L["reset"])}</button>')
            pill = f'<span class="pill" data-progress="{sid}"><span data-progress-text data-short></span></span>'
        attr = " data-findings" if toolbar_done else ""
        head = f'<h2>{render_inline(sec["title"])}{heading_extra}</h2>' if sec["title"] else ""
        sections_html.append(f'<section id="{sid}"{attr}>{head}{"".join(parts)}</section>')
        if sec["title"]:
            toc.append(f'<li><a href="#{sid}"><span>{render_inline(sec["title"], links=False)}</span>{pill}</a></li>')

    if not cards:
        sections_html.insert(0, f'<section id="no-findings"><p class="empty">{esc(L["no_findings"])}</p></section>')

    tiles = [f'<button class="tile k-all" type="button" data-filter="all"><span class="n">{len(cards)}</span>'
             f'<span class="l"><span>{esc(L["tile_findings"])}</span></span></button>']
    for c in CONFIDENCE:
        tiles.append(f'<button class="tile k-{CONF_CLASS[c]}" type="button" data-filter="{c}" title="{esc(L[c])}">'
                     f'<span class="n">{by_conf[c]}</span><span class="l"><span class="dot"></span>'
                     f'<span>{c}</span></span></button>')
    if build_known:
        tiles.append(f'<button class="tile k-nb" type="button" data-filter="build"><span class="n">{builds}</span>'
                     f'<span class="l"><span class="dot"></span><span>{esc(L["tile_build"])}</span></span></button>')
    if ctx.tasks:
        done = sum(1 for _, checked in ctx.tasks if checked)
        tiles.append(f'<div class="tile k-nb" data-progress=""><span class="n" data-progress-text data-short>'
                     f'{done}/{len(ctx.tasks)}</span><span class="l"><span>{esc(L["tile_checklist"])}</span>'
                     f'</span></div>')
    dist = ""
    if cards:
        x, rects = 0.0, []
        for c, cls in [(c, CONF_CLASS[c]) for c in CONFIDENCE] + [("", "none")]:
            n = by_conf[c] if c else unknown
            if n:
                w = 100.0 * n / len(cards)
                rects.append(f'<rect class="{cls}" x="{x:.3f}" y="0" width="{w:.3f}" height="1"/>')
                x += w
        dist = (f'<div class="dist"><svg viewBox="0 0 100 1" preserveAspectRatio="none" aria-hidden="true">'
                f'{"".join(rects)}</svg></div>')

    meta = render_blocks(doc["meta"], ctx)
    labels_js = json.dumps(L, ensure_ascii=False).replace("</", "<\\/")
    script = JS.replace("__LABELS__", labels_js)
    style = CSS
    csp = (f"default-src 'none'; style-src {csp_hash(style)}; script-src {csp_hash(script)}; img-src data:; "
           f"base-uri 'none'; form-action 'none'")
    key = "aspf:" + hashlib.sha1(title_text.encode("utf-8")).hexdigest()[:16]
    footer = esc(L["footer"].format(source=source, version=version).replace("  ", " "))
    toc_html = (f'<nav class="toc" aria-label="{esc(L["contents"])}"><p class="toc-title">{esc(L["contents"])}</p>'
                f'<ol>{"".join(toc)}</ol></nav>') if toc else '<nav class="toc"></nav>'
    return f"""<!doctype html>
<html lang="{esc(lang)}" data-key="{esc(key)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<meta name="referrer" content="no-referrer">
<meta name="generator" content="app-store-review-preflight {esc(version)}">
<title>{esc(title_text)}</title>
<style>{style}</style>
</head>
<body>
<header class="masthead"><div class="wrap">
<div class="topbar"><div class="eyebrow">{ICON_CHECK}<span>{esc(L["eyebrow"])}</span></div>
<div class="actions"><button class="btn" type="button" id="print">{esc(L["print"])}</button>
<button class="btn" type="button" id="theme">{esc(L["theme"])}</button></div></div>
<h1>{render_inline(shown_title)}</h1>
<div class="meta">{meta}</div>
<div class="tiles">{"".join(tiles)}</div>
{dist}
</div></header>
<div class="wrap layout">
{toc_html}
<main>
{"".join(sections_html)}
</main>
</div>
<footer><div class="wrap">{footer}</div></footer>
<script>{script}</script>
</body>
</html>
"""


def render_toolbar(L, by_conf, unknown, build_known):
    chips = [f'<button class="chip k-all" type="button" data-filter="all">{esc(L["filter_all"])}</button>']
    for c in CONFIDENCE:
        if by_conf[c]:
            chips.append(f'<button class="chip k-{CONF_CLASS[c]}" type="button" data-filter="{c}" '
                         f'title="{esc(L[c])}"><span class="dot"></span>{c}</button>')
    if build_known:
        chips.append(f'<button class="chip k-nb" type="button" data-filter="build"><span class="dot"></span>'
                     f'{esc(L["filter_build"])}</button>')
    return (f'<div class="toolbar"><label class="search">{ICON_SEARCH}<input id="search" type="search" '
            f'placeholder="{esc(L["search"])} ( / )" aria-label="{esc(L["search"])}" autocomplete="off"></label>'
            f'<div class="chips">{"".join(chips)}</div>'
            f'<button class="btn" type="button" id="expand">{esc(L["expand"])}</button>'
            f'<button class="btn" type="button" id="collapse">{esc(L["collapse"])}</button></div>'
            f'<p class="count" id="count"></p>')


def labels_for(lang, overrides=None):
    base = dict(LABELS["en"])
    base.update(LABELS.get((lang or "en").split("-")[0].lower(), {}))
    if overrides:
        base.update({k: str(v) for k, v in overrides.items() if k in base})
    return base


def render(markdown, lang="en", source="APP_REVIEW_PREFLIGHT.md", labels=None, version=None):
    """Return (html, doc) for a markdown report."""
    doc = parse_report(markdown)
    page = render_page(doc, labels_for(lang, labels), lang or "en", source,
                       version if version is not None else skill_version())
    return page, doc


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render the preflight report as an interactive HTML page")
    parser.add_argument("report", help="the markdown report, e.g. APP_REVIEW_PREFLIGHT.md")
    parser.add_argument("--out", help="output path (default: the report path with .html)")
    parser.add_argument("--lang", default="en", help="language of the page's controls: en, tr, or any code with --labels")
    parser.add_argument("--labels", help="JSON object that overrides the page's control labels")
    args = parser.parse_args(argv)

    with open(args.report, encoding="utf-8") as fh:
        markdown = fh.read()
    overrides = None
    if args.labels:
        with open(args.labels, encoding="utf-8") as fh:
            overrides = json.load(fh)
        if not isinstance(overrides, dict):
            parser.error("--labels must hold a JSON object")
    out = args.out or os.path.splitext(args.report)[0] + ".html"
    page, doc = render(markdown, lang=args.lang, source=os.path.basename(args.report), labels=overrides)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)

    cards = doc["cards"]
    counts = ", ".join(f"{sum(1 for c in cards if c['conf'] == k)} {k}" for k in CONFIDENCE)
    builds = sum(1 for c in cards if c["build"] == "yes")
    print(f"Wrote {out}: {len(cards)} findings ({counts}); {builds} need a new build.")
    missing = [c["n"] for c in cards if c["conf"] not in CONFIDENCE]
    if missing:
        print(f"warning: findings {missing} have no confidence level (validator-certain, review-risk, judgment-call).",
              file=sys.stderr)
    ov = doc.get("overview")
    if cards and (not ov or any(t is None for t in ov["mapping"]) or len(ov["mapping"]) != len(cards)):
        print("warning: the findings table does not map one row to each `### [guideline] title` finding; "
              "filters use what each finding says.", file=sys.stderr)
    if cards and not any(c["build"] for c in cards):
        print("warning: no finding says whether it needs a new build (findings table, last column).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
