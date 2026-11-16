# Concise Encyclopedia

A personal, print-it-yourself encyclopedia modeled on the *Britannica Concise*: short, dense,
neutral entries in a two-column B5 book. The owner prints it for their own reading.

## Decisions (made with the owner, 2026-11-16)

- **Language:** English.
- **Size:** 15,000 entries. All of Wikipedia Vital Articles Levels 1–4 (~10,000) plus the
  ~5,000 most important Level 5 articles, balanced by category (rank within category by
  pageviews). Expected ~1,930 pages of text plus images, about 3 volumes.
- **Sources:** Wikipedia is the base. Grokipedia is used as a cross-check (the owner's explicit
  choice; they find it more reliable on politically contested topics). Wikidata supplies life
  dates for people. Where the two sources frame a contested topic differently, entries give the
  neutral version with attributed positions (see `style_guide.md`).
- **Condensing:** LLM-condensed. Haiku for Level 4–5, Sonnet for Level 1–3, run as Claude Code
  subagents **split across several sessions** (the owner prefers using plan quota over the
  paid API). An API Batch run was estimated at about $25–40 for 25k entries, should the owner change their mind.
- **Images:** included. Policy in `build_book.py::show_image` (core levels always; Level 4
  people/geography/biology/arts/technology). Cap at roughly 2,000 images for the full book.
- **Quality bar:** "really consistent and well made". `style_guide.md` is the single source of
  rules. Don't change conventions without updating it.

## Pipeline (`scripts/`)

| Step | Script | Output |
|---|---|---|
| 1. Candidate list | `select_articles.py` | `data/vital.json` (~49.8k titles with level and category) |
| 2. Pick the book's titles | `select_final.py` | `data/selection.json` (15,000; pageviews from dump files) |
| 3. Fetch sources | `fetch_sources.py <list.json>` | `data/sources/*.json` (resumable; image metadata only) |
| 3b. Fetch images | `fetch_images.py` | `data/images/*`, only for entries `show_image` keeps |
| 4. Condenser inputs | `prepare_inputs.py <selection.json> [--rebuild]` | `data/condense_input/*.json` |
| 5. Pack work groups | `pack_groups.py` | `data/groups/{sonnet,haiku}_NNN.{json,txt}` (skips finished keys) |
| 6. Condense | subagents read `style_guide.md` + a group `.txt`, write `data/condensed/<group>.json` | |
| 7. Check | `validate.py` (mechanical rules), `fact_check.py` (numbers absent from sources) | `data/failed.json` |
| 8. Build | `build_book.py [--light] [--out book/x.pdf]` | `book/entries.json` → Typst `book/main.typ` → PDF |

Python env: `uv venv .venv --python 3.12 && uv pip install requests beautifulsoup4 lxml typst pillow keyring`.
Set `PYTHONUTF8=1` on Windows. Group `.txt` files exist because agent file readers truncate
very long JSON lines. Keep lines ≤160 chars.

### Subagent prompt used in the pilot (worked well)

> Read the style guide `style_guide.md` and follow it exactly. Read the source file
> `data/groups/<group>.txt` (entries separated by "=== KEY:" lines). Write ONE file
> `data/condensed/<group>.json`: a JSON array of {"key","headword","sort_key","entry"}.
> Only facts from the supplied sources; word targets by level; definitional fragment first;
> no birth/death dates for people; cross-references only as [[Exact Candidate Title|text]]
> from that entry's CROSSREF_CANDIDATES, first mention only, max 8; neutral on contested topics.
> Copy numbers exactly as the sources give them; do not round or reword figures, and do not add dates or
> numbers the sources don't state.
> Do not use shared scratch files outside data/condensed. Reply only with the count written.

For Sonnet groups, write "word targets by level (Level 3: stay within 200–280 words)". Wave 1 Level 3
entries ran to a median of 286 words. Wave 1 also had one agent re-run another agent's scratch script.

Groups: Haiku 25 entries per group, Sonnet 10 per group, about 10 agents in parallel per wave.

### Token budget rules (the owner is cost-sensitive)

- **Always set the subagent model explicitly:** `model: "haiku"` for `haiku_*` groups, `model: "sonnet"`
  for `sonnet_*` groups. Never let condensing agents inherit the main session's model.
