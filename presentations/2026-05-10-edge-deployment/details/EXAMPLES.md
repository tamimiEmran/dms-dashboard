# Examples gallery — swap workflow

Where the test-vehicle gallery (`details/test-vehicle.html`) gets its videos
and how to replace them.

## Layout

```
reports/dashboard/
├── assets/9May26/
│   ├── _build_manifest.py       # rebuilds source_manifest.json from the source folder
│   ├── source_manifest.json     # ALL 386 source clips, indexed by alert kind + ISO time
│   └── alert_*.mp4 / general_*.mp4   # currently featured clips (12 of 386)
└── presentations/2026-05-10-edge-deployment/details/
    ├── test-vehicle.html        # gallery — FEATURED array drives rendering
    └── EXAMPLES.md              # this file
```

## Source data

- **Source folder**: `C:/Users/Admin/Downloads/9-May-Recording-Howen-Monitoring 1`
  - `detected/` — 386 alert clips (`alert_<YYYYMMDD>_<HHMMSS>_<kind>.mp4`)
  - `normal/` — 123 baseline clips (`general_<YYYYMMDD>_<HHMMSS>.mp4`)
- **Recording date**: 2026-05-07 (filename timestamps span 2026-05-07 → 2026-05-10 from the device, but the recording is single-day)
- **Alert kinds** (5):

  | Kind in filename            | Use case in deck   | Source count |
  |-----------------------------|--------------------|--------------|
  | `look_forward`              | Distracted driving |          162 |
  | `drowsiness_detected`       | Fatigue            |          168 |
  | `put_down_your_phone`       | Phone usage        |           39 |
  | `fasten_your_seatbelt`      | Seatbelt           |           10 |
  | `yawn_detected`             | Yawn (fatigue-adj) |            7 |

## Currently featured (12 clips)

Two per kind plus two normal-driving baselines, spread across May 7 and May 10
where possible. Selection lives in the `FEATURED` array in `test-vehicle.html`.

## Swap workflow

### 1. Find a candidate in `source_manifest.json`

```bash
# All drowsiness clips, sorted by filename time
M:/DMS/.venv/Scripts/python.exe -c "
import json
m = json.load(open('M:/DMS/reports/dashboard/assets/9May26/source_manifest.json'))
for c in m['detected']['drowsiness_detected']:
    print(c['file'], c['time'])
"
```

(Filename `date` prefixes are unreliable — the recording is single-day on
2026-05-07, see `recording_date` in the manifest. Filter by `time` window
or by visual inspection rather than by `date`.)

### 2. Copy the clip into the assets folder

```bash
cp "C:/Users/Admin/Downloads/9-May-Recording-Howen-Monitoring 1/detected/<new_file>.mp4" \
   "M:/DMS/reports/dashboard/assets/9May26/"
```

### 3. Update the `FEATURED` entry in `test-vehicle.html`

Find the row with the old `file` name and replace `file` + `when` (time-of-day only):

```js
{ kind: 'drowsiness', file: 'alert_<NEW>.mp4', when: '14:35:12', label: 'Drowsiness detected' },
```

### 4. (Optional) Remove the orphaned old clip

```bash
rm "M:/DMS/reports/dashboard/assets/9May26/<old_file>.mp4"
```

## Updating the source manifest

Run the helper script when the source folder changes:

```bash
M:/DMS/.venv/Scripts/python.exe "M:/DMS/reports/dashboard/assets/9May26/_build_manifest.py"
```

If the source folder moves, edit `SOURCE_DIR` at the top of that script and rerun.

## Adding a new alert kind

1. Add a row to `SECTIONS` in `test-vehicle.html` (`kind`, `title`, `short`, `accent`, `sourceCount`).
2. Add `FEATURED` rows with that `kind`.
3. Copy the clips into `assets/9May26/`.

The accent values map to existing CSS classes — `green | amber | blue | purple | teal | muted`.

## Notes

- Featured-clip files live under `assets/9May26/` (flat folder, no per-kind subfolders).
  Iframes from the deck resolve as `../../../assets/9May26/<file>`.
- The source manifest excludes `__MACOSX/` artefacts.
- Videos are served with `preload="metadata"` so they don't all download at once
  on page load.
