# Dashboard Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the flat dashboard root into a hybrid `presentations/` + `reports/` + `drafts/` + `archive/` structure without breaking the live `index.html` and any links it references.

**Architecture:** Move 24 HTML files (plus one `.svg` and one `.js`) into topic-or-date subfolders via `git mv`. For each moved file, prefix every relative `href`/`src`/`data` path with `../` per level of depth added; rewrite cross-file links to point to the moved siblings. A small Python script (`scripts/rewrite_paths.py`) handles the mechanical path rewrites consistently. A second script (`scripts/audit_links.py`) walks every HTML file and reports broken local links — used to verify the migration before pushing.

**Tech Stack:** Python 3 stdlib (the migration scripts), `git mv`, GitHub Pages.

**Spec:** `docs/specs/2026-04-27-dashboard-reorganization-design.md`

---

## File Structure

**New scripts** (created in this plan):
- `scripts/audit_links.py` — broken-link auditor (test harness)
- `scripts/rewrite_paths.py` — per-file path rewriter

**New directories** (created via `mkdir -p` per phase):
- `presentations/2026-04-21-hikvision-eval/`
- `presentations/2026-04-14-efficientnet/`
- `presentations/2026-04-07-raqeeb/`
- `presentations/2026-03-31-strategy/`
- `reports/hikvision/`
- `reports/raqeeb/`
- `reports/dms/`
- `drafts/`

**Files moved** (full mapping in spec section 3). 24 HTML files + 1 SVG + 1 JS.

**Files modified in place:**
- `index.html` — JS registries (`RESOURCES`, `PRESENTATIONS`) and lightbox SVG references
- `STYLE.md` — prose mentioning old filenames
- `.gitignore` — un-ignore `archive/`

---

## Working assumptions

- Branch: `master` (matches existing pattern). All commits go directly to master; the migration's intermediate commits do not deploy until the final `git push`.
- Python interpreter: any Python ≥ 3.9 on PATH (scripts use stdlib only).
- Run all commands from `M:/DMS/reports/dashboard/`.
- No worktree — the dashboard repo is small and changes are bounded; rollback is `git revert`.

---

## Task 1: Create the link audit script

**Files:**
- Create: `M:/DMS/reports/dashboard/scripts/audit_links.py`

- [ ] **Step 1.1 — Create scripts directory**

```bash
mkdir -p scripts
```

- [ ] **Step 1.2 — Write the audit script**

Write to `scripts/audit_links.py`:

```python
"""Broken-link audit for the dashboard.

Walks every .html file under the dashboard root and reports every
href/src/data attribute whose target does not exist on disk. Skips
external URLs (http, https, mailto, data:, file:///), pure anchor links,
and files inside dotted directories (.git, .wrangler, etc.).

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

EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "data:", "file:///", "javascript:")


def is_external(url: str) -> bool:
    return url.startswith(EXTERNAL_PREFIXES)


def strip_query_and_anchor(url: str) -> str:
    return url.split("#", 1)[0].split("?", 1)[0]


def audit_file(html_path: Path, dashboard_root: Path) -> list[str]:
    content = html_path.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    for match in ATTR_PATTERN.finditer(content):
        url = match.group(1).strip()
        if not url or url.startswith("#") or is_external(url):
            continue
        target_path = strip_query_and_anchor(url)
        if not target_path:
            continue
        decoded = unquote(target_path)
        target = (html_path.parent / decoded).resolve()
        if not target.exists():
            line = content[: match.start()].count("\n") + 1
            rel = html_path.relative_to(dashboard_root)
            errors.append(f"{rel}:{line}: broken -> {url}")
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
```

- [ ] **Step 1.3 — Run baseline audit**

```bash
python scripts/audit_links.py
```

Expected output: `OK: all relative links resolve.` (exit 0). If the audit reports broken links *before* migration, those are pre-existing issues — capture the output and stop; the user must decide whether to fix them first or proceed.

Note: the three `file:///M:/...` hardcoded links are classified as *external* by this auditor (`file:///` prefix), so they will not appear here. They are addressed explicitly in Task 5.

- [ ] **Step 1.4 — Commit**

