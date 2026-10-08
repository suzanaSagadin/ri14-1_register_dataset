"""Step 8: consistency checks; the build fails on any violation."""
import collections
import csv

from .common import DATA, read_jsonl


def run():
    entities = read_jsonl(DATA / "entities.jsonl")
    digests = read_jsonl(DATA / "digests.jsonl")
    mentions = read_jsonl(DATA / "mentions.jsonl")
    problems = []
    ids = [e["id"] for e in entities]
    if len(ids) != len(set(ids)):
        problems.append("duplicate entity ids")
    labels = collections.Counter((e["type"], e["label"], e.get("region")) for e in entities)
    dup = [k for k, v in labels.items() if v > 1]
    if dup:
        problems.append(f"duplicate (type,label,region): {dup[:5]}")
    did = {d["id"]: d for d in digests}
    for e in entities:
        if not e["digests"]:
            problems.append(f"{e['id']} has no digests")
        for d in e["digests"]:
            if d not in did:
                problems.append(f"{e['id']} -> unknown digest {d}")
    eid = {e["id"]: e for e in entities}
    for d in digests:
        for t, lst in d["entities"].items():
            for x in lst:
                if x not in eid or eid[x]["type"] != t:
                    problems.append(f"{d['id']} -> bad entity {x} under {t}")
    with open(DATA / "links.csv", encoding="utf-8") as f:
        n_links = sum(1 for _ in csv.DictReader(f))
    n_expected = sum(len(e["digests"]) for e in entities)
    if n_links != n_expected:
        problems.append(f"links.csv has {n_links} rows, expected {n_expected}")
    # mentions: one row per person link, offsets must reproduce the string
    person_links = {(d["id"], x) for d in digests for t in d["entities"] for x in d["entities"][t]}
    seen = set()
    for m in mentions:
        key = (m["digest_id"], m["entity_id"])
        if key not in person_links:
            problems.append(f"mention for unknown link {key}")
        seen.add(key)
        if m["start"] is not None:
            if did[m["digest_id"]]["text"][m["start"]:m["end"]] != m["text"]:
                problems.append(f"mention offsets do not match text in {m['digest_id']} / {m['entity_id']}")
    if seen != person_links:
        problems.append(f"mentions cover {len(seen)} of {len(person_links)} person links")
    split_ids = set()
    for name in ("catalogue_digests.txt", "test_digests.txt"):
        for line in open(DATA / "splits" / name, encoding="utf-8"):
            x = line.strip()
            if x in split_ids:
                problems.append(f"digest {x} in both splits")
            if x not in did:
                problems.append(f"split id {x} unknown")
            split_ids.add(x)
    if problems:
        raise SystemExit("validation failed:\n  " + "\n  ".join(problems[:20]))
    print("  validation passed")
