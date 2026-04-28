# Password Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a B-tier password gate on the public GitHub Pages deployment of the private `dms-dashboard` repo: every HTML page hides its body until the correct shared password is entered, search engines are blocked via `noindex` + `robots.txt`, and the gate can be re-applied to new HTML files by running one Python script.

**Architecture:** Three new repo-root artifacts (`password-gate.js`, `robots.txt`, `scripts/inject_password_gate.py`) + three injected lines into every existing HTML file's `<head>`. The script tag uses a **depth-aware relative path** (`../../password-gate.js`) so the gate works both locally (`python -m http.server`) and on the deployed `https://tamimiemran.github.io/dms-dashboard/` site without baking the URL prefix in.

**Tech Stack:** Vanilla JavaScript (`crypto.subtle` + `localStorage` + DOM `createElement`, no build step), Python 3.11 stdlib (`pathlib`, `re`, `argparse`, `unittest`) for the injector, Playwright MCP for the smoke test.

**Spec:** `docs/specs/2026-04-28-password-gate-design.md` (commit b87afaf)

---

## File Structure

| Path | New / Modified | Responsibility |
|---|---|---|
| `password-gate.js` | NEW | Self-contained gate: hash check, localStorage, password prompt UI built via `createElement`, reload on success. ~70 LOC. |
| `robots.txt` | NEW | `User-agent: *` / `Disallow: /` — three lines, blocks search-engine crawl. |
| `scripts/inject_password_gate.py` | NEW | Walks all `*.html`, idempotently inserts the three `<head>` lines (noindex meta, hide-body style, gate script with depth-relative path). Argparse CLI matching `audit_links.py` / `rewrite_paths.py` style. |
| `scripts/test_inject_password_gate.py` | NEW | `unittest` tests for the injector. Run with `python -m unittest scripts.test_inject_password_gate -v`. |
| `**/*.html` (37 files) | MODIFIED | Three new lines in `<head>` after `<meta charset>` (or after `<head>` if no charset). |

**Why depth-aware relative paths instead of `/dms-dashboard/password-gate.js`:** `rewrite_paths.py` already uses this pattern for `assets/` references. Matching it keeps the gate working when the repo is served locally for testing and when deployed to Pages, without hardcoding the project-site prefix.

**Why `createElement` instead of `innerHTML`:** the prompt's HTML is fully static today (no user input interpolated), but a future edit could easily change that and introduce XSS. Building DOM nodes via `createElement` removes the footgun entirely. Trade-off is ~20 extra lines of code, which is fine.

---

## Task 1: Create `password-gate.js`

**Files:**
- Create: `M:/DMS/reports/dashboard/password-gate.js`

This file is small enough that we write it whole and verify with a syntax check. End-to-end behavior is validated in Task 6.

- [ ] **Step 1.1: Write the gate script**

Create `password-gate.js` with this exact content:

