"""Per-file path rewriter for the dashboard reorganization.

Given a moved HTML file and the depth it now sits at, prepends "../" *
depth to every standard relative path (index.html, assets/...). Optional
-r flags apply additional literal substring replacements (used for
cross-file link rewrites that aren't covered by the standard rules).

Usage:
    python scripts/rewrite_paths.py FILE DEPTH [-r OLD NEW]...

Examples:
    # File moved 2 levels deep, no extra cross-links:
    python scripts/rewrite_paths.py reports/hikvision/audit.html 2

    # File with cross-links to other moved files:
    python scripts/rewrite_paths.py presentations/2026-04-21-hikvision-eval/summary.html 2 \\
        -r 'href="hikvision_audit.html"' 'href="../../reports/hikvision/audit.html"'

The replacements are exact substring matches (no regex). Order matters:
standard rules apply first, then -r rules in the order given.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def build_standard_replacements(depth: int) -> list[tuple[str, str]]:
    prefix = "../" * depth
    return [
        ('href="index.html"', f'href="{prefix}index.html"'),
        ("href='index.html'", f"href='{prefix}index.html'"),
        ('href="assets/', f'href="{prefix}assets/'),
        ('src="assets/', f'src="{prefix}assets/'),
        ('data="assets/', f'data="{prefix}assets/'),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("depth", type=int)
    parser.add_argument(
        "-r",
        nargs=2,
        action="append",
        metavar=("OLD", "NEW"),
        default=[],
        help="Extra literal replacement (repeatable)",
    )
    args = parser.parse_args()

    if not args.file.exists():
        raise SystemExit(f"file not found: {args.file}")

    pairs = build_standard_replacements(args.depth) + [tuple(p) for p in args.r]
    content = args.file.read_text(encoding="utf-8")
    changes = 0
    for old, new in pairs:
        if old in content:
            content = content.replace(old, new)
            changes += 1
    args.file.write_text(content, encoding="utf-8")
    print(f"{args.file}: applied {changes} of {len(pairs)} substitutions")


if __name__ == "__main__":
    main()
