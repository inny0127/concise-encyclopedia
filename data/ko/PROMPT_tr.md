You translate one group of encyclopedia entries from English into Korean. GROUP is given in your task.

1. Read `style_guide_ko.md` and follow it exactly.
2. Read `data/ko/tr_in/GROUP.txt`: 40 entries separated by "=== KEY:" lines. Each has HEADWORD (English = Korean),
   LEVEL, a GLOSSARY of the names and terms in that entry (English = Korean), and the English ENTRY.
3. Write ONE file `data/ko/tr_out/GROUP.json`: a JSON array, one object per line, of {"key": KEY exactly as given,
   "entry": the Korean translation of ENTRY}.
Rules: translate everything and add nothing. Use the GLOSSARY form for every name and term it lists (the same name
must be spelled the same way across the book). Keep every number and date exactly, in Korean date order; 만/억 units
are fine (6 million = 600만). Keep every [[Target|text]] link: the English Target stays unchanged, the display text is a
natural Korean translation of the English display text (bare [[Target]] becomes [[Target|Korean]]). Remove *italics*
marks; put work titles in 『 』 (books, long works) or 「 」 (short works, films, paintings, songs) unless the glossary
form already has them. Plain 사전체 (~이다, ~했다). The opening stays a definitional fragment ending in a noun.
Write the file once, when complete. Do not call session tools or touch other files. Reply only with the count written.
