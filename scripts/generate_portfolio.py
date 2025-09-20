#!/usr/bin/env python3
"""Generate the giving portfolio table and fetch favicons where possible."""
import csv
import html
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "giving_updated.csv"
FAVICON_DIR = ROOT / "favicon"
OUTPUT_PATH = ROOT / "portfolio_table.html"
FAVICON_DIR.mkdir(exist_ok=True)

@dataclass
class IconCandidate:
    url: str
    rel_priority: int
    size_score: int

class IconLinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.candidates: List[IconCandidate] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "link":
            return
        attr_map = {k.lower(): v for k, v in attrs}
        rel = attr_map.get("rel", "").lower()
        href = attr_map.get("href")
        if not href or "icon" not in rel:
            return
        rel_priority = 1
        if "apple-touch-icon" in rel:
            rel_priority = 2
        sizes_attr = attr_map.get("sizes", "").lower()
        size_score = 0
        if "" == sizes_attr or sizes_attr == "any":
            size_score = 48
        else:
            for part in sizes_attr.split():
                if "x" in part:
                    try:
                        width = int(part.split("x")[0])
                        size_score = max(size_score, width)
                    except ValueError:
                        continue
        absolute_url = urllib.parse.urljoin(self.base_url, href)
        self.candidates.append(IconCandidate(absolute_url, rel_priority, size_score))

def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

