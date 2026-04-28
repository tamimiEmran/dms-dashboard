# Dashboard Password Gate — Design

**Date:** 2026-04-28
**Repo:** `tamimiEmran/dms-dashboard` (deployed via GitHub Pages, `master` root, no custom domain)
**Status:** drafted, awaiting review

---

## 1. Problem

The dashboard is hosted at `https://tamimiemran.github.io/dms-dashboard/`. The
backing repo is private, but the Pages site is publicly reachable to anyone
who knows or guesses the URL (`"public": true` per the Pages API). We want a
lightweight gate that:

- Stops casual visitors who land on the URL by accident or via a forwarded
  link from seeing the content.
- Keeps the site out of Google's index.

We are explicitly **not** trying to stop a determined visitor with browser
DevTools or `curl`. That tier of protection is incompatible with static
hosting on GitHub Pages and is deferred to a possible future migration.

## 2. Goals & non-goals

**In scope:**

- Single shared password (`@inno$dpt_pwd...`, hash committed; plaintext
  shared out-of-band).
- Client-side gate that hides body content of every served HTML file until
  the password is entered correctly.
- `noindex` directive on every HTML file plus a root `robots.txt` to block
  search-engine indexing.
- Idempotent injector script so newly added HTML files can be gated by
  re-running one command.

**Explicitly out of scope:**

- Protecting `/assets/**` files (images, videos, PDFs). They remain publicly
  fetchable by URL. GitHub Pages does not list directories, so discovery
  requires guessing or a leaked URL — accepted as the B-tier trade-off.
- Resistance to DevTools bypass, `curl`, or anyone who reads the gate's
  source. The hash makes the password itself non-leaky from the gate file,
  but the gate's HTML/JS is fully inspectable.
- Per-recipient passwords or revocation. One password for everyone; rotation
  = update one hash + everyone re-enters.
- Server-side authentication, OAuth, or any third-party identity provider.

## 3. Architecture

Four artifacts:

```
dashboard/
├── password-gate.js                    # NEW — single source of truth
├── robots.txt                          # NEW — Disallow: /
├── scripts/
│   └── inject_password_gate.py         # NEW — idempotent injector
└── **/*.html                           # MODIFIED — two new <head> lines each
```

### 3.1 `password-gate.js`

Loaded synchronously from every HTML file's `<head>`, before `<body>` parses.
Embeds the SHA-256 hash of the shared password as a constant. On load:

1. Read `localStorage.getItem('dms-dashboard-unlocked')`.
2. If the stored value equals the embedded hash → do nothing. Page renders
   normally.
3. Otherwise:
   - Inject `<style>body{display:none}</style>` so the real content never
     flashes.
   - On `DOMContentLoaded`, replace `<body>` content with a centered password
     prompt (input + submit button).
   - On submit, hash the input via `crypto.subtle.digest('SHA-256', ...)`,
     compare to the embedded hash. Match → store hash in `localStorage` and
     reload the page. Mismatch → clear input, show "wrong password."

Storing the hash (rather than a boolean flag) means rotating the password
auto-invalidates everyone's session: the next page load won't find a
matching value and will re-prompt.

### 3.2 `<head>` injection

Every served HTML file gains exactly two lines, inserted after the existing
`<meta charset>` line:

```html
<meta name="robots" content="noindex,nofollow">
<script src="/dms-dashboard/password-gate.js"></script>
```

The `/dms-dashboard/` prefix matches the GitHub Pages project-site URL. An
absolute path is used (not relative) so the script resolves correctly from
nested files like `reports/hikvision/audit.html`.

### 3.3 `robots.txt`

Three lines at repo root:

```
User-agent: *
Disallow: /
```

`noindex` is the load-bearing directive (Google honors it even on pages it
crawls); `robots.txt` is a polite supplement that discourages crawling in
the first place.

### 3.4 `scripts/inject_password_gate.py`

Modeled on the existing `scripts/rewrite_paths.py`. Walks every `*.html` file
in the repo, skips those that already contain the gate `<script>` tag, and
inserts the two `<head>` lines for the rest. Idempotent — safe to run
multiple times. Reports inserted/skipped counts. Run once now, run again
when new HTML files are added.

## 4. Page-load sequence

```
1. Browser fetches /dms-dashboard/some_page.html (no auth required by host).
2. <head> parses. <meta robots noindex> + <script password-gate.js> seen.
3. password-gate.js fetched and run synchronously.
4. Script checks localStorage:
   - Match → script returns; <body> parses and renders normally.
   - No match → script injects display:none style, queues DOMContentLoaded
     handler, returns.
5. <body> parses (invisible). DOMContentLoaded fires.
6. Handler swaps body for password prompt.
7. User submits. Hash compared. Match → store + reload (back to step 1, this
   time the localStorage check passes).
```

## 5. Limitations (re-stated for the record)

- **Asset URLs are fetchable.** Anyone who knows or guesses
  `/dms-dashboard/assets/...` can download the file. The gate runs in the
  browser; it has no way to intervene in separate HTTP requests for
  `<img>`/`<video>` resources.
- **HTML source is fetchable too**, but its visible content is in encoded
  form only after the gate-injection (the page's body still contains the
  full markup; we only hide it visually). A `curl` returns the full HTML.
  Per the B-tier accept-list.
- **Password rotates by editing one hash** in `password-gate.js`. There is
  no admin UI; it's a code change + push.
- **No telemetry** on failed attempts, no rate-limiting. A scripted attack
  can try thousands of passwords against the JS-side hash check — but it
  has to do so client-side, and the password is long/strong enough that
  brute force is impractical in any realistic time.

## 6. Decisions log

| Decision | Choice | Why |
|---|---|---|
| Storage | `localStorage` (persists across sessions) | UX: one-time prompt per browser. Switch to `sessionStorage` later if too lax. |
| Stored value | Hash, not boolean | Password rotation auto-invalidates sessions. |
| Hash algorithm | SHA-256 via `crypto.subtle` | Browser-native, no library, no build step. |
| Password embedding | Hash only, plaintext out-of-band | Keeps password out of git history. |
| Scope | All HTML in repo, including `archive/` and `drafts/` | Simpler than maintaining an exemption list. |
| Script src path | Absolute (`/dms-dashboard/...`) | Resolves correctly from any depth. Tied to project-site URL prefix; if a custom domain is added later, change to `/`. |
| Per-recipient passwords | No | YAGNI for B-tier; complicates rotation. |

## 7. Acceptance criteria

- Visiting any HTML page on the deployed site (root, `reports/...`,
  `presentations/...`, `drafts/...`, `archive/...`, `onboarding/...`)
  shows a password prompt instead of content.
- Entering the correct password unlocks the page and persists across page
  navigations within the same browser.
- Entering the wrong password leaves the prompt visible and shows a "wrong
  password" message.
- `view-source:` on any page shows the `noindex` meta tag.
- `https://tamimiemran.github.io/dms-dashboard/robots.txt` returns
  `User-agent: *\nDisallow: /`.
- Re-running `python scripts/inject_password_gate.py` after the initial
  injection reports 0 files modified (idempotent).

## 8. Future work (deferred)

- Migrate to Cloudflare Pages + Cloudflare Access for true server-side auth
  that protects assets too. Estimated 45 min, separate spec.
- Replace shared password with email-PIN whitelist (Cloudflare Access
  handles this natively).
