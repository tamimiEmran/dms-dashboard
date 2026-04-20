# Dashboard Style Guide

Reference for building new weekly presentation decks in `reports/dashboard/`.
Everything here is codified from the 21 April 2026 set (`hikvision_audit.html`,
`hikvision_rulebased.html`, `hikvision_leaderboard_benchmark.html`,
`dms_comparison_21Apr26.html`, `compression_pipeline_21Apr26.html`). Copy one of
those files and edit — the CSS tokens, fonts, nav, and scroll-snap plumbing
are already in place.

---

## 1. Voice

Write like a tired, seasoned researcher logging results. Not excited. Not
selling. Numbers first, interpretation second (or not at all).

### Always

- Numerical facts before framing: `96% reduction, 24 GB kept` beats
  `an impressive 96% reduction was achieved`.
- Passive or subject-less where natural: `three encoders tested`,
  `audio is dropped`, `cabin detail holds`.
- Short sentences. A period is cheaper than a clause.
- Specific identifiers over category words: `SVT-AV1 at 480p / 2 fps`
  beats `a modern, efficient codec`.

### Never

Ban list (replace on sight):

| Don't write                               | Do write                                |
|-------------------------------------------|-----------------------------------------|
| our model, our custom model, we delivered | the custom pipeline, `<name>` pipeline  |
| head-to-head, showdown, winner, beats     | scored against, vs., agreement          |
| deep-dive, field test                     | evaluation, comparison, in-vehicle      |
| successfully detected                     | detected (or state the count)           |
| precise / immediate / robust / seamless   | *drop entirely unless a number backs it* |
| delivers, slashes, unlocks, leverages     | yields, reduces by X%, runs on          |
| visual fidelity preserved                 | `~4% of source bitrate`, `detail holds` |
| state-of-the-art, cutting-edge            | *just name the model*                   |
| canonical class / canonical classes       | use case / use cases                    |
| Frames (as a stat label)                  | Alerts, Alert Data                      |

### Wording the project has settled on

- **use cases** — the 6 DMS classes (distracted, eating, fatigue, phone,
  seatbelt, smoking). Never "canonical classes" in user-facing copy.
- **Hikvision Alert Data / Alerts** — the 619 reviewed frames.
- **accuracy** — the metric. Never "balanced accuracy" in copy, even if
  the formula is `(recall + specificity) / 2` (it is).
- **detector family** — MediaPipe, Detection, Classification (three only).
  "Object Detection" → "Detection". No "(YOLO)" qualifier in legends.
- **custom pipeline** — the MediaPipe + YOLO bench pipeline. Never
  "our model" or "Custom Model (Ours)".
- **Hikvision OEM / OEM baseline** — the commercial DMS we score against.

---

## 2. File layout

One HTML file per presentation. Filename: `<topic>_<DDMonYY>.html`
(`compression_pipeline_21Apr26.html`) or plain topic name for evergreens
(`hikvision_rulebased.html`).

Skeleton (copy from any existing file):

```
<head>
  DM Sans + JetBrains Mono via Google Fonts
  :root with the shared palette (see §4)
  page-specific CSS at the bottom of <style>
</head>
<body>
  <nav>                       ← fixed top bar, matches palette
    <a href="index.html">← Home</a>
    <a href="#first"   class="active">First</a>
    <a href="#second">Second</a>
    <span class="slide-counter" id="slideCounter">1 / N</span>
  </nav>

  <section class="slide" id="first">...</section>
  <section class="slide" id="second">...</section>

  <script>
    IntersectionObserver to update counter + active nav on scroll
  </script>
</body>
```

Every slide is `min-height: 100vh; scroll-snap-align: start`. Padding is
`64px 56px 28px`. Don't fight that rhythm — add internal spacing with grids,
not padding on `.slide`.

---

## 3. Slide structure

A slide almost always opens with the same four elements in this order:

1. `<div class="slide-stamp">` — the engineering-log watermark (see §5.1).
2. `<span class="tag tag--<color>">Section Name</span>` — small monospace
   category label. Colour picks the section accent.
3. `<h2>` — section title. Short. Noun phrase. No verbs.
   `Encoder selection`, `Results`, `Methodology`. Not
   `Evaluating Three Encoders for the Fleet`.
4. `<h3>` — one short descriptive sentence. Tells the reader what's below.
   `Three encoders on the same source clips. SVT-AV1 picked on
   size-at-quality.` Not a teaser — a caption.

Then one or more of:
- stat grid
- comparison cards / encoder grid
- data table (heat-map tinted)
- video comparison
- action-bar callout
- notes list

