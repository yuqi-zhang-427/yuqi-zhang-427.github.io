# yuqizhang.me — Personal site

[![Update publications](https://github.com/yuqi-zhang-427/yuqi-zhang-427.github.io/actions/workflows/update-publications.yml/badge.svg)](https://github.com/yuqi-zhang-427/yuqi-zhang-427.github.io/actions/workflows/update-publications.yml)

Static GitHub Pages site. The **Publications** section auto-syncs from Google Scholar.

## How the auto-sync works

```
Google Scholar ──(SerpApi)──► scripts/fetch_scholar.py ──► data/publications.json ──► assets/pubs.js ──► page
                                        ▲
                          data/overrides.json  (the bits Scholar can't give)
```

- A weekly GitHub Action (`.github/workflows/update-publications.yml`) scrapes Scholar through SerpApi, merges your supplements, writes `data/publications.json`, and commits it — GitHub Pages then redeploys on its own.
- The browser renders that JSON via `assets/pubs.js`. If the fetch ever fails, the static entries in `index.html` stay visible as a fallback.

## One-time setup (needed for auto-sync)

1. **Get a free SerpApi key** → https://serpapi.com/ (free tier = 100 searches/month; the weekly sync uses ~4).
2. **Add it as a repo secret**: GitHub repo → *Settings → Secrets and variables → Actions → New repository secret*
   - Name: `SERPAPI_KEY`
   - Value: *your key*
3. **Let the Action push**: *Settings → Actions → General → Workflow permissions → Read and write permissions*.
4. **Kick off the first run**: *Actions tab → “Update publications from Google Scholar” → Run workflow* (or just wait for Monday).

After that it updates itself weekly.

The Action commits refreshed data directly to `main`. A local checkout can therefore look stale even when the live site is current; run `git pull --ff-only` before editing publication data locally. The status badge above links to the latest sync runs.

## What you maintain: `data/overrides.json`

Scholar does **not** expose impact factors, corresponding-author marks, full author names, or rich venue text — you supply those here. Common edits:

- **New journal / impact factor** → add under `journals`:
  ```json
  "nature communications": { "type": "journal", "impact_factor": 16.6 }
  ```
- **A collaborator showing up as initials** (e.g. `J Smith`) → add under `author_full_names` so it expands to the full name:
  ```json
  "John Smith": "John Smith"
  ```
- **Figures** → the publication list is text only. The **Journal Cover** block beside News is written by hand in `index.html`; their images live in `assets/img/papers/`. The per-paper `image` field is kept in the data but not displayed.
- **A paper's venue tag and full venue name** → set `venue_badge` (the short navy label above the title; the year is added, so `"PNAS"` shows as "PNAS 2026", while a badge that already has a year such as `"SC '26"` is shown as written) and `venue_full` (shown in italics under the authors). A `status` such as `"In Press"` gets its own label.
- **An accepted paper Scholar doesn't list yet** → add it under `manual_publications` with a placeholder `citation_id` such as `manual:pnas-kras-2026` (reference that ID in `order`) and `"status": "In Press"`. When Scholar adds the paper, it is matched by title, so no duplicate card appears and the order stays put. Two collaborators whose names share a first initial and surname (Sixu Chen and Siwei Chen) must not both be in `author_full_names`; write one as `{ "name": "Sixu Chen" }` in that paper's author list.
- **A specific paper** (corresponding authors, venue prose, code links, “Under Review”, *et al.*) → add an entry under `publications`, keyed by its **`citation_id`** — the string after `citation_for_view=` in that paper's Scholar link.

Curated titles, authors, years, links, and display fields in `overrides.json` take precedence over Scholar. Citation counts still refresh automatically. Matching uses the current `citation_id`, an explicit `citation_aliases` list for old IDs, then a unique title normalized for Unicode dashes and spacing. This keeps metadata and ordering intact when Scholar merges or replaces a record. If both old and current IDs appear, one card is shown with the larger citation count, without adding duplicate counts together.

The `order` list sets the chosen venue-priority order for published papers: PNAS, Advanced Science, SC (2026 before 2025), then ACM Transactions on Quantum Computing. Preprints appear after published work. Scholar refreshes keep this curated order.

For a journal Frontispiece, add a `frontispiece` object to the original paper's override with `image`, `url`, `title`, `issue`, `published`, `credit`, `license`, and `license_url`. The paper then gets a "Frontispiece" label that links to the **Journal Cover** block beside News, where the full cover is shown with its issue details and the image credit and licence (edit that block in `index.html` when the cover changes). The feature's publication date is separate from the original research article's year. If Scholar lists the Frontispiece separately, set its `citation_id` and full `scholar_title` inside that object so it stays attached to the research paper instead of producing an extra paper card.

**Sync policy** (enforced in `scripts/fetch_scholar.py`, not configurable via overrides):

- Only papers where **you are the first author** are kept — in both sections.
- **Published journal/conference** entries render as full-detail cards under **Publications**.
- **arXiv preprints and under-review** entries render as compact rows under **Preprints & Working Papers** (title + venue + year only; no authors, citations, or corresponding marks).
- Corresponding-author marks (Publications only) are **per-paper**. If a paper's `publications` entry doesn't list `corresponding`, no author is marked.

## Run / test

```bash
# Regression checks for changed Scholar IDs, curated metadata, and Frontispiece data:
python3 -B -m unittest discover -s tests -v

# Test the transform offline, no key needed (uses a saved sample response):
python3 scripts/fetch_scholar.py --input-json tests/sample_serpapi.json --dry-run

# Real fetch locally:
SERPAPI_KEY=xxxxx python3 scripts/fetch_scholar.py

# Preview the site locally:
python3 -m http.server 4321   # then open http://localhost:4321
```

## Files

| Path | Purpose |
|------|---------|
| `index.html` | The page. `#pub-list` is filled in by JS. |
| `assets/pubs.js` | Fetches `data/publications.json` and renders the list. |
| `assets/img/papers/` | Paper figures and the journal cover, used by the Journal Cover block in `index.html`. |
| `assets/img/research-overview.webp`, `research-overview-mobile.webp` | Research overview figure (wide, and stacked for phones), drawn in Figma and exported at 2x. `overview-protein.webp` is the KRAS structure used inside it. |
| `assets/img/og-card.png` | Social preview card (2400×1260) used by Open Graph and X metadata. |
| `data/publications.json` | Auto-generated publication data — **don't hand-edit**. |
| `data/overrides.json` | **Your** supplements (IF, corresponding authors, venue text, links). |
| `scripts/fetch_scholar.py` | Scholar → JSON fetcher (standard library only, zero deps). |
| `.github/workflows/update-publications.yml` | Weekly auto-update job. |
| `tests/sample_serpapi.json` | Mock SerpApi response for offline testing. |

## If a sync fails

The fetcher exits **without** overwriting `data/publications.json` when Scholar returns nothing (bad/missing key, quota exhausted, network blip), so the last good list stays live. Check the Actions log — the usual cause is a missing or used-up `SERPAPI_KEY`.