def download(url: str, dest: Path) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = resp.read()
            if not data:
                return False
            content_type = resp.headers.get("Content-Type", "")
            suffix = ""
            if "/" in content_type:
                subtype = content_type.split("/")[-1].split(";")[0]
                if subtype in {"png", "jpeg", "jpg", "gif", "ico", "svg+xml", "webp"}:
                    if subtype == "svg+xml":
                        suffix = ".svg"
                    elif subtype == "jpeg":
                        suffix = ".jpg"
                    else:
                        suffix = f".{subtype}"
            parsed = urllib.parse.urlparse(url)
            if not suffix:
                suffix = Path(parsed.path).suffix or ".ico"
            dest_path = dest.with_suffix(suffix)
            dest_path.write_bytes(data)
            return True
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def fetch_favicon(base_url: str, slug: str) -> Optional[str]:
    if not base_url:
        return None
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url
    parsed = urllib.parse.urlparse(base_url)
    base_root = f"{parsed.scheme}://{parsed.netloc}/"
    target = FAVICON_DIR / slug
    if any(target.with_suffix(ext).exists() for ext in [".png", ".jpg", ".jpeg", ".ico", ".svg", ".webp"]):
        for ext in [".png", ".jpg", ".jpeg", ".ico", ".svg", ".webp"]:
            path = target.with_suffix(ext)
            if path.exists():
                return path.name
    try:
        with urllib.request.urlopen(base_root, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        html = ""
    candidates: List[IconCandidate] = []
    if html:
        parser = IconLinkParser(base_root)
        parser.feed(html)
        candidates = sorted(
            parser.candidates,
            key=lambda c: (-c.rel_priority, -c.size_score)
        )
    tried = set()
    for candidate in candidates:
        if candidate.url in tried:
            continue
        tried.add(candidate.url)
        if download(candidate.url, target):
            return Path(candidate.url).suffix and target.with_suffix(Path(candidate.url).suffix).name
    fallback = urllib.parse.urljoin(base_root, "/favicon.ico")
    if download(fallback, target):
        return target.with_suffix(".ico").name
    return None


def main():
    if not CSV_PATH.exists():
        print(f"CSV not found: {CSV_PATH}", file=sys.stderr)
        sys.exit(1)
    lines = [line for line in CSV_PATH.read_text().splitlines() if line.strip()]
    rows = [r for r in csv.DictReader(lines) if r.get("Org")]
    order_map = {"Local": 0, "National": 1, "Global": 2}
    rows = [r for idx, r in sorted(enumerate(rows), key=lambda item: (order_map.get(item[1]['Class'], 99), item[0]))]

    table_rows = []
    for row in rows:
        org = row['Org']
        slug = slugify(org)
        website = (row.get('Website') or '').strip()
        icon_filename = fetch_favicon(website, slug)
        if icon_filename:
            icon_html = f"<img class=\"favicon\" src=\"favicon/{icon_filename}\" alt=\"\" aria-hidden=\"true\">"
        else:
            icon_html = "<span class=\"favicon-fallback\" aria-hidden=\"true\">🌐</span>"
        name = html.escape(org)
        href = ''
        if website:
            href = website if website.startswith(('http://','https://')) else 'https://' + website
        if href:
            name_html = f"<a class=\"org-name\" href=\"{html.escape(href)}\" target=\"_blank\" rel=\"noreferrer\">{name}</a>"
        else:
            name_html = f"<span class=\"org-name\">{name}</span>"
        summary = (row.get('Summary') or 'Details coming soon.').strip() or 'Details coming soon.'
        summary_html = html.escape(summary)
        reason_key = (row.get('Reason') or '').strip().lower()
        scope = (row.get('Class') or '').strip()
        scope_emoji, scope_label = {
            'Local': ('🏘️', 'Local Giving'),
            'National': ('🇺🇸', 'National Giving'),
            'Global': ('🌍', 'Global Giving')
        }.get(scope, ('❓', 'Undesignated'))
        cat_emoji, cat_label = {
            'education': ('🎓', 'Education'),
            'environment': ('🌿', 'Environment'),
            'homeless': ('🏠', 'Housing & Stability'),
            'church': ('🙏', 'Faith & Community'),
            'food': ('🍎', 'Food Security'),
            'justice': ('⚖️', 'Justice'),
            'health': ('🩺', 'Health')
        }.get(reason_key, ('❓', row.get('Reason') or 'Focus pending'))
        why = (row.get('Why') or '').strip() or 'Personal note coming soon while we document this grant.'
        cn = (row.get('CharityNavigator') or '').strip()
        gs = (row.get('GuideStar') or '').strip()

        card_content = (
            f"<div class=\"org-card\">{icon_html}<div class=\"org-card-content\"><div>{name_html}</div><span class=\"summary\">{summary_html}</span></div></div>"
        )

        cn_html = (
            f"<a class=\"badge-link\" href=\"{html.escape(cn)}\" target=\"_blank\" rel=\"noreferrer\"><img class=\"badge-image\" src=\"assets/cn.png\" alt=\"Charity Navigator logo\"></a>"
            if cn
            else '<span class="badge-empty" aria-hidden="true"></span>'
        )
        gs_html = (
            f"<a class=\"badge-link\" href=\"{html.escape(gs)}\" target=\"_blank\" rel=\"noreferrer\"><img class=\"badge-image\" src=\"assets/gs.jpeg\" alt=\"GuideStar logo\"></a>"
            if gs
            else '<span class="badge-empty" aria-hidden="true"></span>'
        )

        table_rows.append(
            "    <tr>\n"
            f"      <td class=\"org\">{card_content}</td>\n"
            f"      <td class=\"scope\"><span class=\"emoji\" title=\"{html.escape(scope_label)}\">{scope_emoji}</span></td>\n"
            f"      <td class=\"category\"><span class=\"emoji\" title=\"{html.escape(cat_label)}\">{cat_emoji}</span></td>\n"
            f"      <td class=\"ratings\">{cn_html}{gs_html}</td>\n"
            f"      <td class=\"notes\"><span class=\"why\">{html.escape(why)}</span></td>\n"
            "    </tr>"
        )

    OUTPUT_PATH.write_text('\n'.join(table_rows) + '\n')
    print(f"Wrote {len(table_rows)} rows to {OUTPUT_PATH}")

if __name__ == '__main__':
    main()
