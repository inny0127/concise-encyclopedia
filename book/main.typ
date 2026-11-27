// Concise Encyclopedia: B5 two-column layout.
#let data = json(sys.inputs.at("data", default: "entries.json"))
#let col-width = (176mm - 18mm - 14mm - 5mm) / 2
#let max-img-height = 40mm

#set document(title: "A Concise Encyclopedia", author: "Compiled from Wikipedia and Grokipedia")
#set text(font: "Libertinus Serif", size: 8.6pt, lang: "en", hyphenate: true, number-type: "old-style")
#set par(justify: true, leading: 0.48em, spacing: 0.48em)

// ---------- Front matter ----------
#set page(width: 176mm, height: 250mm, margin: (inside: 18mm, outside: 14mm, top: 20mm, bottom: 18mm))

#page(header: none)[
  #v(55mm)
  #align(center)[
    #text(size: 26pt, weight: "bold", tracking: 0.04em)[A CONCISE]\
    #v(2mm)
    #text(size: 26pt, weight: "bold", tracking: 0.04em)[ENCYCLOPEDIA]
    #v(10mm)
    #line(length: 40%, stroke: 0.6pt)
    #v(6mm)
    #if data.at("volume", default: "") != "" [
      #text(size: 14pt, weight: "bold")[#data.volume]\
      #v(2mm)
      #text(size: 13pt)[#data.span]
      #v(6mm)
    ]
    #text(size: 11pt, style: "italic")[#data.entries.len() entries]
  ]
]

#page(header: none)[
  #set text(size: 8pt)
  #set par(spacing: 0.9em)
  #v(1fr)
  *About this edition.* Entries are condensed from the English Wikipedia, cross-checked against
  Grokipedia, with life dates for people taken from Wikidata. Topics are drawn from Wikipedia's
  Vital Articles lists. Words set in #smallcaps[small capitals] refer to entries of their own.

  Text is adapted from Wikipedia articles, available under the Creative Commons
  Attribution-ShareAlike 4.0 License (CC BY-SA 4.0); this adaptation is shared under the same terms.
  Image credits appear at the end of the volume. Printed for personal use.
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
  else { smallcaps(s.v) }
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
        #text(weight: "bold", size: 9.2pt)[#e.head#if hom > 0 { super(str(hom)) }]#metadata(e.head)<entry>#context [#metadata((h: e.head, n: hom, s: e.sort, p: counter(page).get().first()))<idx>]
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
    #text(size: 12pt, weight: "bold")[Index of entries]
    #h(1fr) #text(size: 7pt, style: "italic")[Volume and page]
  ])
  set text(size: 6pt)
  set par(justify: false, spacing: 0.2em, hanging-indent: 0.8em)
  for x in index [
    #x.h#if x.n > 0 { super(str(x.n)) } #h(1fr) #x.v~#x.p\
  ]
}

// ---------- Image credits ----------
#pagebreak()
#set page(columns: 1)
#block(width: 100%)[#text(size: 12pt, weight: "bold")[Image credits]]
#set text(size: 6.5pt)
#set par(justify: false, spacing: 0.35em)
#for c in data.credits [
  #text(weight: "bold")[#c.head#if c.at("hom", default: 0) > 0 { super(str(c.hom)) }]: #c.artist (#c.license)\
]
