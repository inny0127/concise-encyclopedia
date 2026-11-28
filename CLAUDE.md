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

All four original steps are done (2026-11-27):
1. Spelling: `scripts/americanize.py` changed 684 lowercase British forms to American (center, theater, gray, aluminum,
   -ization ...) plus 15 headwords (Theater, Jewelry, Gray, Check, 100 meters ...). Capitalized proper names keep their
   spelling (Labour Party, Globe Theatre, Sydney Harbour Bridge, Tyre in Lebanon, *Rumours*, *Neighbours*). Rerun it after
   any new condensing; it is idempotent.
2. Images: `show_image` now takes all eligible Level 1-3 images, then Level 4 people/visual categories by pageviews
   (`data/pageviews_core/`, from `pageviews_core.py`), up to `IMAGE_CAP = 2000`. 1,969 images are in the book; about 30
   were never fetched (Wikimedia rate limits). Rerun `fetch_images.py` to retry them.
3. Homographs are numbered by level, then key (Alcohol¹, Alcohol²): 263 entries.
4. `build_book.py` builds 3 volumes split at letter boundaries by text+image weight (I A–F 720 pp., II G–O 739 pp.,
   III P–Z 747 pp.), each in its own process (one process ran out of memory at 13.8 GB). Volume III ends with an index of
   all headwords with volume and page, taken from a Typst query of `<idx>` metadata. `--light` writes `vol*_light.pdf`
   with small images. The PDFs (~120 MB each) are gitignored.

Possible follow-ups: proofread a sample of pages; decide whether the headword index is worth its ~45 pages;
cover/title design; rotate the Wikimedia OAuth token (no longer needed).

## Korean edition (pilot 2026-11-27, full run done 2026-11-28)

- `style_guide_ko.md` (rules), `data/ko/glossary.json` (845 pilot terms from one Sonnet agent), `data/ko/PROMPT_ko.md`
  (translator prompt), `scripts/check_ko.py` (numbers incl. 만/억 and ranges, links, italics, polite endings),
  `scripts/build_book_ko.py` + `book/main_ko.typ` (가나다 order, ㄱㄴㄷ dividers, Noto Serif KR in `fonts/`, gitignored:
  download from github.com/notofonts/noto-cjk Serif/SubsetOTF/KR).
- Pilot: 157 entries, Haiku (all) and Sonnet (pilot_0, 49) -> `book/ko_pilot_haiku.pdf` (28 pp.), `ko_pilot_sonnet.pdf`.
  Both pass check_ko.py. Sonnet reads more naturally; tokens per entry: Sonnet ~2.7k, Haiku ~5.2k (Haiku agents wrote
  helper scripts and reread the whole glossary).
- Lessons for a full run: give each group only its own glossary subset; glossary must also cover proper nouns inside
  the text (e.g. "palace examination" = 전시, not 궁정 시험) and senses (Monopoly economics vs game, Chalk stick vs rock);
  link display text should translate the English display text, the glossary fixes only name spellings.

- **Full run: done (2026-11-28).** All 15,000 entries are in `data/ko/translated/` and pass `scripts/check_ko.py`
  except reviewed false alarms (numbers spelled out, ranges like 1950~60년대, quotations with ~습니다, "A*" asterisks).
  Pipeline (`scripts/ko_pipeline.py`; `status` names the next step):
  1. `gloss-prep`: 150 groups of 100 -> Opus agents (`data/ko/PROMPT_gloss.md`) -> `data/ko/gloss/`. Groups blocked by the
     content filter were split 10 ways (`split g_NNN 10`); that always worked. `verify` checks heads/terms per file.
  2. `merge`: votes per term; spacing-only and strong-majority (>=75%, >=4 votes) conflicts take the majority, title-bracket
     variants become "context" (each entry keeps its own group's form); the rest (2,856) went to 6 Opus agents
     (`data/ko/PROMPT_resolve.md`, `resolve_in` -> `resolve`). `gloss_resolved.json` holds manual overrides (포름산 etc.).
  3. `tr-prep`: 375 groups of 40 with per-entry glossary lines. Global terms match only as link targets, own-group terms,
     multiword terms or names of 4+ letters used mid-sentence (single common words like "It", "value" were noise).
     Sonnet agents (`data/ko/PROMPT_tr.md`), up to 20 at once; ~115k subagent tokens per group (~2.9k per entry).
  4. `scripts/ko_fix_links.py` (unwrap links the English lacks, restore dropped links from the glossary form), strip
     italics on Korean text, `assemble`, `check_ko.py`; remaining flags went to 3 Sonnet fix agents (`PROMPT_fix.md`,
     `fix_in/`, split by tr_out file so no two agents edit one file). 70 real fixes, ~150 false alarms.
  5. `build_book_ko.py --volumes 3 [--light]`: 제1권 ㄱ–ㅁ, 제2권 ㅂ–ㅇ, 제3권 ㅈ–ㅎ (about 650/820/700 pages); index
     (찾아보기) at the end of vol. 3, photo credits (사진 출처) in each volume. Light build takes ~2 minutes.
  - Translators found English-source bugs fixed during the run: Armor ("British spelling is armour", americanize now skips
    it) and four sonnet_023/haiku_043 entries with broken link fragments (Dementia, Democracy, Desert, Avant-garde).
  - Chemical-name convention: organic names 표준국어대사전 (메탄, 포름산), elements as in textbooks (플루오린), compounds spaced.

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
