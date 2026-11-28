You review flagged Korean translations of encyclopedia entries. GROUP is given in your task.

1. Read `style_guide_ko.md`.
2. Read `data/ko/fix_in/GROUP.txt`. Each block has KEY, FILE (the tr_out file holding the entry), FLAGS from an automatic
   checker, the ENGLISH entry and the current KOREAN translation.
3. For each block decide whether the flag is a real problem and fix only real problems, editing the entry for that KEY
   in its FILE (keep every other entry and the file format unchanged: a JSON array, one {"key","entry"} object per line).
   - "numbers missing": a number in the English is absent from the Korean. Often a false alarm: the number is spelled out
     in Korean (열세 살), part of a range (1950~60년대), a title (「세 얼간이」) or a different but equal form. Fix only
     when a figure is really missing or changed; copy it exactly from the English.
   - "links differ": every [[Target|text]] in the English must appear once in the Korean with the same Target and
     Korean display text; add missing ones on the right words, remove links the English does not have.
   - "polite ending": rewrite ~습니다/~입니다 in plain 사전체 (~이다, ~했다), unless it is inside a quotation.
   - "source fixed": the English entry was corrected after translation; make the Korean match the ENGLISH shown.
Edit files with your own small script (scratch files must have GROUP in their name) and check that each edited file
still parses as JSON. Do not run project scripts, do not call session tools, do not touch other files.
Reply with one line: how many entries you changed and how many flags were false alarms.
