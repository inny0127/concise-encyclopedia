You build part of the Korean glossary for a Korean edition of an English encyclopedia. GROUP is given in your task.

1. Read `style_guide_ko.md` (rules for Korean names and headwords).
2. Read `data/ko/gloss_in/GROUP.txt`: 100 entries separated by "=== KEY:" lines, each with HEADWORD, PERSON,
   LINK TARGETS (Wikipedia titles linked from the entry) and the English ENTRY text.
3. Write ONE file `data/ko/gloss/GROUP.json`:
   {"heads": {KEY: {"ko": Korean headword, "orig": original form, "ko_sort": ko without spaces/punctuation}, ...},
    "terms": {"English term": {"ko": Korean form, "orig": original form or ""}, ...}}
   - "heads": one record for EVERY key. People inverted as in the style guide (아인슈타인, 알베르트); East Asian names in
     natural order (마오쩌둥); disambiguators stripped; "orig" = original Latin-script or East Asian script form,
     "" for common nouns and concepts with an established Korean word.
   - "terms": EVERY link target exactly as written (natural-order names: 알베르트 아인슈타인), plus every proper noun and
     every specialized term in the entry texts whose Korean form a translator could get wrong: people, places, peoples,
     languages, dynasties, organizations, events, treaties, works (with 『』 or 「」 as part of "ko"), titles and offices,
     technical terms (e.g. "palace examination" = 전시(殿試) -> ko "전시"). Key each term by the exact English surface
     form used in the text. Skip everyday words that any translator renders correctly.
   - Choose the sense that fits the entry (Monopoly in economics = 독점, the board game = 모노폴리).
   - Use standard forms: 국립국어원 외래어 표기법, 표준국어대사전, 두산백과, established Korean scholarly terms
     (Milky Way = 우리은하 for the galaxy, 은하수 for the band of light in the sky; Suprematism = 절대주의).
Write the JSON with one key per line. Write the file once, when complete. Do not call session tools
(create_session, send_message, etc.) and do not touch other files. Reply only with the number of heads and terms.