```javascript
/**
 * Dashboard password gate -- B-tier protection.
 *
 * Behavior:
 *   - On every HTML page load, check localStorage for a stored hash.
 *   - If the stored hash matches the embedded HASH constant, remove the
 *     hide-body style and let the page render normally.
 *   - Otherwise, replace <body> content with a centered password prompt.
 *     On correct password, store the hash and reload.
 *
 * The hide-body <style> is injected by the HTML's <head> (not by this
 * script) so the body is hidden BEFORE this script even fetches -- no
 * flash of original content.
 *
 * DOM is built via createElement (not innerHTML) so that any future edit
 * adding user-controlled text can't accidentally introduce XSS.
 *
 * Limitations (B-tier, see spec):
 *   - The full HTML is still in the HTTP response; curl bypasses the gate.
 *   - DevTools "delete the gate" bypass is accepted.
 *   - Asset URLs (assets/**) are not gated.
 */
(function () {
  'use strict';

  // SHA-256 of the shared password. Rotate by recomputing this hash and
  // committing the new value -- old localStorage entries auto-invalidate.
  const HASH = '07775f56063609b25c480986c5d51fc9127fc17197d1d7100b205e134a3bf8e0';
  const STORAGE_KEY = 'dms-dashboard-unlocked';
  const HIDE_STYLE_ID = 'dms-gate-hide';

  const hide = document.getElementById(HIDE_STYLE_ID);

  // Already unlocked -- reveal body and exit.
  if (localStorage.getItem(STORAGE_KEY) === HASH) {
    if (hide) hide.remove();
    return;
  }

  async function sha256(text) {
    const buf = await crypto.subtle.digest(
      'SHA-256',
      new TextEncoder().encode(text)
    );
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  }

  function buildPrompt() {
    const overlay = document.createElement('div');
    overlay.id = 'dms-gate';
    overlay.style.cssText =
      'position:fixed;inset:0;display:flex;align-items:center;' +
      'justify-content:center;background:#F8F9FB;' +
      'font-family:system-ui,-apple-system,sans-serif';

    const form = document.createElement('form');
    form.id = 'dms-gate-form';
    form.style.cssText =
      'display:flex;flex-direction:column;gap:12px;padding:32px;' +
      'background:#fff;border:1px solid #E0E2E8;border-radius:10px;' +
      'min-width:280px;box-shadow:0 4px 12px rgba(0,0,0,0.04)';

    const label = document.createElement('label');
    label.htmlFor = 'dms-gate-pw';
    label.textContent = 'Password';
    label.style.cssText = 'color:#5A5E6E;font-size:14px';

    const input = document.createElement('input');
    input.id = 'dms-gate-pw';
    input.type = 'password';
    input.autofocus = true;
    input.autocomplete = 'off';
    input.style.cssText =
      'padding:10px 12px;border:1px solid #E0E2E8;border-radius:6px;' +
      'font-size:14px;font-family:inherit;outline:none';

    const button = document.createElement('button');
    button.type = 'submit';
    button.textContent = 'Unlock';
    button.style.cssText =
      'padding:10px 12px;background:#0E9A7E;color:#fff;border:none;' +
      'border-radius:6px;font-size:14px;cursor:pointer;font-family:inherit';

    const msg = document.createElement('div');
    msg.id = 'dms-gate-msg';
    msg.style.cssText = 'color:#D9453E;font-size:13px;min-height:18px';

    form.appendChild(label);
    form.appendChild(input);
    form.appendChild(button);
    form.appendChild(msg);
    overlay.appendChild(form);

    return { overlay, form, input, msg };
  }

  function showPrompt() {
    // Clear body, then mount the prompt.
    while (document.body.firstChild) {
      document.body.removeChild(document.body.firstChild);
    }
    const { overlay, form, input, msg } = buildPrompt();
    document.body.appendChild(overlay);

    // Body now contains only the prompt; safe to remove the hide style.
    if (hide) hide.remove();

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const hash = await sha256(input.value);
      if (hash === HASH) {
        localStorage.setItem(STORAGE_KEY, HASH);
        location.reload();
      } else {
        msg.textContent = 'Wrong password.';
        input.value = '';
        input.focus();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', showPrompt);
  } else {
    showPrompt();
  }
})();
```

- [ ] **Step 1.2: Syntax check**

Run: `node --check M:/DMS/reports/dashboard/password-gate.js`
Expected: no output (success). Any output = syntax error.

- [ ] **Step 1.3: Commit**

```bash
cd M:/DMS/reports/dashboard
git add password-gate.js
git commit -m "$(cat <<'EOF'
feat(gate): add password-gate.js for B-tier dashboard auth

SHA-256 hash check via crypto.subtle, localStorage persistence,
prompt UI built via createElement (no innerHTML). Embeds hash
constant; rotate by recomputing and committing the new hash --
old sessions auto-invalidate.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Create `robots.txt`

**Files:**
- Create: `M:/DMS/reports/dashboard/robots.txt`

- [ ] **Step 2.1: Write the file**

Create `robots.txt` with exactly this content (two lines + final newline, no other content):

```
User-agent: *
Disallow: /
```

- [ ] **Step 2.2: Commit**

```bash
cd M:/DMS/reports/dashboard
git add robots.txt
git commit -m "$(cat <<'EOF'
feat(gate): add robots.txt to block search-engine indexing

