You translate one group of encyclopedia entries from English into Korean. GROUP and OUTDIR are given in your task.

1. Read `style_guide_ko.md` and follow it exactly.
2. Read `data/ko/glossary.json` (English term -> {"ko","orig","ko_sort"}). Every headword and every [[link target]] is in it.
3. Read `data/ko/GROUP.txt` (entries separated by "=== KEY:" lines; each has LEVEL, PERSON, HEADWORD and ENTRY).
4. Write ONE file `OUTDIR/GROUP.json`: a JSON array, one object per line, of
   {"key": KEY exactly as given, "ko_headword": glossary[HEADWORD].ko, "orig": glossary[HEADWORD].orig,
    "ko_sort": glossary[HEADWORD].ko_sort, "entry": the Korean translation of ENTRY}.
Rules for "entry": translate everything and add nothing; keep every number and date exactly (Korean date order);
keep every [[Target|text]] link with the English Target unchanged and Korean display text that uses the glossary form
of Target (a natural-order name may be shortened to the family name, e.g. [[Albert Einstein|아인슈타인]]);
remove *italics* marks and put work titles in 『 』 or 「 」; plain 사전체 (~이다); the opening is a noun-ending
definitional fragment. Write the file once, when complete. Do not call session tools or touch other files.
Reply only with the count written.
