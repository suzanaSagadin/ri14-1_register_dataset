# Mention curation: instructions for the annotator

You get one batch file `curation/batches/batch_NNN.json`: a list of digests
(German regest texts from Regesta Imperii XIV,1). Each digest lists the entities
the printed index attaches to it, with the string an automatic finder located
(`auto`). Entities with `"review": true` must be decided; the others are context
only (you may still correct one if it is plainly wrong).

Write one JSON object per reviewed entity, one per line, to
`curation/batches/batch_NNN.fixes.jsonl` (same number as the batch):

```json
{"digest_id": "RI XIV,1 n. 753", "entity_id": "RI14-1-P0094", "verdict": "confirmed",
 "kind": "direct", "text": "Wilhelm von Aw", "occurrence": 1, "note": null}
```

## Fields

* `verdict`:
  * `confirmed`: the automatic string is right (copy it into `text`).
  * `corrected`: the automatic string is wrong or badly cut; `text` holds the right one.
  * `filled`: the finder found nothing, you found the mention.
  * `absent`: the entity is not referred to in this text at all (index error, or the
    reference is only in the archival note). `text` is null.
* `kind`: `direct` when the entity is named (any spelling), `indirect` when it is referred
  to by title, office or description only ("der Kg von Frankreich", "dem Papst",
  "der Hofstaat der Kgin", "das niederösterreichische Regiment" for an institution).
  Null for `absent`.
* `text`: the mention **copied verbatim** from the digest `text`, character for character
  (umlauts, ß, abbreviations, editor's parentheses). It is validated as a substring; a row
  whose string is not in the text is rejected.
* `occurrence`: if the exact same string occurs more than once in the text, the 1-based
  index of the occurrence you mean (default 1). Choose the first occurrence that is the
  fullest form of the name.
* `note`: short free text only when something is odd (suspected index error, two
  persons with the same name, uncertainty). Otherwise null.

## What the string covers

The name phrase, including titles and name particles that belong to it, and nothing else:

* persons: `Gf Ulrich von Arco`, `Bf Friedrich von Augsburg`, `Hg Albrecht von Bayern`,
  `Christoph von Liechtenstein (-Nikolsburg)`, `Kr Friedrichs III.`, `Ebf Berthold`.
  Keep title abbreviations (Hg, Gf, Bf, Kg, Kr, Ebf, Mgf, Pfgf, Dr., Ritter) when they
  stand directly before the name. Keep ordinals and editor's additions in parentheses
  when they are inside the phrase.
* not included: articles and possessives (`der`, `dem`, `seinem`), role phrases that are
  not part of the name (`seinem Sekretär`, `KMs Rat`, `Landvogt im Elsaß`), and anything
  after the name.
* indirect mentions: the referring expression without the article: `Kg von Frankreich`,
  `Papst`, `Hofstaat der Kgin`.
* places: the place name as written, without preposition: `Wienn`, `Worms`, `Innsbruck`.
  A place named only as the issue place at the end of the text ("Wienn Mittichen nach …")
  counts as direct.
* institutions and other entities: the noun phrase as written: `niederösterreichische
  Regiment`, `Juden zu Worms`, `Schloß und Markt Absperg`.
* if a person is named more than once, take the first occurrence of the fullest form.

## Decisions

* The index decides identity. If the text says "Hg Albrecht von Bayern" and the index
  attaches Albrecht IV., mark it direct with that string; do not second-guess the editor.
* If an entity is truly not in the text (sometimes the index refers to the archival note
  or a footnote not in `text`), write `absent` with a note.
* Entities of type `other` that are offices or things ("Salzburg, Dompropst") are usually
  mentioned as that office: `Dompropst von Salzburg` is direct.
* Do not invent strings. When in doubt between two spans, take the shorter one that still
  contains the name.

Work through every digest in the batch, in order. Do not skip reviewed entities. Keep the
output file to exactly one JSON object per line, no comments, no trailing text.
