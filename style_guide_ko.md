# 한국어판 번역 지침 (Korean edition style guide)

The Korean edition translates the finished English entries (`data/condensed/`). It adds no facts and drops
none. `style_guide.md` still governs content; this file governs the Korean text.

## Glossary first

`data/ko/glossary.json` maps every English headword and cross-reference target to one Korean form:
`{"English title": {"ko": "한국어 표제", "orig": "Original form"}}`. Translators must use it exactly, so
the same name is spelled the same way in all 15,000 entries. Terms not in the glossary follow the rules below.

## Spelling of names (외래어 표기법)

- Follow 국립국어원 외래어 표기법 and the forms used by 표준국어대사전 / 두산백과 for established names:
  아인슈타인, 셰익스피어, 뉴욕, 베이징, 마오쩌둥, 도쿄.
- Chinese names after 1911 and Japanese names: original-language reading (마오쩌둥, 도쿠가와 이에야스).
  Chinese names before 1911: Korean reading (공자, 진시황, 이백).
- Use the established Korean term for concepts (광합성, 민주주의, 산업 혁명), not a transliteration.

## Headword (`ko_headword`, `orig`, `ko_sort`)

- People from the West and elsewhere with a family name last: `성, 이름` (아인슈타인, 알베르트), like the
  English inverted form. East Asian and Korean names keep their natural order (마오쩌둥, 이순신).
  Rulers and single names stay as they are (루이 14세, 샤를마뉴, 공자).
- `orig`: the original form shown after the headword in the book, in Latin script, or the original script
  for East Asian names: `Albert Einstein`, `毛澤東`, `Mercury`. Empty when the headword is already Korean in origin.
- `ko_sort`: the headword with spaces and punctuation removed, used for 가나다 order.
- Strip disambiguators as in English (Mercury (planet) → 수성). Homographs are numbered by the build.

## Text

- Plain declarative 사전체: `~이다`, `~했다`. No honorifics, no `~습니다`.
- The opening stays a definitional fragment ending in a noun: `독일 태생의 이론물리학자.`
- Keep every number, date and unit exactly as in English (1,000 km, 1879년 3월 14일, 기원전 44년).
  Write dates the Korean way: `March 14, 1879` → `1879년 3월 14일`; `c. 500 BC` → `기원전 500년경`;
  `the 19th century` → `19세기`. Never add, round or convert a figure.
- Original spelling in parentheses only where it helps on first mention of a name not in the glossary:
  `하이젠베르크(Werner Heisenberg)`. Do not add it to glossary terms; the glossary already decides.
- Titles of works: books, newspapers and long works in 『 』, short works, paintings, films and songs in 「 」.
  Remove the English `*italics*` marks.
- Cross-references: keep the English target and translate only the display text, using the glossary:
  `[[Albert Einstein|Einstein]]` → `[[Albert Einstein|아인슈타인]]`. Keep every link the English entry has.
- Sub/superscripts stay Unicode (H₂O, 10⁶). Punctuation: Korean commas and periods; quotes as “ ”.
- Length: translate everything; Korean length follows naturally (no word limits).

## Fixed conventions (added during the full run)

- Chemical names: 표준국어대사전 forms, not the newer 대한화학회 forms: 메탄, 에탄, 알칸, 알킨, 알데히드, 카르복실산.
- Work titles are bare in headwords (아이네이스); 『 』 or 「 」 appear in running text and in glossary terms.
