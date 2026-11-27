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
- **Condensing is complete: all 15,000 entries** (`sonnet_000`–`099`, `haiku_000`–`560`) are in `data/condensed/` and pass
  `validate.py` (its 39 remaining "not written" items are extra condense inputs that are not in `data/selection.json`).
  `haiku_440`–`560` were run without waves on 2026-11-27: up to 20 Haiku agents at once (the session limit), each new one
  launched as another finished, with one shared prompt in `data/groups/PROMPT.md` (gitignored; same text as the wave prompt).
  Checks ran once at the end. Cost was ~8k subagent tokens per Haiku entry and ~13k per Sonnet entry.
  Old pilot output is in `data/condensed_pilot_v1/`. Pilot titles were re-condensed in their normal groups.
- `data/selection.json` done: 10,012 Level 1–4 + 4,988 Level 5 = 15,000.
- Sources fetched for all 15,000 (248 have no Grokipedia page). Condenser inputs built.
  Groups: 100 Sonnet (`sonnet_000`–`099`) and 561 Haiku (`haiku_000`–`560`), 15,000 entries. Waves run
  3 Sonnet + 7 Haiku groups in order. `data/groups/` is gitignored: rerun
  `pack_groups.py` in a fresh clone (it skips finished keys).

## Next steps

1. (Done) Condensing. Before the build, do the British vs American spelling consistency pass for waves 1–34.
2. Apply the image cap (~2,000) in `show_image`, then run `fetch_images.py`. The current policy alone
   would pick ~5,000. `data/images/` is gitignored, so a fresh clone must rerun it (pilot images too).
3. In `build_book.py`, number homographs (same headword, e.g. Bar¹/Bar²) in a stable order such as by level
   and then key, per `style_guide.md`.
4. Split into volumes (A–F / G–P / Q–Z or by page count), add an index, and build print PDFs.

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
- `fact_check.py` now reads spelled-out numbers ("forty-six", "eight hundred", "nineteenth") and "4.3 million".
  The 7 flags left in waves 1–6 were all reviewed: derived figures (Einstein 1901, Guinness 1936, Kumar 1992,
  ASEAN 2020s), formatting (Aconcagua 22,858; Angular momentum 10⁴⁰), and the LA riots' "over 2,380", a
  rounded version of the source's 2,383. Only new flags need review.
- More reviewed `fact_check.py` flags, all fine: Biosphere/Brazilian Highlands (dotted thousands, now read), Galaxy 2×10¹¹
  (flattened superscript in the source), Genghis Khan 1219 (source: 1218, "the following year"). Ordinals
  ("twelfth") are now read correctly.

- A scheduled task ("Encyclopedia: condense 5 waves", every 5 h) fires into the main session and runs 5 waves
  per firing (see its prompt). Run `validate.py` yourself after every wave: agents sometimes report "no flags"
  while their own file still has over-length entries (`sonnet_055` had 6) or a mangled key
  (`Democratic-Republican_Party_535fd0` for `Democratic_Republican_Party_535fd0`). Fix keys mechanically.
- `validate.py` no longer treats [[links]] as source mentions (Creative Commons links to Wikipedia). `fact_check.py`
  also reads "2.5 × 106" as 2.5 × 10⁶ and ordinals up to ninety-ninth.
- `validate.py` now has `NAMES_WITH_PRONOUNS` (e.g. "Umkhonto we Sizwe"): add proper names with a lowercase
  we/you/us there instead of editing entries. Agents also kept exceeding 8 cross-references (wave 22, 8 entries):
  the wave prompt now says "AT MOST 8 LINKS PER ENTRY (count them)".
- Wave prompt additions that cut flags (waves 30+): "check each link target against that list", "never use we/you/our", "a century or decade not
  named by the sources counts as a new date". `fact_check.py` does not read "one hundred and sixty" (Davy, reviewed, fine) or "11th century"
  derived from 1071 (History of Turkey, fine).
- Haiku-only waves (35+): 10 Haiku agents per wave, prompt says "write the file once, when it is complete" (otherwise the commit loop
  commits half-written files) and "American spelling in headwords and text". Proper names keep their official spelling (Labour Party, not
  "Labor Party": fixed by hand in wave 39; Israel Defense Forces and Kennedy Space Center are official American forms). Add "except proper
  names such as Labour Party" to the wave prompt. Waves 1–34 may still contain British spellings (Industrialisation was fixed by hand); a
  consistency pass for British vs American spelling is still to do before the build. Validate only after every agent has reported.
- `fact_check.py` now takes 5+ minutes: run it as a background Bash task (`run_in_background`, big timeout) and read its output file when
  notified. Run `validate.py` and `fact_check.py` only after the LAST agent of the wave has reported (an agent may still be writing its file).
  Prompt addition (wave 41+): "do not round, e.g. keep 372.15, not 372". Derived flags reviewed as fine: Kurds 1923 (1920 + three years),
  Foucault 1858 ("succeeding year"), Lock 250 ("two hundred and fifty"), Malawi 1966 (1964 + "two years later").
- Waves 45–49: Level 5 target is now "at most 100 words (hard limit 105)"; prompt also says "do not convert units, do not expand a range
  like 1904–08 into a new date" (wave 47 had real misses: North Pole 13,000 ft vs source 13,100 feet, Olmecs "650 BC" not in source; fixed by
  hand). Mwene we Mutapa was added to `NAMES_WITH_PRONOUNS`. Reviewed flags, all fine: Namibia 1908 ("1904–08"), Pagan Kingdom 846/1297
  (input `description` field), Pandanus 6.5 ("6+1⁄2 ft"), Odrysian 479 ("480–79"), Nuclide 10 (flattened 10¹⁷), Numerical digit 100 (4/100).
- Final run (haiku_440–560): 12 new `fact_check.py` flags. Fixed: Toyota (Corolla "1966" not in source), University of Chicago
  ("more than 100" → 102 Nobel laureates), Volkswagen (Beetle "2003" end not in source). Fine: Salsa ("late 80s"), Sexual and
  reproductive health ("4·3"), System ("mid-50s"), Tarantula ("a thousand"), Incoherence of the Philosophers (description 1095),
  Tokyo Story/Weimar Republic/Faulkner ("the following year"), West Siberian Plain ("70s and 80s").
- Subagents occasionally make stray calls to session tools (create_session, send_message, interrupt_session);
  they are denied and harmless.
