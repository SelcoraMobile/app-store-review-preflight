#!/usr/bin/env python3
"""Print App Review Guidelines sections by number from the text made by fetch_apple.py.

Usage:
  python3 -I guideline_sections.py GUIDELINES.txt list
  python3 -I guideline_sections.py GUIDELINES.txt show 1.2 2.1 3.1.2 [--children]
  python3 -I guideline_sections.py GUIDELINES.txt grep "third-party AI" [--context 1]

"show" prints a section from its numbered line up to the next numbered line. Lettered
parts come with it whether they are bullets inside the section (2.1 (a)/(b)) or numbered
lines of their own (3.1.2 -> 3.1.2(a), (b), (c)). --children also prints numbered
subsections (1.2 -> 1.2.1). Quote guideline wording from this output, not from memory.
"""
import argparse
import re
import sys

SECTION_RE = re.compile(r"^(?:• |## )?(\d+(?:\.\d+){0,2}(?:\([a-z]+\))?)(?:\.)?(?=\s|$)")


def load_sections(path):
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    sections = []  # (number, start, end)
    starts = []
    for idx, line in enumerate(lines):
        m = SECTION_RE.match(line.strip())
        if not m:
            continue
        number = m.group(1)
        # Top-level headings look like "## 1. Safety"; keep them as "1".
        if "." not in number and not line.strip().startswith("## "):
            continue
        starts.append((number, idx))
    for n, (number, idx) in enumerate(starts):
        end = starts[n + 1][1] if n + 1 < len(starts) else len(lines)
        sections.append((number, idx, end))
    return lines, sections


def footer_cut(lines, end):
    # Stop before the page footer if the last section runs into it.
    for i in range(end):
        if lines[i].startswith("Last Updated:"):
            return i
    return end


def cmd_list(lines, sections, _args):
    for number, start, _end in sections:
        title = re.sub(r"^(?:• |## )", "", lines[start]).strip()
        print(f"{number:10} {title[:90]}")


def cmd_show(lines, sections, args):
    wanted = args.numbers
    found = set()
    for number, start, end in sections:
        lettered = any(number.startswith(w + "(") for w in wanted)
        hit = number in wanted or lettered or (args.children and any(number.startswith(w + ".") for w in wanted))
        if not hit:
            continue
        found.add(number)
        stop = min(end, footer_cut(lines, len(lines)))
        print("\n".join(lines[start:stop]).rstrip())
        print()
    missing = [w for w in wanted if w not in found]
    if missing:
        print(f"[not found as numbered sections: {', '.join(missing)} — try `list` or `grep`]", file=sys.stderr)
        return 1
    return 0


def cmd_grep(lines, sections, args):
    pattern = re.compile(args.pattern, re.I)
    hits = 0
    for number, start, end in sections:
        for i in range(start, end):
            if pattern.search(lines[i]):
                lo, hi = max(start, i - args.context), min(end, i + args.context + 1)
                snippet = " ⏎ ".join(lines[lo:hi])
                print(f"[{number}] {snippet[:600]}")
                hits += 1
    if not hits:
        print("no matches")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="App Review Guidelines sections by number")
    parser.add_argument("file")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p = sub.add_parser("show")
    p.add_argument("numbers", nargs="+")
    p.add_argument("--children", action="store_true")
    p = sub.add_parser("grep")
    p.add_argument("pattern")
    p.add_argument("--context", type=int, default=0)
    args = parser.parse_args(argv)
    lines, sections = load_sections(args.file)
    if not sections:
        print("no numbered sections found; was this file made by fetch_apple.py guidelines?", file=sys.stderr)
        return 2
    return {"list": cmd_list, "show": cmd_show, "grep": cmd_grep}[args.cmd](lines, sections, args) or 0


if __name__ == "__main__":
    sys.exit(main())