```bash
git add scripts/audit_links.py
git commit -m "$(cat <<'EOF'
chore(dashboard): add link audit script

Walks every .html under the dashboard root and reports any href/src/data
target that doesn't exist on disk. Used to verify the upcoming directory
reorganization doesn't break in-page links.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Create the path-rewrite helper

**Files:**
- Create: `M:/DMS/reports/dashboard/scripts/rewrite_paths.py`

- [ ] **Step 2.1 — Write the script**

Write to `scripts/rewrite_paths.py`:

```python
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

    pairs = build_standard_replacements(args.depth) + list(map(tuple, args.r))
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
```

- [ ] **Step 2.2 — Smoke-test the script (no commit needed for this step)**

Run with a non-existent file to confirm the error path works:

```bash
python scripts/rewrite_paths.py /tmp/does_not_exist.html 2
```

Expected: `SystemExit: file not found: ...` (exit 1).

- [ ] **Step 2.3 — Commit**

```bash
git add scripts/rewrite_paths.py
git commit -m "$(cat <<'EOF'
chore(dashboard): add per-file path rewriter

Prepends ../ per depth level to standard relative paths (index.html,
assets/) and applies any extra literal substring replacements via -r
flags. Used during the reorganization to keep moved files' links valid.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Un-gitignore archive/

**Files:**
- Modify: `M:/DMS/reports/dashboard/.gitignore`

- [ ] **Step 3.1 — Remove `archive/` from .gitignore**

Use the Edit tool:

```
old_string: archive/
new_string: (empty — delete the line)
```

After this edit, `.gitignore` should contain only `.wrangler/` and any blank lines that were already there.

- [ ] **Step 3.2 — Verify the change**

```bash
git check-ignore -v archive/dms_model_landscape.html
```

Expected: empty output (file is no longer ignored). Exit code may be 1 — that's normal for "not ignored".

```bash
git status --short
```

Expected: `.gitignore` shown as modified, plus 6 archive files now showing as untracked (`?? archive/dms_model_landscape.html`, etc.).

- [ ] **Step 3.3 — Stage existing archive contents**

```bash
git add .gitignore archive/
```

- [ ] **Step 3.4 — Commit**

