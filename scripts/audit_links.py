"""Broken-link audit for the dashboard.

Walks every .html file under the dashboard root and reports every
href/src/data attribute whose target does not exist on disk.

Scope rules:
- Skips external URLs (http, https, mailto, data:, file:///, javascript:)
- Skips pure anchor links (#foo)
- Skips files inside dotted directories (.git, .wrangler, etc.)
- Skips the archive/ directory (historical content, broken links there
  are tolerated as the cost of being archived)
- Strips <script>, <style>, <pre>, <code> blocks before scanning so we
  don't match attribute-like patterns inside JS template literals or
  example code

Usage:
    python scripts/audit_links.py            # run from dashboard root
    python scripts/audit_links.py --root .   # explicit root

Exit codes: 0 = clean, 1 = broken links found.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ATTR_PATTERN = re.compile(r'''(?:href|src|data)\s*=\s*["']([^"']+)["']''')

# Tags whose content is not real markup (scripts, styles, code samples).
# Stripped before attribute-pattern matching to avoid false positives.
OPAQUE_TAGS = ("script", "style", "pre", "code")

EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "data:", "file:///", "javascript:")

SKIP_DIRS = {"archive"}


def is_external(url: str) -> bool:
    return url.startswith(EXTERNAL_PREFIXES)


def strip_query_and_anchor(url: str) -> str:
    return url.split("#", 1)[0].split("?", 1)[0]


def strip_opaque_blocks(content: str) -> str:
    """Remove <script>...</script>, <style>...</style>, <pre>...</pre>,
    <code>...</code> blocks. Non-greedy match so adjacent blocks aren't
    merged. Case-insensitive; DOTALL so blocks may span lines.
    """
    for tag in OPAQUE_TAGS:
        content = re.sub(
            rf"<{tag}\b[^>]*>.*?</{tag}>",
            "",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )
    return content


def audit_file(html_path: Path, dashboard_root: Path) -> list[str]:
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    scrubbed = strip_opaque_blocks(raw)
    errors: list[str] = []
    for match in ATTR_PATTERN.finditer(scrubbed):
        url = match.group(1).strip()
        if not url or url.startswith("#") or is_external(url):
            continue
        target_path = strip_query_and_anchor(url)
        if not target_path:
            continue
        decoded = unquote(target_path)
        target = (html_path.parent / decoded).resolve()
        if not target.exists():
            # Line number is from the scrubbed content; close enough for
            # error reporting (still in the right ballpark).
            line = scrubbed[: match.start()].count("\n") + 1
            rel = html_path.relative_to(dashboard_root)
            errors.append(f"{rel}:~{line}: broken -> {url}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    root = args.root.resolve()
    all_errors: list[str] = []
    for html in sorted(root.rglob("*.html")):
        rel_parts = html.relative_to(root).parts
        if any(p.startswith(".") for p in rel_parts):
            continue
        if any(p in SKIP_DIRS for p in rel_parts):
            continue
        all_errors.extend(audit_file(html, root))

    if all_errors:
        print(f"BROKEN LINKS FOUND ({len(all_errors)}):")
        for err in all_errors:
            print(f"  {err}")
        return 1
    print("OK: all relative links resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
