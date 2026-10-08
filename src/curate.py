"""Step 7: apply curated mention fixes on top of the automatic pass.

`curation/mention_fixes.jsonl` holds one row per reviewed (digest, entity) link:
  {"digest_id", "entity_id", "verdict": confirmed|corrected|filled|absent,
   "kind": direct|indirect|null, "text": <exact substring or null>,
   "occurrence": <1-based index if the string occurs several times, default 1>,
   "note", "annotator", "date"}
The row replaces the automatic result; `source` records who decided.
"""
import collections

from .common import ROOT, DATA, REVIEW, read_jsonl, write_jsonl

FIXES = ROOT / "curation" / "mention_fixes.jsonl"


def run():
    mentions = read_jsonl(DATA / "mentions.jsonl")
    if not FIXES.exists():
        print("  no curation file, automatic pass kept")
        return
    digests = {d["id"]: d for d in read_jsonl(DATA / "digests.jsonl")}
    by_key = {(m["digest_id"], m["entity_id"]): m for m in mentions}
    fixes = read_jsonl(FIXES)
    applied, problems = collections.Counter(), []
    for f in fixes:
        key = (f["digest_id"], f["entity_id"])
        m = by_key.get(key)
        if m is None:
            problems.append(f"fix for unknown link {key}")
            continue
        text = digests[f["digest_id"]]["text"]
        m["auto_match"], m["auto_text"] = m["match"], m["text"]
        if f.get("text"):
            occ = int(f.get("occurrence") or 1)
            pos, start = -1, -1
            for _ in range(occ):
                start = text.find(f["text"], pos + 1)
                if start < 0:
                    break
                pos = start
            if start < 0:
                problems.append(f"{key}: string not in digest text: {f['text']!r}")
                continue
            m.update(text=f["text"], start=start, end=start + len(f["text"]),
                     occurrences=text.count(f["text"]), kind=f.get("kind") or "direct")
        else:
            m.update(text=None, start=None, end=None, occurrences=0, kind=None)
        m.update(match="curated", confidence="high" if f["verdict"] != "absent" else "none",
                 source=f.get("annotator", "claude"), verdict=f["verdict"], note=f.get("note") or None)
        applied[f["verdict"]] += 1
    write_jsonl(DATA / "mentions.jsonl", mentions)
    with open(REVIEW / "mentions_unmatched.tsv", "w", encoding="utf-8") as f:
        f.write("digest_id\tentity_id\tlabel\tmention_text\tdigest_start\n")
        for m in mentions:
            if not m.get("text") and m.get("verdict") != "absent":
                f.write(f"{m['digest_id']}\t{m['entity_id']}\t{m['label']}\t\t{digests[m['digest_id']]['text'][:160]}\n")
    if problems:
        print("  WARNING " + f"{len(problems)} fixes not applied:\n    " + "\n    ".join(problems[:10]))
    print(f"  curated links: {dict(applied)}")
