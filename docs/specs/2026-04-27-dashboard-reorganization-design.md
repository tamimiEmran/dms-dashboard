# Dashboard Reorganization — Design

**Date:** 2026-04-27
**Repo:** `tamimiEmran/dms-dashboard` (deployed via GitHub Pages)
**Status:** approved, ready to plan

---

## 1. Problem

The dashboard root is a flat collection of ~25 HTML files mixing finished
reports, live presentation decks, active drafts, and superseded artifacts.
Finding things is slow, and the root keeps accreting new WIP files. We want
a cleaner structure without breaking the live `index.html` and its
references.

## 2. Goals & non-goals

**In scope:**
- Group root files into a hybrid structure (date-anchored for presentations,
  topic-anchored for reusable reports).
- Move active WIP into a top-level `drafts/` folder, still web-accessible.
- Move superseded files into the existing `archive/` folder.
- Rewrite every `href`/`src`/`data` path inside moved files so the live
  `index.html` and all in-page links continue to work.
- Fix three pre-existing hardcoded `file:///M:/...` links (already broken on
  the live site) as a free win during the rewrite phase.
- Un-gitignore `archive/` so its contents are part of the live deploy.

**Explicitly out of scope:**
- HTTP redirects from old root paths to new ones. External bookmarks to
  specific reports (e.g., a previously-shared `/hikvision_audit.html` link)
  will 404 after the migration. Confirmed acceptable: only `index.html` and
  its referenced links must keep working.
- Restructuring `assets/` (already date-organized).
- Restructuring `onboarding/` (already topic-organized with internal
  navigation).
- Renaming files inside `drafts/` — they move in their current form.

## 3. Target directory structure

```
dashboard/
├── index.html                         # entry point, stays at root
├── STYLE.md                           # stays at root (prose updated)
├── .gitignore  .gitattributes
│
├── presentations/                     # date-anchored decks
│   ├── 2026-04-21-hikvision-eval/
│   │   └── summary.html               # was summary_21Apr26.html
│   ├── 2026-04-14-efficientnet/
│   │   └── deck.html                  # was 14_Apr.html
│   ├── 2026-04-07-raqeeb/
│   │   ├── deck.html                  # was raqeeb_audit_pres.html
│   │   └── raqeeb_data.js             # loaded by deck.html (same folder)
│   └── 2026-03-31-strategy/
│       └── deck.html                  # was index2.html
│
├── reports/                           # topic-anchored, reusable
│   ├── hikvision/
│   │   ├── audit.html                 # was hikvision_audit.html
│   │   ├── rulebased.html             # was hikvision_rulebased.html
│   │   ├── leaderboard.html           # was hikvision_leaderboard_benchmark.html
│   │   └── leaderboard_summary.html   # was hikvision_leaderboard_benchmark_summary.html
│   ├── raqeeb/
│   │   └── audit.html                 # was raqeeb_audit.html
│   └── dms/
│       ├── workflow.html
│       ├── comparison_21Apr26.html    # was dms_comparison_21Apr26.html
│       ├── compression.html           # was compression_pipeline_21Apr26.html
│       └── iot_architecture.svg       # was dms_iot_architecture.svg
│
├── drafts/                            # active WIP, web-accessible at /drafts/<file>
│   ├── pareto_design_review.html
│   ├── pareto_design_review_v2.html
│   ├── pareto_slopegraph.html
│   ├── face_crop_fallback_26Apr26.html
│   ├── face_crop_fallback_rescored_26Apr26.html
│   ├── face_detector_bench_26Apr26.html
│   ├── occupancy_counts_26Apr26.html
│   └── hikvision_leaderboard_benchmark_26Apr26.html
│
├── archive/                           # superseded; un-gitignored as part of this work
│   ├── preprocessing_pipeline.html    # moved in
│   ├── raqeeb_audit_backup.html       # moved in
│   └── (existing archive contents become tracked)
│
├── onboarding/                        # untouched
└── assets/                            # untouched
```

## 4. The rewrite rule

For every moved file, all relative paths inside it get **prefixed with `../`
per level of depth added**:

| New depth | Prefix |
|---|---|
| 1 (e.g., `drafts/`) | `../` |
| 2 (e.g., `presentations/2026-04-21-hikvision-eval/`) | `../../` |

Five categories of `href`/`src`/`data` get rewritten in each moved file:

| # | Pattern | Example (depth 2) |
|---|---|---|
| 1 | `← Home` link | `href="index.html"` → `href="../../index.html"` |
| 2 | Asset references | `src="assets/21April26/foo.png"` → `src="../../assets/21April26/foo.png"` |
| 3 | Sibling-file links | `href="hikvision_audit.html"` → `href="../../reports/hikvision/audit.html"` |
| 4 | Same-folder JS | `<script src="raqeeb_data.js">` (unchanged — data.js moves with the deck) |
| 5 | Hardcoded `file:///` | `href="file:///M:/DMS/reports/dashboard/hikvision_rulebased.html"` → `href="../../reports/hikvision/rulebased.html"` (also fixes the broken live link) |

