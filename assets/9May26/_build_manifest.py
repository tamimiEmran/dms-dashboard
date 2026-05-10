"""Build a JSON manifest of all source clips in the Howen recording folder.

Run once after the source folder is updated. Reusing this on subsequent
recordings = update SOURCE_DIR and rerun.
"""
import json
import os
import re
from pathlib import Path

SOURCE_DIR = Path("C:/Users/Admin/Downloads/9-May-Recording-Howen-Monitoring 1")
OUT_PATH = Path("M:/DMS/reports/dashboard/assets/9May26/source_manifest.json")

manifest = {
    "source_dir": str(SOURCE_DIR).replace("\\", "/"),
    "recording_date": "2026-05-07",
    "filename_date_range": ["2026-05-07", "2026-05-10"],
    "note": "Recording is single-day (2026-05-07). Filename timestamps span 3 dates due to device clock; trust the recording_date field.",
    "detected": {},
    "normal": [],
}

alert_re = re.compile(r"alert_(\d{8})_(\d{6})_(.+)\.mp4")
gen_re = re.compile(r"general_(\d{8})_(\d{6})\.mp4")

detected_dir = SOURCE_DIR / "detected"
for fname in sorted(os.listdir(detected_dir)):
    m = alert_re.match(fname)
    if not m:
        continue
    date_s, time_s, kind = m.groups()
    iso = f"{date_s[:4]}-{date_s[4:6]}-{date_s[6:]}T{time_s[:2]}:{time_s[2:4]}:{time_s[4:]}"
    size = os.path.getsize(detected_dir / fname)
    entry = {
        "file": fname,
        "iso": iso,
        "date": iso[:10],
        "time": iso[11:],
        "size_bytes": size,
    }
    manifest["detected"].setdefault(kind, []).append(entry)

normal_dir = SOURCE_DIR / "normal"
for fname in sorted(os.listdir(normal_dir)):
    nm = gen_re.match(fname)
    if not nm:
        continue
    date_s, time_s = nm.groups()
    iso = f"{date_s[:4]}-{date_s[4:6]}-{date_s[6:]}T{time_s[:2]}:{time_s[2:4]}:{time_s[4:]}"
    size = os.path.getsize(normal_dir / fname)
    manifest["normal"].append(
        {
            "file": fname,
            "iso": iso,
            "date": iso[:10],
            "time": iso[11:],
            "size_bytes": size,
        }
    )

print("Detected counts:")
for k, v in manifest["detected"].items():
    print(f"  {k}: {len(v)}")
print(f"Normal: {len(manifest['normal'])}")

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2)
print(f"Wrote {OUT_PATH}")
print(f"Manifest size: {os.path.getsize(OUT_PATH)} bytes")