Polite supplement to the per-page noindex meta tag added by the gate
injector. Disallows crawl of the entire deployed site.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Write failing tests for the injector

**Files:**
- Create: `M:/DMS/reports/dashboard/scripts/test_inject_password_gate.py`

We're using stdlib `unittest` (no `pytest` setup in this repo) with `tempfile.TemporaryDirectory` for isolated HTML fixtures.

- [ ] **Step 3.1: Write the test file**

Create `scripts/test_inject_password_gate.py` with this exact content:

```python
"""Tests for inject_password_gate.py.

Run with:
    python -m unittest scripts.test_inject_password_gate -v

(Run from the dashboard repo root.)
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.inject_password_gate import inject_into_file, inject_into_tree


HTML_WITH_CHARSET = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Test</title>
</head>
<body>
  <h1>Hello</h1>
</body>
</html>
"""

HTML_NO_CHARSET = """\
<!DOCTYPE html>
<html>
<head>
  <title>Test</title>
</head>
<body>x</body>
</html>
"""

HTML_NO_HEAD = """\
<!DOCTYPE html>
<html><body>nope</body></html>
"""


class InjectIntoFileTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _write(self, rel: str, content: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_inserts_after_charset_meta_at_root(self) -> None:
        path = self._write("index.html", HTML_WITH_CHARSET)
        changed = inject_into_file(path, root=self.root)
        self.assertTrue(changed)
        result = path.read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex,nofollow"', result)
        self.assertIn('id="dms-gate-hide"', result)
        self.assertIn('src="password-gate.js"', result)
        # Order: charset before robots before style before script.
        self.assertLess(result.index("charset"), result.index("robots"))
        self.assertLess(result.index("robots"), result.index("dms-gate-hide"))
        self.assertLess(result.index("dms-gate-hide"), result.index("password-gate.js"))

    def test_falls_back_to_head_open_when_no_charset(self) -> None:
        path = self._write("page.html", HTML_NO_CHARSET)
        changed = inject_into_file(path, root=self.root)
        self.assertTrue(changed)
        result = path.read_text(encoding="utf-8")
        self.assertIn('name="robots"', result)
        # Inserted between <head> and <title>.
        self.assertLess(result.index("<head>"), result.index("robots"))
        self.assertLess(result.index("robots"), result.index("<title>"))

    def test_idempotent(self) -> None:
        path = self._write("index.html", HTML_WITH_CHARSET)
        first = inject_into_file(path, root=self.root)
        second = inject_into_file(path, root=self.root)
        self.assertTrue(first)
        self.assertFalse(second, "Second run must be a no-op")
        result = path.read_text(encoding="utf-8")
        self.assertEqual(result.count("password-gate.js"), 1)
        self.assertEqual(result.count("dms-gate-hide"), 1)
        self.assertEqual(result.count('name="robots"'), 1)

    def test_depth_aware_relative_path(self) -> None:
        root_path = self._write("index.html", HTML_WITH_CHARSET)
        nested = self._write("reports/hikvision/audit.html", HTML_WITH_CHARSET)
        inject_into_file(root_path, root=self.root)
        inject_into_file(nested, root=self.root)
        self.assertIn(
            'src="password-gate.js"',
            root_path.read_text(encoding="utf-8"),
        )
        self.assertIn(
            'src="../../password-gate.js"',
            nested.read_text(encoding="utf-8"),
        )

    def test_raises_on_missing_head(self) -> None:
        path = self._write("broken.html", HTML_NO_HEAD)
        with self.assertRaises(ValueError):
            inject_into_file(path, root=self.root)


class InjectIntoTreeTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _write(self, rel: str, content: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_walks_tree_and_reports_counts(self) -> None:
        self._write("index.html", HTML_WITH_CHARSET)
        self._write("reports/a.html", HTML_WITH_CHARSET)
        self._write("drafts/b.html", HTML_WITH_CHARSET)
        self._write("notes.txt", "ignored")  # non-HTML
        inserted, skipped = inject_into_tree(self.root)
        self.assertEqual(inserted, 3)
        self.assertEqual(skipped, 0)

    def test_second_run_skips_all(self) -> None:
        self._write("index.html", HTML_WITH_CHARSET)
        self._write("reports/a.html", HTML_WITH_CHARSET)
        inject_into_tree(self.root)
        inserted, skipped = inject_into_tree(self.root)
        self.assertEqual(inserted, 0)
        self.assertEqual(skipped, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3.2: Run tests to verify they fail (red phase)**

Run:
```bash
cd M:/DMS/reports/dashboard
python -m unittest scripts.test_inject_password_gate -v
```
Expected: `ModuleNotFoundError: No module named 'scripts.inject_password_gate'`. The implementation doesn't exist yet; this confirms the tests are wired up to import the right thing.

---

## Task 4: Implement the injector to make tests pass

**Files:**
- Create: `M:/DMS/reports/dashboard/scripts/inject_password_gate.py`

- [ ] **Step 4.1: Write the implementation**

Create `scripts/inject_password_gate.py` with this exact content:

```python
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
```

- [ ] **Step 4.2: Run tests to verify they pass (green phase)**

Run:
```bash
cd M:/DMS/reports/dashboard
python -m unittest scripts.test_inject_password_gate -v
```
Expected: 7 tests, all pass. (5 in `InjectIntoFileTests`, 2 in `InjectIntoTreeTests`.)

- [ ] **Step 4.3: Commit**

```bash
cd M:/DMS/reports/dashboard
git add scripts/inject_password_gate.py scripts/test_inject_password_gate.py
git commit -m "$(cat <<'EOF'
feat(gate): add idempotent HTML injector + tests

