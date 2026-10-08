"""Step 5: link entities to regests by register number (both directions)."""
import csv

from .common import DATA, REVIEW, read_jsonl, write_jsonl


def run():
    entities = read_jsonl(DATA / "entities.jsonl")
    regests = read_jsonl(DATA / "digests.jsonl")
    by_nr = {r["nr"]: r for r in regests}
    missing = []
    links = []
    for ent in entities:
        ids = []
        for nr in ent["digests"]:
            r = by_nr.get(nr)
            if r is None:
                missing.append((ent["id"], nr))
                continue
            if ent["id"] not in r["entities"][ent["type"]]:
                r["entities"][ent["type"]].append(ent["id"])
            ids.append(r["id"])
            links.append((r["id"], ent["id"], ent["type"]))
        ent["digests"] = ids
    REVIEW.mkdir(exist_ok=True)
    with open(REVIEW / "missing_regest_numbers.tsv", "w", encoding="utf-8") as f:
        f.write("entity_id\tregister_number\n")
        for eid, nr in missing:
            f.write(f"{eid}\t{nr}\n")
    if missing:
        print(f"  WARNING: {len(missing)} register number(s) not in RI_14.csv, dropped: {missing}")
    write_jsonl(DATA / "entities.jsonl", entities)
    write_jsonl(DATA / "digests.jsonl", regests)
    with open(DATA / "links.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["digest_id", "entity_id", "entity_type"])
        w.writerows(sorted(set(links)))
    print(f"  links: {len(set(links))}, digests with >=1 person: "
          f"{sum(1 for r in regests if r['entities']['person'])}")