---

## 4. Design tokens

The palette is shared across every dashboard file — do not invent new colours.

```css
--bg:           #F8F9FB       /* page background */
--bg-card:      #FFFFFF       /* card surface */
--bg-elevated:  #F0F1F4       /* chip / muted fill */
--border:       #E0E2E8

--text:         #1A1D26
--text-dim:     #5A5E6E
--text-muted:   #8E92A0

--accent:       #0E9A7E       /* teal-green  — primary brand; "good" */
--accent-2:     #3B6FD6       /* blue        — data / measurement */
--accent-3:     #C88A1A       /* amber       — warning / "maybe" */
--red:          #D9453E       /* "bad" / regression only */
--purple:       #8B5CC4
--teal:         #0E8A9A

--font: 'DM Sans', system-ui, sans-serif;
--mono: 'JetBrains Mono', monospace;
```

Accent conventions (don't mix):
- **Accent (green)** — primary, positive deltas, "good" verdicts, Hikvision
  baseline row (exception: the baseline is supposed to feel like *the* green).
- **Accent-2 (blue)** — MediaPipe family, compressed data, secondary measure.
- **Accent-3 (amber)** — Detection family, "maybe" verdicts, warnings.
- **Purple** — Classification family, derived datasets.
- **Red** — genuine regressions only. Never "this is worse than expected"
  when it's just a forced-negative.
- **Text-muted** — neutral / n/a. Use instead of red for "not applicable".

Typography:
- Numbers in `var(--mono)`, always. Including stat values, table cells,
  percentages, model ids.
- Copy in `var(--font)`. `letter-spacing: -0.02em` on `h1`/`h2`;
  `letter-spacing: 0.06em; text-transform: uppercase` on small labels
  (`.tag`, `.label`, `.slide-stamp`).

---

## 5. Components — what's been built

When in doubt, copy the block verbatim from the corresponding 21 Apr file.
All of these already render consistently across the deck; don't restyle.

### 5.1 Slide stamp

```html
<div class="slide-stamp">
  <span>compression / fleet / 2026-04</span>
  <span class="stamp-sep"></span>
  <span class="stamp-idx">01 / 03</span>
</div>
```

Top-right corner of every slide. Format: `<topic> / <scope> / YYYY-MM`
followed by a 24px rule and the slide index. Muted mono. Makes the deck feel
like a bound report. *Renumber all stamps whenever you add or drop a slide.*

### 5.2 Stat grid (landing slide)

Four-column grid of big numbers. On the landing slide, use the coloured
variant (`.intro-stats .stat--<colour>`): left accent stripe + tinted
background + large coloured value. On inner slides, use the plain `.stat`
(neutral background, smaller value).

Labels: noun, 1–2 words. Values: number + unit. Sub: one passive clause.

### 5.3 Summary cards (results slide)

Plain white card with a 3px coloured accent stripe on the left edge:

```html
<div class="summary-card" data-accent="red">
  <div class="label">Original</div>
  <div class="value" style="color:var(--red)">674 GB</div>
  <div class="detail">468 + 210 GB, two batches</div>
</div>
```

`data-accent` takes `red | green | blue | purple`. Don't fill the whole card
with the colour — only the stripe and the value.

### 5.4 Family chips / breakdown strip

Horizontal grid of 3 chips (MediaPipe / Detection / Classification), each
with a large mono count and a one-line subtitle. Left-aligned bottom rule
in the family colour. Used on the landing slide to declare the roster.

### 5.5 Capability matrix

6 × 3 table of **good / maybe / bad** verdicts. Pills use:

- `.verdict--good`  → accent (green) + filled dot
- `.verdict--maybe` → amber + filled dot
- `.verdict--bad`   → muted grey + faded dot (never red — "bad" means
  "not this detector's job", not a regression)

Column headers are coloured per family (`.fam-col-blue`, `.fam-col-amber`,
`.fam-col-purple`). The row labels carry the use-case names, not code
identifiers.

### 5.6 Leaderboard heat-map (`<table class="lb">`)

Each `<td class="num">` must carry a `data-delta` attribute. Buckets:

| Attribute value | When to use                                |
|-----------------|--------------------------------------------|
| `baseline`      | Hikvision row cells                        |
| `pos-{tiny,weak,mid,strong}` | `|Δ| < 0.03 / 0.03–0.08 / 0.08–0.18 / ≥ 0.18` and model beats baseline |
| `neg-{tiny,weak,mid,strong}` | Same brackets, model below baseline        |
| `zero`          | `|Δ| < 1e-4` exactly, non-trivial match    |
| `forced`        | **Accuracy is exactly 0.500** (forced-negative — model has no mapping for the class). Paint neutral diagonal hatch, not red. |
| `na`            | Zero GT support for that cell              |

Rules:
- Cell backgrounds do the tinting. Delta chips drop the pill background
  and just sit as inline signed numbers in the matching colour.
- Accuracy numeral picks up the sign colour; `mid`/`strong` go bold.
- Forced-negative `0.500` cells are the majority in a sparse roster — if
  you paint them red the whole table is red and means nothing. Always
  use the `forced` hatch.
- Bake the buckets in at build time with a Python script that parses each
  td's delta text; the leaderboard currently does this. Don't rely on
  runtime JS.

### 5.7 Action bar

Small left-bordered callout for a single sentence of framing:

```html
<div class="action-bar blue">
  <div class="action-text"><strong>Note on 2 fps.</strong>
    The DMS model samples frames sparsely, so every decision window is kept.
  </div>
</div>
```

One per slide, maximum. Colour picks the tone: blue = observation,
amber = caveat, red = regression, accent = summary.

### 5.8 Hero numeral (watermark)

One giant mono numeral anchored bottom-right, coloured just above
`--border` so it behaves as a watermark. Used once per deck — typically
the headline number of the whole report (`28×`, `36`, `96%`). Not a
design flourish; it's the number the reader should remember.

---

## 6. Landing page card copy

When you add a presentation to `index.html`'s `PRESENTATIONS` registry,
match these conventions.

### Material card

- `title` **must match the page's `<h1>`** (or be a clean abbreviation).
  Don't write a descriptive title in the card and a different one on the
  page — pick the short one and use it in both.
- `desc` is 1–2 terse sentences, numerical when possible, passive where
  natural. State scope, not pitch.
- Compare:
  - ✘ *"674 GB of raw bus camera footage compressed to ~24 GB via
    SVT-AV1 at 480p/2fps — 28× reduction with visual fidelity preserved
    for AI inference."* (three verbs, one marketing clause)
  - ✔ *"674 GB of H.264 1080p re-encoded to ~24 GB of SVT-AV1 480p /
    2 fps — a 28× reduction. Three encoders tested; cabin detail holds
    at ~4% of source bitrate."*

### Upcoming card (the presentation header)

- `subtitle` — one sentence, ≤ 220 chars. State the comparison scope and
  the scale. Don't preview the conclusions.
- `tags` — pick 3–4 labels that name what the reader will **see**, not
  what you did. `Hikvision / Leaderboard / Rule-based / In-vehicle` is
  good. `Comprehensive / Rigorous / Multi-Stage` is not.
- `stats` — 4 cells. Values are mono-rendered numbers or short codes
  (`36`, `619`, `21 Apr`). Labels are single nouns (`Models`, `Alerts`,
  `Use cases`, `Target`). The label must correspond to a thing in the
  linked materials, not a vibe.

---

## 7. Pre-ship checklist

Before committing a new deck:

- [ ] Every `.slide` has a `.slide-stamp` in the top-right.
- [ ] Stamp indexes match the real slide count.
- [ ] `slide-counter` in `<nav>` reads `1 / N` where N is correct.
- [ ] Nav contains one link per slide; the first is `class="active"`.
- [ ] No banned word from §1's table appears anywhere in the copy.
- [ ] All numbers carry units (`GB`, `h`, `fps`, `%`). Not bare integers
      unless context is obvious.
- [ ] Every claim with an adjective (`precise`, `high-quality`, `low`) is
      either deleted or followed by a number.
- [ ] Colour scheme limited to the `:root` tokens. No inline hex codes.
- [ ] Fonts limited to DM Sans + JetBrains Mono. No new Google Fonts links.
- [ ] The deck file lives in `reports/dashboard/` (its own git repo,
      remote is `dms-dashboard`). Commit there, not in the outer
      `DMS_ML_pipeline` repo.
- [ ] `index.html`'s `PRESENTATIONS` registry updated with a card
      following §6.

---

## 8. Known utility scripts

Not required for new decks — useful when a reviewer asks for heat-map
re-tinting or global rewording.

- Parse a `<table>` tbody and annotate every `<td>` with `data-delta`:
  see the inline Python used to build the leaderboard heat-map
  (`hikvision_leaderboard_benchmark.html`).
- Global ban-list sweep: `git grep` the §1 table terms before shipping.