scripts/inject_password_gate.py walks *.html, inserts noindex meta,
hide-body style, and gate script tag into <head> with depth-aware
relative path. Idempotent via dms-gate-hide marker. Dry-run mode
shows planned changes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Apply the gate to all existing HTML files

**Files:**
- Modify: every `*.html` file in the repo (37 files per pre-task count). One diff per file: three new lines in `<head>`.

- [ ] **Step 5.1: Dry-run to preview changes**

Run:
```bash
cd M:/DMS/reports/dashboard
python scripts/inject_password_gate.py --dry-run
```
Expected: prints `insert <relative-path>` for ~37 files, then `Dry run: would insert into 37 file(s), 0 already injected.` (count may differ slightly if files were added/removed since spec was written -- verify the listed files are all dashboard HTML, no surprises).

- [ ] **Step 5.2: Apply the injection**

Run:
```bash
cd M:/DMS/reports/dashboard
python scripts/inject_password_gate.py
```
Expected: `Inserted gate into 37 file(s); 0 already had it.`

- [ ] **Step 5.3: Verify idempotency**

Run:
```bash
cd M:/DMS/reports/dashboard
python scripts/inject_password_gate.py
```
Expected: `Inserted gate into 0 file(s); 37 already had it.`

- [ ] **Step 5.4: Spot-check a root and a nested file**

Run:
```bash
head -10 M:/DMS/reports/dashboard/index.html
head -10 M:/DMS/reports/dashboard/reports/hikvision/audit.html
```
Expected for root: gate script src is `password-gate.js` (no prefix).
Expected for nested (depth 2): gate script src is `../../password-gate.js`.
Both should show the noindex meta and the dms-gate-hide style immediately after the existing `<meta charset>` line.

- [ ] **Step 5.5: Verify the link audit still passes**

Run:
```bash
cd M:/DMS/reports/dashboard
python scripts/audit_links.py
```
Expected: exit code 0 ("clean"). The injected `<script src="password-gate.js">` should be detected by `audit_links.py`'s `src=` regex and resolved against the (now-existing) `password-gate.js` file at the correct depth-relative location.

