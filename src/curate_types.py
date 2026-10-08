"""Step 3b: apply curated entity types on top of the parser's classification.

`curation/type_fixes.jsonl` holds one row per entity:
  {"entity_id", "type": person|place|other, "subtype", "confidence", "note", "annotator", "date"}
The row sets `type` and `subtype`; the parser's own decision stays in
`classification` for the record, and `type_source` says who decided.
"""
import collections

from .common import ROOT, DATA, read_jsonl, write_jsonl

FIXES = ROOT / "curation" / "type_fixes.jsonl"
SUBTYPES = {"person": {"individual"},
            "place": {"settlement", "region", "site"},
            "other": {"family", "group", "institution", "office", "territory", "property", "event", "object"}}


def run():
    entities = read_jsonl(DATA / "entities.jsonl")
    for e in entities:
        e.setdefault("subtype", None)
        e.setdefault("type_source", "parser")
    if not FIXES.exists():
        write_jsonl(DATA / "entities.jsonl", entities)
        print("  no type curation file, parser types kept")
        return
    by_id = {e["id"]: e for e in entities}
    changed, problems = collections.Counter(), []
    for f in read_jsonl(FIXES):
        e = by_id.get(f["entity_id"])
        if e is None:
            problems.append(f"unknown entity {f['entity_id']}"); continue
        if f["type"] not in SUBTYPES or f.get("subtype") not in SUBTYPES[f["type"]]:
            problems.append(f"{f['entity_id']}: bad type/subtype {f.get('type')}/{f.get('subtype')}"); continue
        if e["type"] != f["type"]:
            changed[(e["type"], f["type"])] += 1
        e["type"], e["subtype"] = f["type"], f["subtype"]
        e["type_source"] = f.get("annotator", "curated")
        e["type_confidence"] = f.get("confidence")
        e["type_note"] = f.get("note") or None
    write_jsonl(DATA / "entities.jsonl", entities)
    if problems:
        print(f"  WARNING {len(problems)} type fixes not applied: " + "; ".join(problems[:5]))
    n = sum(1 for e in entities if e["type_source"] != "parser")
    print(f"  types curated for {n} entities; type changes {dict(changed)}")