```bash
git commit -m "$(cat <<'EOF'
chore(dashboard): un-gitignore archive folder

archive/ was previously gitignored, so its 6 HTML files lived only on
the maintainer's laptop. Tracking them now so the live deploy carries
the historical decks/landing pages — needed before incoming reorg
phases route superseded files into archive/.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Move `reports/raqeeb/*`

**Files:**
- Move: `raqeeb_audit.html` → `reports/raqeeb/audit.html`

(Doing the smallest topic group first to validate the workflow.)

- [ ] **Step 4.1 — Create destination directory**

```bash
mkdir -p reports/raqeeb
```

- [ ] **Step 4.2 — Move the file**

```bash
git mv raqeeb_audit.html reports/raqeeb/audit.html
```

- [ ] **Step 4.3 — Rewrite paths in the moved file**

```bash
python scripts/rewrite_paths.py reports/raqeeb/audit.html 2
```

Expected output: `reports/raqeeb/audit.html: applied N of M substitutions` where N ≥ 1 (at minimum the `← Home` link).

- [ ] **Step 4.4 — Commit**

The `git mv` already staged the rename; staging the destination picks up the path-rewrite modifications too.

```bash
git add reports/raqeeb/
git commit -m "$(cat <<'EOF'
refactor(reports): group raqeeb audit under reports/raqeeb/

Relocates raqeeb_audit.html → reports/raqeeb/audit.html and rewrites
its in-page hrefs (Home link + asset references) for the new depth.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Move `reports/hikvision/*` (and fix `file:///` links)

**Files:**
- Move: `hikvision_audit.html` → `reports/hikvision/audit.html`
- Move: `hikvision_rulebased.html` → `reports/hikvision/rulebased.html`
- Move: `hikvision_leaderboard_benchmark.html` → `reports/hikvision/leaderboard.html`
- Move: `hikvision_leaderboard_benchmark_summary.html` → `reports/hikvision/leaderboard_summary.html`

- [ ] **Step 5.1 — Create destination directory**

```bash
mkdir -p reports/hikvision
```

- [ ] **Step 5.2 — Move all four files**

```bash
git mv hikvision_audit.html reports/hikvision/audit.html
git mv hikvision_rulebased.html reports/hikvision/rulebased.html
git mv hikvision_leaderboard_benchmark.html reports/hikvision/leaderboard.html
git mv hikvision_leaderboard_benchmark_summary.html reports/hikvision/leaderboard_summary.html
```

- [ ] **Step 5.3 — Rewrite paths: `audit.html` and `rulebased.html` (no extra cross-links)**

```bash
python scripts/rewrite_paths.py reports/hikvision/audit.html 2
python scripts/rewrite_paths.py reports/hikvision/rulebased.html 2
```

- [ ] **Step 5.4 — Rewrite paths: `leaderboard.html` (fix `file:///` cross-link)**

The leaderboard file links to the rulebased file via a hardcoded `file:///` path. Now that they're siblings in the same folder, use a same-folder relative link:

```bash
python scripts/rewrite_paths.py reports/hikvision/leaderboard.html 2 \
  -r 'href="file:///M:/DMS/reports/dashboard/hikvision_rulebased.html"' 'href="rulebased.html"'
```

- [ ] **Step 5.5 — Rewrite paths: `leaderboard_summary.html` (fix `file:///` cross-link)**

```bash
python scripts/rewrite_paths.py reports/hikvision/leaderboard_summary.html 2 \
  -r 'href="file:///M:/DMS/reports/dashboard/hikvision_rulebased.html"' 'href="rulebased.html"'
```

- [ ] **Step 5.6 — Verify the `file:///` links are gone**

```bash
grep -rn 'file:///M:/' reports/hikvision/
```

Expected: no output (exit code 1 from grep is fine — means no matches).

- [ ] **Step 5.7 — Commit**

```bash
git add reports/hikvision/
git commit -m "$(cat <<'EOF'
refactor(reports): group hikvision reports under reports/hikvision/

Relocates the four hikvision-topic HTML files into reports/hikvision/
and rewrites their in-page hrefs for the new depth. Also fixes the
hardcoded file:///M:/... "Details ->" links in leaderboard.html and
leaderboard_summary.html — they now point at sibling rulebased.html.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Move `reports/dms/*`

**Files:**
- Move: `workflow.html` → `reports/dms/workflow.html`
- Move: `dms_comparison_21Apr26.html` → `reports/dms/comparison_21Apr26.html`
- Move: `compression_pipeline_21Apr26.html` → `reports/dms/compression.html`
- Move: `dms_iot_architecture.svg` → `reports/dms/iot_architecture.svg`

- [ ] **Step 6.1 — Create destination directory**

```bash
mkdir -p reports/dms
```

- [ ] **Step 6.2 — Move all four files**

```bash
git mv workflow.html reports/dms/workflow.html
git mv dms_comparison_21Apr26.html reports/dms/comparison_21Apr26.html
git mv compression_pipeline_21Apr26.html reports/dms/compression.html
git mv dms_iot_architecture.svg reports/dms/iot_architecture.svg
```

- [ ] **Step 6.3 — Rewrite paths in the three HTML files**

```bash
python scripts/rewrite_paths.py reports/dms/workflow.html 2
python scripts/rewrite_paths.py reports/dms/comparison_21Apr26.html 2
python scripts/rewrite_paths.py reports/dms/compression.html 2
```

(SVG file gets no path rewrite — it's referenced *by* others, doesn't reference anything itself.)

- [ ] **Step 6.4 — Commit**

```bash
git add reports/dms/
git commit -m "$(cat <<'EOF'
refactor(reports): group dms reports under reports/dms/

Relocates workflow.html, dms_comparison_21Apr26.html, the compression
pipeline page, and the IoT architecture SVG into reports/dms/. Path
rewrites applied to the three HTMLs; SVG is referenced-only.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Move `presentations/*`

**Files:**
- Move: `summary_21Apr26.html` → `presentations/2026-04-21-hikvision-eval/summary.html`
- Move: `14_Apr.html` → `presentations/2026-04-14-efficientnet/deck.html`
- Move: `raqeeb_audit_pres.html` → `presentations/2026-04-07-raqeeb/deck.html`
- Move: `raqeeb_data.js` → `presentations/2026-04-07-raqeeb/raqeeb_data.js`
- Move: `index2.html` → `presentations/2026-03-31-strategy/deck.html`

This is the most cross-link-heavy phase. The 21 April deck links to the hikvision and dms reports we just moved, and embeds `leaderboard_summary.html` in an iframe.

- [ ] **Step 7.1 — Create destination directories**

```bash
mkdir -p presentations/2026-04-21-hikvision-eval
mkdir -p presentations/2026-04-14-efficientnet
mkdir -p presentations/2026-04-07-raqeeb
mkdir -p presentations/2026-03-31-strategy
```

- [ ] **Step 7.2 — Move all five files**

```bash
git mv summary_21Apr26.html presentations/2026-04-21-hikvision-eval/summary.html
git mv 14_Apr.html presentations/2026-04-14-efficientnet/deck.html
git mv raqeeb_audit_pres.html presentations/2026-04-07-raqeeb/deck.html
git mv raqeeb_data.js presentations/2026-04-07-raqeeb/raqeeb_data.js
git mv index2.html presentations/2026-03-31-strategy/deck.html
```

- [ ] **Step 7.3 — Rewrite paths: 21 April hikvision-eval summary (heavy cross-links)**

```bash
python scripts/rewrite_paths.py presentations/2026-04-21-hikvision-eval/summary.html 2 \
  -r 'href="hikvision_audit.html"' 'href="../../reports/hikvision/audit.html"' \
  -r 'href="hikvision_rulebased.html"' 'href="../../reports/hikvision/rulebased.html"' \
  -r 'href="dms_comparison_21Apr26.html"' 'href="../../reports/dms/comparison_21Apr26.html"' \
  -r 'src="hikvision_leaderboard_benchmark_summary.html"' 'src="../../reports/hikvision/leaderboard_summary.html"'
```

The fourth `-r` covers the `<iframe src="hikvision_leaderboard_benchmark_summary.html">` on line 2631.

- [ ] **Step 7.4 — Rewrite paths: 14 April EfficientNet deck**

```bash
python scripts/rewrite_paths.py presentations/2026-04-14-efficientnet/deck.html 2
```

- [ ] **Step 7.5 — Rewrite paths: 7 April raqeeb deck**

The deck loads `raqeeb_data.js` from the same folder — no rewrite needed for that line, but the standard rules still apply for `← Home` and asset paths.

```bash
python scripts/rewrite_paths.py presentations/2026-04-07-raqeeb/deck.html 2
```

- [ ] **Step 7.6 — Rewrite paths: 31 March strategy deck**

```bash
python scripts/rewrite_paths.py presentations/2026-03-31-strategy/deck.html 2
```

- [ ] **Step 7.7 — Sanity check: verify the `raqeeb_data.js` reference still works**

```bash
grep -n 'raqeeb_data.js' presentations/2026-04-07-raqeeb/deck.html
```

Expected: a line containing `<script src="raqeeb_data.js"></script>` (unchanged — same-folder reference).

- [ ] **Step 7.8 — Commit**

```bash
git add presentations/
git commit -m "$(cat <<'EOF'
refactor(presentations): group decks by date

Relocates the four presentation decks into date-stamped folders under
presentations/, taking raqeeb_data.js along with the 7-Apr raqeeb deck
that loads it. Path rewrites applied to all four decks; the 21-Apr
summary additionally rewrites cross-links to reports/hikvision/* and
reports/dms/comparison_21Apr26.html plus the leaderboard-summary
iframe.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Move drafts

**Files:**
- Move 8 files from root → `drafts/`. Most have no cross-links (they're orphans), but one has a `file:///` hardcoded link to fix.

- [ ] **Step 8.1 — Create destination directory**

```bash
mkdir -p drafts
```

- [ ] **Step 8.2 — Move all eight files**

```bash
git mv pareto_design_review.html drafts/pareto_design_review.html
git mv pareto_design_review_v2.html drafts/pareto_design_review_v2.html
git mv pareto_slopegraph.html drafts/pareto_slopegraph.html
git mv face_crop_fallback_26Apr26.html drafts/face_crop_fallback_26Apr26.html
git mv face_crop_fallback_rescored_26Apr26.html drafts/face_crop_fallback_rescored_26Apr26.html
git mv face_detector_bench_26Apr26.html drafts/face_detector_bench_26Apr26.html
git mv occupancy_counts_26Apr26.html drafts/occupancy_counts_26Apr26.html
git mv hikvision_leaderboard_benchmark_26Apr26.html drafts/hikvision_leaderboard_benchmark_26Apr26.html
```

- [ ] **Step 8.3 — Rewrite paths in each draft (depth 1)**

The Pareto and slopegraph drafts only load external Plotly CDN — the script will report 0 substitutions, which is fine. The other drafts have `← Home` and/or asset references.

```bash
python scripts/rewrite_paths.py drafts/pareto_design_review.html 1
python scripts/rewrite_paths.py drafts/pareto_design_review_v2.html 1
python scripts/rewrite_paths.py drafts/pareto_slopegraph.html 1
python scripts/rewrite_paths.py drafts/face_crop_fallback_26Apr26.html 1
python scripts/rewrite_paths.py drafts/face_crop_fallback_rescored_26Apr26.html 1
python scripts/rewrite_paths.py drafts/face_detector_bench_26Apr26.html 1
python scripts/rewrite_paths.py drafts/occupancy_counts_26Apr26.html 1
```

For the leaderboard draft, also fix its `file:///` hardcoded link to point at the now-relocated rulebased.html:

```bash
python scripts/rewrite_paths.py drafts/hikvision_leaderboard_benchmark_26Apr26.html 1 \
  -r 'href="file:///M:/DMS/reports/dashboard/hikvision_rulebased.html"' 'href="../reports/hikvision/rulebased.html"'
```

- [ ] **Step 8.4 — Verify no `file:///M:/...` paths remain anywhere**

```bash
grep -rn 'file:///M:/' . --include='*.html' || echo "OK: no hardcoded file:/// paths"
```

Expected: `OK: no hardcoded file:/// paths`.

- [ ] **Step 8.5 — Commit**

```bash
git add drafts/
git commit -m "$(cat <<'EOF'
refactor(drafts): collect WIP into drafts/

Relocates eight active drafts (pareto v1/v2/slopegraph, three face
crop/detector pages, occupancy counts, and the in-flight leaderboard
benchmark) into drafts/. Standard depth-1 path rewrites applied; the
leaderboard draft's hardcoded file:///M:/... link also rewritten to
point at the new reports/hikvision/rulebased.html location.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Archive superseded files

**Files:**
- Move: `preprocessing_pipeline.html` → `archive/preprocessing_pipeline.html`
- Move: `raqeeb_audit_backup.html` → `archive/raqeeb_audit_backup.html`

These two are orphans (not referenced anywhere from `index.html` or any moved file). They get retired into `archive/` without path rewrites — anyone visiting the archived URLs gets the page as-is.

- [ ] **Step 9.1 — Move both files**

```bash
git mv preprocessing_pipeline.html archive/preprocessing_pipeline.html
git mv raqeeb_audit_backup.html archive/raqeeb_audit_backup.html
```

- [ ] **Step 9.2 — Commit**

```bash
git add archive/
git commit -m "$(cat <<'EOF'
chore(archive): retire preprocessing_pipeline + raqeeb_audit_backup

Both files are orphans — preprocessing_pipeline.html was an early
diagram superseded by content in raqeeb_audit_pres.html, and
raqeeb_audit_backup.html is an explicit backup of raqeeb_audit.html.
Moved into archive/ without path rewrites; their internal links may
or may not still resolve, which is acceptable for archived material.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Rewire `index.html` and update `STYLE.md`

**Files:**
- Modify: `M:/DMS/reports/dashboard/index.html`
- Modify: `M:/DMS/reports/dashboard/STYLE.md`

This is the final wiring — until this commit, `index.html` still references the old root paths and would 404 if pushed. After this commit, the migration is complete.

- [ ] **Step 10.1 — Rewire `RESOURCES` array entries in `index.html`**

Use the Edit tool, one substitution per `RESOURCES` entry:

Edit 1:
```
old_string:         file: 'hikvision_audit.html',
new_string:         file: 'reports/hikvision/audit.html',
```

Edit 2:
```
old_string:         file: 'raqeeb_audit.html',
new_string:         file: 'reports/raqeeb/audit.html',
```

Edit 3:
```
old_string:         file: 'workflow.html',
new_string:         file: 'reports/dms/workflow.html',
```

(The `'onboarding/index.html'` entry is unchanged.)

- [ ] **Step 10.2 — Rewire `PRESENTATIONS` array — `hikvision_deep_dive` (the WIP card)**

Edit 4 — the deck file:
```
old_string:         file: 'summary_21Apr26.html#audit',
new_string:         file: 'presentations/2026-04-21-hikvision-eval/summary.html#audit',
```

Edit 5 — material 1 (audit):
```
old_string:             file: 'hikvision_audit.html',
new_string:             file: 'reports/hikvision/audit.html',
```

Edit 6 — material 2 (rulebased):
```
old_string:             file: 'hikvision_rulebased.html',
new_string:             file: 'reports/hikvision/rulebased.html',
```

Edit 7 — material 3 (leaderboard):
```
old_string:             file: 'hikvision_leaderboard_benchmark.html',
new_string:             file: 'reports/hikvision/leaderboard.html',
```

Edit 8 — material 4 (in-vehicle comparison):
```
old_string:             file: 'dms_comparison_21Apr26.html',
new_string:             file: 'reports/dms/comparison_21Apr26.html',
```

Edit 9 — material 5 (compression):
```
old_string:             file: 'compression_pipeline_21Apr26.html',
new_string:             file: 'reports/dms/compression.html',
```

- [ ] **Step 10.3 — Rewire `PRESENTATIONS` past entries**

Edit 10 — efficientnet:
```
old_string:         file: '14_Apr.html',
new_string:         file: 'presentations/2026-04-14-efficientnet/deck.html',
```

Edit 11 — raqeeb_audit_pres:
```
old_string:         file: 'raqeeb_audit_pres.html',
new_string:         file: 'presentations/2026-04-07-raqeeb/deck.html',
```

Edit 12 — dms_strategy:
```
old_string:         file: 'index2.html',
new_string:         file: 'presentations/2026-03-31-strategy/deck.html',
```

- [ ] **Step 10.4 — Rewire the lightbox SVG references**

Edit 13:
```
old_string:       <a class="lightbox-open" href="dms_iot_architecture.svg" target="_blank" title="Open in new tab"><svg width="14"
new_string:       <a class="lightbox-open" href="reports/dms/iot_architecture.svg" target="_blank" title="Open in new tab"><svg width="14"
```

Edit 14:
```
old_string:       <object data="dms_iot_architecture.svg" type="image/svg+xml"
new_string:       <object data="reports/dms/iot_architecture.svg" type="image/svg+xml"
```

- [ ] **Step 10.5 — Update `STYLE.md` prose**

`STYLE.md` mentions the old filenames in prose (lines 4–6, 62–63, 75, 338). Update them to reference the new paths so the doc stays accurate:

Edit 15 (line 4–6 block — uses replace_all to fix all five filenames at once is risky because surrounding prose may differ; do them individually):

```
old_string: `hikvision_audit.html`
new_string: `reports/hikvision/audit.html`
replace_all: true
```

```
old_string: `hikvision_rulebased.html`
new_string: `reports/hikvision/rulebased.html`
replace_all: true
```

```
old_string: `hikvision_leaderboard_benchmark.html`
new_string: `reports/hikvision/leaderboard.html`
replace_all: true
```

```
old_string: `dms_comparison_21Apr26.html`
new_string: `reports/dms/comparison_21Apr26.html`
replace_all: true
```

```
old_string: `compression_pipeline_21Apr26.html`
new_string: `reports/dms/compression.html`
replace_all: true
```

For the snippet inside the styled `<a href="index.html">← Home</a>` example on line 75: leave it as-is (it's documentation of the *pattern* for root-level files; the pattern itself is still correct for the rare case of a future root-level file).

- [ ] **Step 10.6 — Run the link audit**

```bash
python scripts/audit_links.py
```

Expected: `OK: all relative links resolve.` (exit 0).

If any broken links are reported, do NOT proceed to commit. Investigate each, fix via Edit, re-run audit until clean.

- [ ] **Step 10.7 — Commit**

```bash
git add index.html STYLE.md
git commit -m "$(cat <<'EOF'
refactor(dashboard): rewire index.html for new layout

Updates RESOURCES and PRESENTATIONS file paths to point at the
relocated reports and decks, and rewrites the lightbox SVG references
to reports/dms/iot_architecture.svg. STYLE.md prose updated to
reference the new filenames so the style guide remains accurate.

This commit completes the dashboard reorganization. Link audit
(scripts/audit_links.py) reports clean.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Local browser smoke test

**Goal:** verify clickable behavior, lightbox, and iframe in a real browser before pushing to the live site.

- [ ] **Step 11.1 — Start a local HTTP server**

`file:///` works for most things, but iframes and certain CORS-sensitive features behave better over HTTP. Use Python's stdlib server:

```bash
python -m http.server 8765
```

Leave this running in a background shell. Then open `http://localhost:8765/index.html` in a browser.

- [ ] **Step 11.2 — Click every card on the home page**

For each card on the home page (4 presentations + 5 resources + the lightbox), click and confirm:
- Page loads (no 404).
- The page renders (not a blank/broken render).
- The `← Home` link returns to `http://localhost:8765/index.html`.

- [ ] **Step 11.3 — Verify the 21-April deck's special features**

Navigate to the 21 April deck (`http://localhost:8765/presentations/2026-04-21-hikvision-eval/summary.html`). Inside it:
- Confirm the embedded leaderboard iframe loads (not a "page not found" inside the iframe).
- Click each of the three `→ full report` links and confirm they open the right targets in new tabs.

- [ ] **Step 11.4 — Verify both lightboxes**

(a) On the home page, click the System Architecture image at the top — confirm the lightbox opens and shows `assets/general/Slide1.jpg`.

(b) Scroll to the Resources section at the bottom and click the "DMS IoT Architecture" card — confirm a separate lightbox opens and renders `reports/dms/iot_architecture.svg` (the SVG, not the JPG). This is the most likely place for a path bug, since the SVG path moved.

- [ ] **Step 11.5 — Stop the local server**

Ctrl+C in the background shell, or kill the process.

- [ ] **Step 11.6 — Sanity check: no untracked/unstaged changes**

```bash
git status
```

Expected: `nothing to commit, working tree clean`. (The reorg should be fully committed by now.)

---

## Task 12: Push to live site, verify

- [ ] **Step 12.1 — Push to origin**

```bash
git push origin master
```

GitHub Pages will rebuild the site from the new tree.

- [ ] **Step 12.2 — Wait for the deploy**

GitHub Pages typically deploys within 1–3 minutes. Check the deploy status at `https://github.com/tamimiEmran/dms-dashboard/actions` (or the repo's "Pages" settings tab).

- [ ] **Step 12.3 — Live smoke test**

Open the live `.io` URL in a browser. Repeat Task 11's clickable checks (steps 11.2 – 11.4) against the live site. Pay particular attention to the iframe in the 21 April deck since that path crosses two subdirectories.

- [ ] **Step 12.4 — If anything is broken on the live site**

Use the rollback strategy from the spec (section 8):
- If only one phase looks problematic, `git revert <bad-commit>` and re-push.
- If the whole reorg needs to be undone, `git revert <first-reorg-commit>..HEAD` and re-push.
- The pre-migration state is preserved at `a09ff32` (current HEAD before this work).

---

## Self-review (post-implementation)

After Task 12 completes:
- The dashboard root contains: `index.html`, `STYLE.md`, `.gitignore`, `.gitattributes`, plus the new directories (`presentations/`, `reports/`, `drafts/`, `archive/`, `assets/` (untouched), `onboarding/` (untouched), `scripts/`, `docs/`).
- No HTML, SVG, or JS files remain at the root other than `index.html`.
- `python scripts/audit_links.py` exits 0.
- No file contains `file:///M:/` (verified via `grep -rn 'file:///M:/' . --include='*.html'`).

If any of these checks fail, the migration is incomplete — debug before considering the work done.