If `audit_links.py` reports `password-gate.js` as broken for nested files, that means it doesn't resolve depth-relative paths correctly -- investigate before proceeding (it likely already does, since it does the same for `assets/`).

- [ ] **Step 5.6: Commit**

```bash
cd M:/DMS/reports/dashboard
git add -A '*.html'
git commit -m "$(cat <<'EOF'
feat(gate): inject password gate into all HTML files

Applied scripts/inject_password_gate.py across the repo. Every served
HTML now hides body until the password is entered correctly. Three
new lines per file's <head>: noindex meta, hide-body style, gate
script with depth-aware relative path.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Local smoke test via Playwright MCP

**Files:** none modified. This task is verification only.

- [ ] **Step 6.1: Start a local server**

Run in a background shell:
```bash
cd M:/DMS/reports/dashboard
python -m http.server 8765
```

- [ ] **Step 6.2: Smoke-test the root page (locked → unlock → reload)**

Use Playwright MCP. Sequence:

1. Clear browser storage to start fresh: `mcp__plugin_playwright_playwright__browser_navigate` to `http://localhost:8765/`, then `mcp__plugin_playwright_playwright__browser_evaluate` with `() => localStorage.clear()`.
2. `mcp__plugin_playwright_playwright__browser_navigate` to `http://localhost:8765/`.
3. `mcp__plugin_playwright_playwright__browser_snapshot`. Expect: a centered form with a "Password" label and an "Unlock" button. The original dashboard content (e.g., "DMS Presentations" title) should NOT be visible.
4. Try a wrong password: `mcp__plugin_playwright_playwright__browser_type` "wrong-pw" into the input, click Unlock. `mcp__plugin_playwright_playwright__browser_snapshot`. Expect: input cleared, "Wrong password." message visible, original content still hidden.
5. Try the correct password (`@inno$dpt_pwd083619`): type it, click Unlock. Page reloads. `mcp__plugin_playwright_playwright__browser_snapshot`. Expect: original dashboard content now visible (e.g., "DMS Presentations" header), no password form.
6. Reload the page (`mcp__plugin_playwright_playwright__browser_navigate` to the same URL): expect content visible without re-prompting (localStorage persisted).

- [ ] **Step 6.3: Smoke-test a deep page**

Without clearing storage:
1. `mcp__plugin_playwright_playwright__browser_navigate` to `http://localhost:8765/reports/hikvision/audit.html`.
2. `mcp__plugin_playwright_playwright__browser_snapshot`. Expect: original report content visible (gate inactive because localStorage already has the unlock).
3. Confirm `<script src="../../password-gate.js">` resolved successfully -- `mcp__plugin_playwright_playwright__browser_console_messages` should NOT show a 404 for `password-gate.js`.

Then verify a deep page locks fresh sessions correctly:
1. `mcp__plugin_playwright_playwright__browser_evaluate` with `() => localStorage.clear()`.
2. `mcp__plugin_playwright_playwright__browser_navigate` to `http://localhost:8765/reports/hikvision/audit.html` (deep entry, no index.html visit first).
3. `mcp__plugin_playwright_playwright__browser_snapshot`. Expect: password prompt, NOT the report content.

- [ ] **Step 6.4: Stop the local server**

Kill the background `python -m http.server` shell.

- [ ] **Step 6.5: Note any failures**

If any of the above fails, do NOT proceed to Task 7. Common failures and where to look:
- Body content visible at first load → hide-body `<style>` not injected, or selector mismatch in JS. Inspect a file with `head -10`.
- `password-gate.js` 404 in console → depth-relative path computed incorrectly in the injector. Inspect `_gate_block(depth)` output for the failing file.
- Wrong password accepted → hash mismatch in `password-gate.js`. Re-verify `python -c 'import hashlib; print(hashlib.sha256(b"@inno$dpt_pwd083619").hexdigest())'` matches the embedded constant.
- localStorage doesn't persist → likely a private/incognito browsing mode in the Playwright session. Try a non-incognito context.

