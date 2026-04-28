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
