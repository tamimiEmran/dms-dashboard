"""Generate an HTML reconstruction of slide 3 from shapes.json.

Each shape is positioned absolutely as a percentage of slide dimensions, so
the page scales with viewport width. Renders:
  - PICTURE  → <img>
  - TEXT_BOX → <div> with the original text
  - LINE     → straight line drawn into a single SVG overlay
  - AUTO_SHAPE (rect with no text) → <div> with light border (frame)
  - FREEFORM → SVG overlay (rendered as a small badge)
"""
import json
from pathlib import Path

DIR = Path("M:/DMS/reports/dashboard/assets/leasing_taxis_arch")
manifest = json.loads((DIR / "shapes.json").read_text(encoding="utf-8"))

OUT = Path(
    "M:/DMS/reports/dashboard/presentations/2026-05-10-edge-deployment/details/mass-rollout-leasing-taxis.html"
)
OUT.parent.mkdir(parents=True, exist_ok=True)


def pct(v):
    return f"{v * 100:.3f}%"


# Build absolutely-positioned elements for pictures + text + frames
positioned_html = []
svg_lines = []

for shape in manifest["shapes"]:
    left = pct(shape["left_frac"])
    top = pct(shape["top_frac"])
    width = pct(shape["w_frac"])
    height = pct(shape["h_frac"])
    style = f"left:{left};top:{top};width:{width};height:{height};"
    kind = shape["kind"]
    if kind == "picture" and "image" in shape:
        positioned_html.append(
            f'<img class="shape pic" src="../../../assets/leasing_taxis_arch/{shape["image"]}" '
            f'style="{style}" alt="" />'
        )
    elif kind == "text" and shape.get("text"):
        text_html = (
            shape["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        text_html = text_html.replace("\n", "<br/>")
        # First line gets bolded if it looks like a label
        positioned_html.append(
            f'<div class="shape text" style="{style}">{text_html}</div>'
        )
    elif kind == "rect" and not shape.get("text"):
        # Auto-shape used as a card background — render as a faint frame.
        positioned_html.append(
            f'<div class="shape frame" style="{style}"></div>'
        )
    elif kind == "rect" and shape.get("text"):
        # Header/title rect with text
        text_html = (
            shape["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        positioned_html.append(
            f'<div class="shape title-rect" style="{style}">{text_html}</div>'
        )
    elif kind == "line":
        # SVG line — coordinates are top-left to bottom-right of the bounding box.
        x1 = shape["left_frac"] * 100
        y1 = shape["top_frac"] * 100
        x2 = (shape["left_frac"] + shape["w_frac"]) * 100
        y2 = (shape["top_frac"] + shape["h_frac"]) * 100
        svg_lines.append(
            f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="#5A5E6E" stroke-width="0.15" />'
        )
    elif kind == "freeform":
        # Render as a small green chevron at the shape's top-left
        positioned_html.append(
            f'<div class="shape freeform" style="{style}">▸</div>'
        )

slide_w = manifest["slide_w_emu"]
slide_h = manifest["slide_h_emu"]
aspect = f"{slide_w}/{slide_h}"

html_template = f"""<!DOCTYPE html>
<html lang="en">
<!--
  Mass-rollout overlay: AI Brain Architecture for Leasing Model Taxis.
  Rebuilt from slide 3 of AI Brain Architecture_Final.pptx via
  assets/leasing_taxis_arch/_extract_slide3.py + _build_overlay.py.

  Shapes are absolutely positioned by fraction of the slide dimensions
  (slide aspect: {aspect}). Pictures live at ../../../assets/leasing_taxis_arch/.
-->
<head>
  <meta charset="UTF-8">
  <meta name="robots" content="noindex,nofollow">
  <style id="dms-gate-hide">body{{display:none!important}}</style>
  <script src="../../../password-gate.js"></script>
  <meta name="viewport" content="width=1280">
  <title>Leasing Model Taxis · AI Brain Architecture</title>
  <link
    href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=JetBrains+Mono:wght@400;500&display=swap"
    rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #F8F9FB;
      --bg-card: #FFFFFF;
      --bg-elevated: #F0F1F4;
      --border: #E0E2E8;
      --text: #1A1D26;
      --text-dim: #5A5E6E;
      --text-muted: #8E92A0;
      --accent: #0E9A7E;
      --accent-2: #3B6FD6;
      --accent-3: #C88A1A;
      --font: 'DM Sans', system-ui, sans-serif;
      --mono: 'JetBrains Mono', monospace;
    }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      line-height: 1.4;
      padding: 28px 32px 36px;
      min-height: 100vh;
      -webkit-font-smoothing: antialiased;
    }}
    .pill {{
      display: inline-block;
      font-family: var(--mono);
      font-size: 10px;
      letter-spacing: 0.10em;
      text-transform: uppercase;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(14, 154, 126, 0.10);
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 8px;
    }}
    h1 {{
      font-size: 22px;
      font-weight: 600;
      letter-spacing: -0.02em;
      margin-bottom: 4px;
    }}
    .sub {{
      font-family: var(--mono);
      font-size: 11.5px;
      color: var(--text-muted);
      letter-spacing: 0.04em;
      margin-bottom: 18px;
    }}

    /* === Slide canvas === */
    .slide-stage {{
      position: relative;
      width: 100%;
      max-width: 1280px;
      aspect-ratio: {aspect};
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
      margin: 0 auto;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .slide-stage .shape {{
      position: absolute;
    }}
    .slide-stage .pic {{
      object-fit: contain;
    }}
    .slide-stage .text {{
      font-size: clamp(8px, 0.95cqi, 14px);
      line-height: 1.25;
      color: var(--text);
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 2px 4px;
      container-type: inline-size;
    }}
    .slide-stage .frame {{
      border: 1px solid var(--border);
      border-radius: 6px;
      background: rgba(255,255,255,0.0);
    }}
    .slide-stage .title-rect {{
      font-size: clamp(14px, 2cqi, 28px);
      font-weight: 700;
      letter-spacing: -0.01em;
      color: var(--text);
      display: flex;
      align-items: center;
      padding-left: 16px;
      container-type: inline-size;
    }}
    .slide-stage .freeform {{
      color: var(--accent);
      font-size: clamp(10px, 1.5cqi, 22px);
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .slide-stage svg.lines {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
    }}

    .footnote {{
      margin-top: 18px;
      padding: 12px 14px;
      background: var(--bg-elevated);
      border-left: 3px solid var(--accent-3);
      border-radius: 0 6px 6px 0;
      font-size: 12.5px;
      color: var(--text-dim);
      max-width: 1280px;
      margin-left: auto;
      margin-right: auto;
    }}
    .footnote strong {{ color: var(--text); font-weight: 600; }}
  </style>
</head>
<body>
  <span class="pill">Mass rollout · early-exit overlay</span>
  <h1>AI Brain Architecture &mdash; Leasing Model Taxis</h1>
  <div class="sub">Rebuilt from slide 3 of AI Brain Architecture_Final.pptx · {len(manifest['shapes'])} shapes · {manifest['image_count']} unique images</div>

  <div class="slide-stage">
    <svg class="lines" viewBox="0 0 100 {(slide_h / slide_w * 100):.3f}" preserveAspectRatio="none">
{chr(10).join("      " + line for line in svg_lines)}
    </svg>
{chr(10).join("    " + el for el in positioned_html)}
  </div>

  <div class="footnote">
    <strong>How this overlay opens:</strong> click on the &ldquo;Early-exit trigger&rdquo;
    box at the bottom of the Model Development Cycle SVG. The trigger fires
    when any weekly field test reaches the 71% threshold and authorises a
    mass rollout to 100 leasing-model taxis with the architecture shown above.
  </div>
</body>
</html>
"""

OUT.write_text(html_template, encoding="utf-8")
print(f"Wrote {OUT}")
print(f"  {len(positioned_html)} positioned elements")
print(f"  {len(svg_lines)} SVG lines")