---

## Task 7: Push to GitHub Pages and verify live

**Files:** none modified. Final deployment + verification.

- [ ] **Step 7.1: Push**

```bash
cd M:/DMS/reports/dashboard
git push origin master
```

- [ ] **Step 7.2: Wait for Pages to redeploy**

Pages on `legacy` build type usually deploys within ~30-60 seconds of push. Check status:
```bash
gh api repos/tamimiEmran/dms-dashboard/pages/builds/latest --jq '.status,.created_at,.commit'
```
Expected: `status` becomes `"built"` with `commit` matching the push HEAD. If it stays `"queued"` or `"building"` for more than 2 min, something's wrong -- check `gh api repos/tamimiEmran/dms-dashboard/pages/builds/latest --jq '.error'`.

- [ ] **Step 7.3: Verify the live deployment in Playwright**

1. `mcp__plugin_playwright_playwright__browser_navigate` to `https://tamimiemran.github.io/dms-dashboard/`.
2. `mcp__plugin_playwright_playwright__browser_evaluate` with `() => localStorage.clear()` (in case stale unlock from a prior browse).
3. Reload and `mcp__plugin_playwright_playwright__browser_snapshot`. Expect: password prompt.
4. Type the password, click Unlock. Expect: page reloads, content visible.
5. Navigate to `https://tamimiemran.github.io/dms-dashboard/reports/hikvision/audit.html`. Expect: content visible (already unlocked).
6. `mcp__plugin_playwright_playwright__browser_console_messages`. Expect: no 404 for `password-gate.js`.

- [ ] **Step 7.4: Verify robots.txt**

```bash
curl -s https://tamimiemran.github.io/dms-dashboard/robots.txt
```
Expected output:
```
User-agent: *
Disallow: /
```

- [ ] **Step 7.5: Verify noindex meta**

```bash
curl -s https://tamimiemran.github.io/dms-dashboard/ | grep -i 'name="robots"'
```
Expected: one line containing `<meta name="robots" content="noindex,nofollow">`.

- [ ] **Step 7.6: Done**

If all verifications pass, the gate is live. Share the password with stakeholders out-of-band (Signal, in-person, password manager -- anything but email or chat that's persistently logged).

If anything failed at this stage, the safest rollback is `git revert <commit-range>` and re-push -- the gate's three injected `<head>` lines per file are isolated and revertable as a clean diff.

---

## Self-review

**Spec coverage** -- every spec section maps to a task:
- Spec §3.1 `password-gate.js` → Task 1.
- Spec §3.2 `<head>` injection → Task 5 (run injector). Injector itself in Task 4.
- Spec §3.3 `robots.txt` → Task 2.
- Spec §3.4 `inject_password_gate.py` → Task 4 (and tests in Task 3).
- Spec §4 page-load sequence → verified end-to-end in Tasks 6 + 7.
- Spec §6 decisions → embedded in Task 1 (storage = hash, algo = SHA-256) and Task 4 (gate-everything, depth-relative path).
- Spec §7 acceptance criteria -- directly checked by Tasks 5 (idempotency), 6 (local browser flow), 7 (live URL + robots.txt).
- Spec §5 limitations are accept-list, not work -- no task needed.
- Spec §8 future work explicitly deferred -- no task needed.

**Placeholder scan:** none. Every step has either a concrete command, concrete code, or a specific MCP tool call.

**Type/name consistency:** marker constant `GATE_MARKER` matches the `id="dms-gate-hide"` attribute used in both the JS (HIDE_STYLE_ID) and the injected HTML. `STORAGE_KEY` only appears in the JS -- single source of truth. Function names `inject_into_file` / `inject_into_tree` / `_dry_run` consistent between Task 3 (test imports) and Task 4 (implementation).

**One small inconsistency to note:** Task 5's expected `audit_links.py` exit code assumes that script handles relative paths correctly. If it doesn't, the worst case is a noisy report -- not a blocker. The plan flags this in Step 5.5 and tells the reader what to do.