URL-encoded paths (`%20`) and anchor fragments (`#audit`) are preserved
unchanged through the prefix operation.

## 5. `index.html` rewiring

`index.html` itself stays at root. Its dynamic registries get path updates:

**`RESOURCES` array:**
- `'hikvision_audit.html'` → `'reports/hikvision/audit.html'`
- `'raqeeb_audit.html'` → `'reports/raqeeb/audit.html'`
- `'workflow.html'` → `'reports/dms/workflow.html'`
- `'onboarding/index.html'` (unchanged)
- lightbox entry (unchanged)

**`PRESENTATIONS` array:**
- `hikvision_deep_dive.file`: `'summary_21Apr26.html#audit'` →
  `'presentations/2026-04-21-hikvision-eval/summary.html#audit'`
- `hikvision_deep_dive.materials[]` files → `reports/hikvision/...` and
  `reports/dms/...` per the file mapping.
- `efficientnet_eval.file`: `'14_Apr.html'` →
  `'presentations/2026-04-14-efficientnet/deck.html'`
- `raqeeb_audit_pres.file`: `'raqeeb_audit_pres.html'` →
  `'presentations/2026-04-07-raqeeb/deck.html'`
- `dms_strategy.file`: `'index2.html'` →
  `'presentations/2026-03-31-strategy/deck.html'`

**Lightbox SVG references** (lines 936, 943):
- `dms_iot_architecture.svg` → `reports/dms/iot_architecture.svg`

The hero image `assets/general/Slide1.jpg` is unchanged.

## 6. Phased commit plan

Each phase is one commit. The full set lands in a single `git push` so the
live site never sees an intermediate broken state.

| # | Phase | Commit message |
|---|---|---|
| 1 | Un-gitignore `archive/` | `chore: un-gitignore archive folder` |
| 2 | Move `reports/hikvision/*` + rewrite hrefs | `refactor(reports): group hikvision reports under reports/hikvision/` |
| 3 | Move `reports/raqeeb/*` + rewrite hrefs | `refactor(reports): group raqeeb audit under reports/raqeeb/` |
| 4 | Move `reports/dms/*` + rewrite hrefs | `refactor(reports): group dms reports under reports/dms/` |
| 5 | Move `presentations/*` + rewrite hrefs | `refactor(presentations): group decks by date` |
| 6 | Move drafts (no href rewrites — orphans) | `refactor(drafts): collect WIP into drafts/` |
| 7 | Archive superseded files | `chore(archive): retire preprocessing_pipeline + raqeeb_audit_backup` |
| 8 | Rewire `index.html` registries + fix `file:///` links + update `STYLE.md` prose | `refactor(dashboard): rewire index.html for new layout` |

Use `git mv` for every move so history is preserved.

## 7. Verification

**Pre-push (local):**
1. Open `index.html` in a browser.
2. Click every card on the home page → must load (no 404).
3. From each loaded page, click `← Home` → must return to dashboard.
4. Spot-check the 21 April deck: iframe to `leaderboard_summary.html` and
   the three "→ full report" external-tab links.
5. Open the IoT architecture lightbox → SVG must render.

**Automated link audit:** a small script that walks every `.html` in the new
tree, extracts every `href`/`src`/`data` attribute that isn't an external
URL, resolves each relative to its containing file, and flags any that
don't exist on disk. Run before push.

**Post-push:** repeat steps 1–5 against the live `.io` URL.

## 8. Rollback

- **Single bad phase** → `git revert <commit>`, push.
- **Whole migration regrettable** → `git revert <first-reorg-commit>..HEAD`,
  push. Live site returns to pre-reorg state.
- **Catastrophic** → `git reset --hard <pre-migration-sha>` + force-push,
  only with explicit user approval.

## 9. Risks & known edge cases

- **`hikvision_leaderboard_benchmark_summary.html` is not actually
  superseded** — it's loaded as an `<iframe>` inside the 21 April deck.
  Routed to `reports/hikvision/leaderboard_summary.html`, not archive.
- **`archive/` is currently gitignored** — un-gitignoring sweeps in 6
  existing untracked files (`dms_model_landscape.html`, `hardware-slide.html`,
  `index.html`, `index2_backup.html`, `index2-v2.html`, `index3.html`).
  Confirmed acceptable.
- **Three hardcoded `file:///M:/...` links** in the leaderboard files are
  already broken on the live site. Fixed during phase 2.
- **`STYLE.md`** mentions several old filenames in prose — updated in phase
  8. Low-risk because it's documentation.
- **External bookmarks** to old root paths will 404. Accepted tradeoff.