- **Never condense entries in the main session.** The main session only runs scripts, launches
  agents and reviews validator output.
- Keep the main session's own context small. Don't read source or condensed files in bulk;
  rely on `validate.py` and `fact_check.py` summaries, and spot-check only flagged entries.
- Run agents in the background and don't poll them.

## Status

- Pilot done: 196 entries (`data/pilot_titles.json`), all pass `validate.py`. `fact_check.py`
  found no unsupported numbers. `book/pilot.pdf` is 40 pages.
- Pilot cost was about 9,600 subagent tokens per entry (most of it fixed overhead per group).
- `style_guide.md` gained the Unicode sub/superscript rule (H₂O) **after** the pilot ran, so pilot
  entries still have flat "H2O".
- Waves 1–2 condensed (`sonnet_000`–`005`, `haiku_000`–`013`, 410 entries): all pass `validate.py`.
  Wave 3 onward: `sonnet_006`+, `haiku_014`+.
  Cost was ~12.6k tokens per Sonnet entry and ~7.7k per Haiku entry, so ~120M tokens for the book.
  The old pilot output is in `data/condensed_pilot_v1/`; pilot titles are re-condensed in their normal groups.
- `data/selection.json` done: 10,012 Level 1–4 + 4,988 Level 5 = 15,000.
- Sources fetched for all 15,000 (248 have no Grokipedia page). Condenser inputs built.
  Groups: 100 Sonnet (`sonnet_000`–`099`) and 561 Haiku (`haiku_000`–`560`), 15,000 entries. Waves run
  3 Sonnet + 7 Haiku groups in order. `data/groups/` is gitignored: rerun
  `pack_groups.py` in a fresh clone (it skips finished keys).

## Next steps

1. Condense in waves across sessions. After each wave run `validate.py`, re-run failures with Sonnet,
   and run `fact_check.py`.
2. Apply the image cap (~2,000) in `show_image`, then run `fetch_images.py`. The current policy alone
   would pick ~5,000. `data/images/` is gitignored, so a fresh clone must rerun it (pilot images too).
3. Split into volumes (A–F / G–P / Q–Z or by page count), add an index, and build print PDFs.

## Notes

- Wikipedia's Vital Articles pages live at `Wikipedia:Vital articles/Level N/...` (with a space). The
  old `Level/N` titles are redirects.
- Grokipedia lead text sits between the `<h1>` and the first `<h2>` in `<article>`. Strip script and
  style tags and HTML comments (see `grokipedia_lead`).
- `send_mail.py` (Naver SMTP) reads its password from Windows Credential Manager. It works only on
  the owner's PC and has never sent successfully (535 auth error; Naver SMTP and app password not set up).
- Cloud sessions share an IP that Wikimedia throttles for anonymous API calls (429 everywhere). The
  owner's OAuth access token (owner-only consumer on meta, 5,000 requests/hour) is saved as a network
  secret for `en.wikipedia.org` on the "Enclyclopedia" environment; `fetch_sources.py` paces itself under it.
  Wikidata and Grokipedia need no token. Pageview dumps on dumps.wikimedia.org are never throttled.
- Wikimedia thumbnails must use standard widths (960 px here). Odd widths get Retry-After: 600.
- Wikidata life dates come from item JSON, not SPARQL (SPARQL converts Julian dates to Gregorian).
  SPARQL is used only to find which items are people.
- Scripts never hard-code a contact email. Set `CE_CONTACT` to add one to the User-Agent.
- In cloud sessions, detached processes (`nohup … &`) die about 20 minutes after the session goes idle. Run long
  jobs such as `fetch_sources.py` as a harness-tracked background Bash task (max 2 h), commit `data/sources`, and
  restart it when it exits.
- `validate.py` (fixed in wave 5): asterisks in names (Sagittarius A*, M87*) and "I"/"You" inside
  *titles*, [[links]] or capitalized names (Zhong You) no longer count as errors. Before this fix, agents
  had mangled 3 entries to get past it; those were restored from git. When a flag looks like a false
  positive, fix the validator, not the entry.
- `fact_check.py` false positives so far are all format changes: spelled-out numbers ("seventeen"),
  "6.3 million" vs 6,300,000, flattened superscripts ("1040" for 10⁴⁰), and simple arithmetic ("a year later").
