#!/usr/bin/env python3
"""Derive the person-reconciliation task from this dataset.

    python tools/make_reconciliation_task.py --out <folder>

Writes <folder>/catalogue.jsonl (the persons of the catalogue digests with
profiles built only from those digests), <folder>/test.jsonl (the test
digests with their person mentions as input and the answer key as gold) and
<folder>/pilot_50.txt (50 test digests chosen so that rare and new persons
are present). The split comes from data/splits/; this script only turns it
into task files. The use case repository ships the result.
"""
import argparse
import collections
import json
import random
from pathlib import Path

DATASET = Path(__file__).resolve().parent.parent
PILOT_SEED, PILOT_SIZE = 20261007, 50


def read_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def write_jsonl(p, rows):
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="folder for catalogue.jsonl, test.jsonl, pilot_50.txt")
    a = ap.parse_args()
    ds = DATASET / "data"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    entities = {e["id"]: e for e in read_jsonl(ds / "entities.jsonl")}
    digests = {d["id"]: d for d in read_jsonl(ds / "digests.jsonl")}
    mentions = {(m["digest_id"], m["entity_id"]): m for m in read_jsonl(ds / "mentions.jsonl")}
    cat_ids = (ds / "splits" / "catalogue_digests.txt").read_text(encoding="utf-8").split("\n")
    test_ids = (ds / "splits" / "test_digests.txt").read_text(encoding="utf-8").split("\n")
    cat_ids = [x for x in cat_ids if x]
    test_ids = [x for x in test_ids if x]

    # catalogue: every person seen in a catalogue digest, profile from those digests only
    catalogue = {}
    for did in cat_ids:
        d = digests[did]
        for pid in d["entities"]["person"]:
            e = entities[pid]
            c = catalogue.setdefault(pid, {
                "id": pid, "label": e["label"], "headword": e["headword"], "subentry": e["subentry"],
                "variants": e["variants"], "aliases": e["aliases"],
                "profile": {"digests": [], "places": [], "date_min": None, "date_max": None,
                            "mention_forms": [], "examples": []},
            })
            p = c["profile"]
            p["digests"].append(did)
            if d["place"] and d["place"] not in p["places"]:
                p["places"].append(d["place"])
            p["date_min"] = min(filter(None, [p["date_min"], d["date_start"]]))
            p["date_max"] = max(filter(None, [p["date_max"], d["date_end"]]))
            m = mentions.get((did, pid))
            if m and m.get("text") and m["text"] not in p["mention_forms"]:
                p["mention_forms"].append(m["text"])
            if len(p["examples"]) < 2 and m and m.get("text") and m.get("kind") == "direct":
                p["examples"].append({"digest_id": did, "date": d["date_start"], "text": d["text"][:300]})
    write_jsonl(out / "catalogue.jsonl", sorted(catalogue.values(), key=lambda c: c["id"]))

    # test: digests with gold; links the curation marked absent are listed but not scored
    test, stats = [], collections.Counter()
    for did in test_ids:
        d = digests[did]
        gold = []
        for pid in d["entities"]["person"]:
            e, m = entities[pid], mentions.get((did, pid))
            known = pid in catalogue
            absent = bool(m and m.get("verdict") == "absent")
            n_cat = len(catalogue[pid]["profile"]["digests"]) if known else 0
            gold.append({"entity_id": pid if known else None, "register_entity_id": pid, "label": e["label"],
                         "status": "known" if known else "new",
                         "catalogue_digests": n_cat,
                         "mention": {"text": m["text"], "kind": m["kind"]} if m and m.get("text") else None,
                         "absent_in_text": absent})
            stats["absent" if absent else gold[-1]["status"]] += 1
        # input for the system: the mention strings, each once; the answer key stays in `gold`
        inputs, seen = [], set()
        for g in gold:
            if g["mention"] and not g["absent_in_text"] and g["mention"]["text"] not in seen:
                inputs.append({"text": g["mention"]["text"], "kind": g["mention"]["kind"]}); seen.add(g["mention"]["text"])
        test.append({"id": did, "nr": d["nr"], "date_start": d["date_start"], "date_end": d["date_end"],
                     "place": d["place"], "text": d["text"], "ri_url": d["ri_url"], "mentions": inputs, "gold": gold})
    write_jsonl(out / "test.jsonl", test)

    # pilot: 50 test digests, stratified so that rare and new persons are present
    rng = random.Random(PILOT_SEED)
    scorable = [t for t in test if any(not g["absent_in_text"] for g in t["gold"]) and 1 <= len(t["gold"]) <= 6]
    def has(t, pred):
        return any(pred(g) for g in t["gold"] if not g["absent_in_text"])
    pools = [
        [t for t in scorable if has(t, lambda g: g["status"] == "new")],
        [t for t in scorable if has(t, lambda g: g["status"] == "known" and g["catalogue_digests"] <= 4)],
        scorable,
    ]
    chosen, seen = [], set()
    for pool, want in zip(pools, (18, 18, PILOT_SIZE)):
        pool = [t for t in pool if t["id"] not in seen]
        rng.shuffle(pool)
        for t in pool[:max(0, want - (len(chosen) if want == PILOT_SIZE else 0))]:
            if len(chosen) >= PILOT_SIZE:
                break
            chosen.append(t); seen.add(t["id"])
    chosen.sort(key=lambda t: test_ids.index(t["id"]))
    (out / "pilot_50.txt").write_text("\n".join(t["id"] for t in chosen) + "\n", encoding="utf-8")
    pilot_links = collections.Counter()
    for t in chosen:
        for g in t["gold"]:
            if g["absent_in_text"]:
                continue
            pilot_links["new" if g["status"] == "new" else
                        ("known, 1-4 catalogue digests" if g["catalogue_digests"] <= 4 else "known, 5+ catalogue digests")] += 1
    print(f"catalogue persons {len(catalogue)}, test digests {len(test)}, gold links {dict(stats)}")
    print(f"pilot: {len(chosen)} digests, links {dict(pilot_links)}")


if __name__ == "__main__":
    main()
