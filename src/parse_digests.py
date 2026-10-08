"""Step 4: extract the volume-1 regests from RI_14.csv."""
import csv
import re

from .common import RAW, DATA, VOLUME_PREFIX, strip_tags, write_jsonl

csv.field_size_limit(10**9)
RI_ID = "https://www.regesta-imperii.de/id/"


def run():
    rows = []
    with open(RAW / "RI_14.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if not r["identifier"].startswith(VOLUME_PREFIX):
                continue
            nr = r["identifier"][len(VOLUME_PREFIX):].strip()
            scan = re.search(r'<link (https?://\S+?)(?:\s|>)', r.get("external_links") or "")
            rows.append({
                "id": r["identifier"],
                "nr": nr,
                "date_start": r["start_date"],
                "date_end": r["end_date"],
                "date_text": r.get("date_string") or None,
                "place": r["locality_string"] or None,
                "text": strip_tags(r["summary"]),
                "archival_history": strip_tags(r.get("archival_history")),
                "ri_url": RI_ID + r["persistent_identifier"],
                "scan_url": scan.group(1) if scan else None,
                "entities": {"person": [], "place": [], "other": []},
            })
    rows.sort(key=lambda x: (int(re.sub(r"\D", "", x["nr"]) or 0), x["nr"]))
    write_jsonl(DATA / "digests.jsonl", rows)
    print(f"  digests in volume 1: {len(rows)}")
