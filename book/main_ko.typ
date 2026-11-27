// Concise Encyclopedia: B5 two-column layout.
#let data = json(sys.inputs.at("data", default: "entries.json"))
#let col-width = (176mm - 18mm - 14mm - 5mm) / 2
#let max-img-height = 40mm

#set document(title: "간추린 백과사전", author: "위키백과와 그로키피디아에서 편집")
#set text(font: ("Libertinus Serif", "Noto Serif KR"), size: 8.4pt, lang: "ko", hyphenate: false)
#set par(justify: true, leading: 0.62em, spacing: 0.62em)

// ---------- Front matter ----------
#set page(width: 176mm, height: 250mm, margin: (inside: 18mm, outside: 14mm, top: 20mm, bottom: 18mm))

#page(header: none)[
  #v(55mm)
  #align(center)[
    #text(size: 28pt, weight: "bold", tracking: 0.1em)[간추린 백과사전]
    #v(10mm)
    #line(length: 40%, stroke: 0.6pt)
    #v(6mm)
    #if data.at("volume", default: "") != "" [
      #text(size: 14pt, weight: "bold")[#data.volume]\
      #v(2mm)
      #text(size: 13pt)[#data.span]
      #v(6mm)
    ]
    #text(size: 11pt)[#data.entries.len()개 항목#if data.at("pilot", default: false) [ · 시범판]]
  ]
]

#page(header: none)[
  #set text(size: 8pt)
  #set par(spacing: 0.9em)
  #v(1fr)
  *이 판에 대하여.* 항목은 영어 위키백과를 바탕으로 그로키피디아와 대조해 간추린 영어판을 한국어로 옮긴 것이다.
  인물의 생몰 연월일은 위키데이터를 따랐다. 밑줄 친 말은 따로 항목이 있음을 뜻한다.
  사진 출처는 각 권 끝에 실었다. 본문은 위키백과 문서를 각색한 것으로 CC BY-SA 4.0 라이선스를 따르며, 이 판도 같은 조건으로 공유한다.
  개인 소장용으로 인쇄했다.
]

// ---------- Body ----------
#pagebreak(to: "odd")
#counter(page).update(1)

#let guide-header = context {
  let pg = here().page()
  let on-page = query(<entry>).filter(m => m.location().page() == pg)
  if on-page.len() > 0 {
    let num = counter(page).display()
    set text(size: 8pt)
    block(width: 100%, inset: (bottom: 1.6mm), stroke: (bottom: 0.4pt))[
      #if calc.even(pg) {
        [#num #h(1fr) #text(weight: "bold")[#on-page.first().value]]
      } else {
        [#text(weight: "bold")[#on-page.last().value] #h(1fr) #num]
      }
    ]
  }
}

#set page(columns: 2, header: guide-header, header-ascent: 35%)
#set columns(gutter: 5mm)

#let run(segs) = for s in segs {
  if s.t == "text" { s.v }
  else if s.t == "ital" { emph(s.v) }
  else { underline(stroke: 0.3pt, offset: 1.6pt, s.v) }
}

#let letter-divider(l) = block(above: 1.4em, below: 0.4em, breakable: false, sticky: true, width: 100%)[
  #set align(center)
  #block(below: 1.2mm, text(size: 22pt, weight: "bold")[#l])
  #line(length: 30%, stroke: 0.5pt)
]

#let entry(e) = block(above: 0.85em, below: 0pt, width: 100%)[
  #if e.image != none {
    // sticky: the picture always stays with the headword that follows it
    block(breakable: false, sticky: true, width: 100%, below: 0.6em)[
      #align(center, if e.image.ratio * col-width * 0.8 > max-img-height {
        image(e.image.path, height: max-img-height)
      } else {
        image(e.image.path, width: 80%)
      })
    ]
  }
  #for (i, p) in e.paras.enumerate() {
    if i == 0 {
      par(first-line-indent: 0pt)[
        #let hom = e.at("hom", default: 0)
        #text(weight: "bold", size: 9.2pt)[#e.head#if hom > 0 { super(str(hom)) }]#if e.at("orig", default: "") != "" [ #text(size: 7.6pt)[#e.orig]]#metadata(e.head)<entry>#context [#metadata((h: e.head, n: hom, s: e.sort, p: counter(page).get().first()))<idx>]
        #if e.dates != "" [ #e.dates]
        #h(0.25em)#run(p)
      ]
    } else {
      par(first-line-indent: 1em)[#run(p)]
    }
  }
]

#let last-letter = none
#for e in data.entries {
  if e.letter != last-letter { letter-divider(e.letter) }
  last-letter = e.letter
  entry(e)
}

// ---------- Index (last volume) ----------
#let index = data.at("index", default: ())
#if index.len() > 0 {
  pagebreak()
  set page(columns: 4, header: none)
  set columns(gutter: 3.5mm)
  place(top, float: true, scope: "parent", block(width: 100%, below: 4mm)[
    #text(size: 12pt, weight: "bold")[찾아보기]
    #h(1fr) #text(size: 7pt, )[권·쪽]
  ])
  set text(size: 6pt)
  set par(justify: false, spacing: 0.2em, hanging-indent: 0.8em)
  for x in index [
    #x.h#if x.n > 0 { super(str(x.n)) } #h(1fr) #x.v;권~#x.p\
  ]
}


// ---------- Image credits ----------
#if data.credits.len() > 0 {
  pagebreak()
  set page(columns: 1, header: none)
  block(width: 100%)[#text(size: 12pt, weight: "bold")[사진 출처]]
  set text(size: 6.5pt)
  set par(justify: false, spacing: 0.35em)
  for c in data.credits [
    #text(weight: "bold")[#c.head#if c.at("hom", default: 0) > 0 { super(str(c.hom)) }]: #c.artist (#c.license)\
  ]
}
