# Entity-type curation: instructions for the annotator

You get one batch file `curation/type_batches/tbatch_NNN.json`: up to 200 entries of the
printed index of persons and places to Regesta Imperii XIV,1 (digests of King Maximilian I.,
1493–1495). Each entry shows its index label, headword and sub-entry, spellings, the type a
rule-based parser guessed (often wrong), up to three excerpts from digests around the entity's
mention string, and notes left by the annotators who located those mentions.

Decide for EVERY entry what kind of thing it is and write one JSON object per line to
`curation/type_batches/tbatch_NNN.types.jsonl`:

```json
{"entity_id": "RI14-1-E2458", "type": "person", "subtype": "individual", "confidence": "high", "note": null}
```

## Types and subtypes

| type | subtype | what it is | examples |
|---|---|---|---|
| person | individual | one human being, named or referred to by title | "Liechtenstein, Paul von, Hofmarschall"; "Albrecht IV., Hg von Bayern"; "Trient, Bf Ulrich von Liechtenstein"; "Wien, St. Dorothea, Propst Bernhard" |
| place | settlement | city, town, village, as a location | "Wien"; "Aach"; "Frankfurt, Oberrad, Dorf" |
| place | region | geographical area or landscape as a location | "Piemont"; "Ligurien"; "Alpen"; "Tirol" when meaning the land |
| place | site | building, castle, church, river, pass, mountain, as a location | "Runkelstein, Burg"; "Wien, St. Stephan" (the church); "Achenpaß" |
| other | family | a family, dynasty or lineage as such | "Liechtenstein zu Murau, Herren von"; "Agresta, Familie" |
| other | group | a collective of people | "Aach, Juden"; "Wien, Bürger"; "Venedig, Gesandte"; "Reichsstände"; "Türken" |
| other | institution | a corporate body or organisation that acts | "Wien, Regiment"; "Innsbruck, Raitkammer"; "Augsburg, Domkapitel"; "Wien, Stadt" (the civic community as party); a monastery as an institution |
| other | office | an office or dignity named without its holder | "Salzburg, Dompropst"; "Thann, Vogt"; "Erlau, Bf" (when no bishop is named) |
| other | territory | a political unit: duchy, county, kingdom, bishopric as a state, lordship | "Mailand, Hgtm"; "Zutphen, Gft"; "Neapel, Kgr"; "Falkenstein, Hft"; "Trient, Btm" |
| other | property | land, rights, revenues, goods | "Aichach, Güter"; "Heilbronn, Fischwasser"; "Wullersdorf, Ungeld"; "Hallein, Salz"; "Jahrsdorf, Zehent"; "Blutbann" |
| other | event | a treaty, peace, diet, battle, assembly | "Senlis, Friede von"; "Worms, Reichstag"; "Vercelli, Friede" |
| other | object | a movable thing, document, relic, work | "Wappen"; "Urkunde"; "Reliquien" |

## Rules

* Decide from the index entry first, then confirm with the excerpts: the mention string shows
  how the entity is referred to in the texts. A "person" has a given name or a personal title
  ("Bf Ulrich", "Gf Eberhard d. Ä.", "Abt Leonhard"); an office without a name is `office`.
* Bishoprics, duchies and the like are `territory`, not `place`, when the entry means the
  political unit (Btm, Hgtm, Gft, Kgr, Hft, Fstm, Lgft). The town of the same name is a
  separate entry and is `place`.
* A castle or church as a location is `place / site`; a monastery or chapter that acts,
  receives, or holds rights is `institution`. If the excerpts show both, choose by the
  excerpts; if unclear, `institution` for monasteries and chapters, `site` for castles and
  churches.
* "Stadt" as sub-entry of a place ("Wien, Stadt") is the civic community as a party:
  `institution`. The bare place headword ("Wien") stays `place / settlement`.
* Groups of office holders ("Räte", "Gesandte", "Hauptleute", "Juden", "Bürger") are `group`.
* Rulers filed under their given name ("Ferdinand I., Kr", "Bona Sforza") are `person`.
* `confidence`: `high` when the entry and excerpts leave no doubt, `medium` when the entry
  is ambiguous but the excerpts decide, `low` when you had to guess. Use `note` for
  anything odd: a duplicate entry, an index error the annotators flagged, an entry that
  mixes two kinds of thing.

Work through every entry in the batch. One JSON object per line, no comments.

## Second pass (residue batches `tbatch_rNNN.json`)

These entries were decided once (`first_pass`) and come back because the decision was not
confident, because the entry is a "Stadt / Markt / Gemeinde / Dorf" sub-entry, or as a random
quality sample of confident changes. Decide them afresh with the same taxonomy; agree with the
first pass when it is right, overrule it when it is wrong. One firm rule for consistency,
regardless of what the excerpts suggest:

* sub-entry **Stadt, Markt, Gemeinde** under a place headword = `other / institution`
  (the index uses this sub-entry for the community as a legal person; the bare headword is the
  location);
* sub-entry **Dorf** = `place / settlement`;
* **Bürger, Juden, Räte, Gesandte, Untertanen** and similar collectives = `other / group`.

Confidence in the second pass means confidence in your own decision.
