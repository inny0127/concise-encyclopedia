You settle conflicts in the Korean glossary for a Korean edition of an English encyclopedia. GROUP is given in your task.

1. Read `style_guide_ko.md`.
2. Read `data/ko/resolve_in/GROUP.txt`. Each line is: English term, TAB, the Korean forms that different glossary
   groups chose, with how many groups chose each: `Igor Stravinsky<TAB>이고르 스트라빈스키 (4) | 이고리 스트라빈스키 (2)`.
3. Write ONE file `data/ko/resolve/GROUP.json` with one key per line, a record for EVERY term in the file:
   {"English term": {"ko": "chosen form", "orig": "original form or empty"}, ...}  or  {"English term": "context"}.

How to decide:
- Same referent, spelling or wording variants (이고르/이고리, 중앙 정보국/중앙정보국(CIA), 양쯔강/창장강, 태국/타이):
  pick ONE form, the standard one: 국립국어원 외래어 표기법 and 표준국어대사전, then 두산백과 and established usage.
  Votes are a hint, not the rule. Prefer the familiar established form (태국, 스페인, 양쯔강, 이메일, 소고기), no
  parenthetical abbreviations in "ko" (NASA = 미국 항공 우주국), spaced compound proper nouns as 표준국어대사전 spaces them.
  US states, provinces etc. take 주 where the term names the state (텍사스주, 하와이주) unless variants show other senses.
- Chemical names: 표준국어대사전 forms (메탄, 에탄, 알칸, 알킨, 알데히드, 포름알데히드, 카르복실산, 포름산), not
  대한화학회 forms (폼알데하이드, 폼산). Compound names written solid: 염화나트륨, 수산화나트륨.
- Fixed choices: Korean War = 6·25 전쟁; Sea of Japan = 동해 (entries quoting what Japan calls it are handled by the
  translator); War of the Pacific = 남아메리카 태평양 전쟁 and Pacific War = 태평양 전쟁; Pancreas = 이자;
  Spain = 스페인; Milky Way = 우리은하 (galaxy).
- Use "context" ONLY when the variants are different senses or legitimately different renderings that depend on the
  entry: a work title vs the thing (Avatar = 아바타 / 아바타라 / 「아바타」), a word with several meanings
  (binary = 이진법 / 이부 형식, Beef, Moonlight, Jupiter planet vs god vs 「주피터」), adjective vs noun (Babylonian),
  or a short term that names different people or things (Copenhagen vs a battle, Mongols as people vs army).
  Each entry then keeps the form its own glossary group chose, which was chosen with that entry's text in view.
- "orig": the original Latin-script or East Asian form for names (Igor Stravinsky), "" for common nouns and concepts.

Any scratch or helper files must have GROUP in their name (e.g. scratchpad/GROUP_work.py). Write the output file once,
when complete. Do not call session tools (create_session, send_message, etc.) and do not touch other files.
Reply only with the number of terms decided and how many are "context".
