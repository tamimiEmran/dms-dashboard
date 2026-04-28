"""Idempotent injector for the dashboard password gate.

Walks the dashboard repo for *.html files and inserts three lines into
each <head>:

    <meta name="robots" content="noindex,nofollow">
    <style id="dms-gate-hide">body{display:none!important}</style>
    <script src="<depth-relative>/password-gate.js"></script>

The script src is depth-aware so the gate works both when serving the
repo locally (e.g. `python -m http.server`) and when deployed to GitHub
Pages at https://tamimiemran.github.io/dms-dashboard/.

Idempotent: files already containing `id="dms-gate-hide"` are skipped.

Usage:
    python scripts/inject_password_gate.py            # mutate in place
    python scripts/inject_password_gate.py --dry-run  # print what would change
    python scripts/inject_password_gate.py --root .   # explicit root

Exit codes:
    0 -- done (or dry-run printed)
    1 -- at least one file lacked a <head> tag (re-raised)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Marker we look for to detect "already injected" -- chosen because it's
# unique to our gate and stable across password rotations (which only
# change the hash inside password-gate.js, not the injected HTML).
GATE_MARKER = 'id="dms-gate-hide"'

# Walk-skip directories. We do NOT skip archive/ or drafts/ -- the spec
# says everything served gets gated.
SKIP_DIRS = {".git", ".github", ".wrangler", ".playwright-mcp", "node_modules"}

CHARSET_RE = re.compile(r"<meta\s+charset[^>]*>", re.IGNORECASE)
HEAD_OPEN_RE = re.compile(r"<head[^>]*>", re.IGNORECASE)


def _gate_block(depth: int) -> str:
    """Return the three-line block to inject, with depth-aware src path."""
    prefix = "../" * depth
    return (
        '\n  <meta name="robots" content="noindex,nofollow">'
        '\n  <style id="dms-gate-hide">body{display:none!important}</style>'
        f'\n  <script src="{prefix}password-gate.js"></script>'
    )


def inject_into_file(path: Path, *, root: Path) -> bool:
    """Inject the gate into a single HTML file.

    Returns:
        True if the file was modified, False if it was already injected.

    Raises:
        ValueError: if the file has no <head> tag at all.
    """
    text = path.read_text(encoding="utf-8")
    if GATE_MARKER in text:
        return False

    depth = len(path.relative_to(root).parts) - 1
    block = _gate_block(depth)

    # Prefer inserting after <meta charset>, fall back to right after <head>.
    charset = CHARSET_RE.search(text)
    if charset:
        insert_at = charset.end()
    else:
        head = HEAD_OPEN_RE.search(text)
        if not head:
            raise ValueError(f"{path}: no <head> tag found")
        insert_at = head.end()

    new_text = text[:insert_at] + block + text[insert_at:]
    path.write_text(new_text, encoding="utf-8")
    return True


def inject_into_tree(root: Path) -> tuple[int, int]:
    """Walk root for *.html files, inject into each.

    Returns:
        (inserted_count, skipped_count). Files raising ValueError are
        re-raised after being printed so the user sees them all.
    """
    inserted = 0
    skipped = 0
    errors: list[str] = []

    for path in sorted(root.rglob("*.html")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            if inject_into_file(path, root=root):
                inserted += 1
            else:
                skipped += 1
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        raise ValueError(f"{len(errors)} file(s) lacked a <head> tag")

    return inserted, skipped


def _dry_run(root: Path) -> tuple[int, int]:
    """Like inject_into_tree but only reports -- no writes."""
    would_insert = 0
    already = 0
    for path in sorted(root.rglob("*.html")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root)
        if GATE_MARKER in text:
            already += 1
            print(f"  skip   {rel}")
        else:
            would_insert += 1
            print(f"  insert {rel}")
    return would_insert, already


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Dashboard repo root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing.",
    )
    args = parser.parse_args()

    root: Path = args.root.resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 1

    if args.dry_run:
        would, already = _dry_run(root)
        print(
            f"\nDry run: would insert into {would} file(s), "
            f"{already} already injected."
        )
        return 0

    try:
        inserted, skipped = inject_into_tree(root)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Inserted gate into {inserted} file(s); {skipped} already had it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
