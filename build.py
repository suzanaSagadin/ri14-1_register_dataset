#!/usr/bin/env python3
"""Build the RI XIV,1 register dataset from the public RI Lab sources.

    python build.py            # all steps
    python build.py --from parse_register   # re-run from a step onwards
    python build.py --force-download
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src import download, convert, parse_register, curate_types, parse_digests, join, mentions, curate, split, validate, stats  # noqa: E402

STEPS = [("download", download.run), ("convert", convert.run), ("parse_register", parse_register.run), ("curate_types", curate_types.run),
         ("parse_digests", parse_digests.run), ("join", join.run), ("mentions", mentions.run), ("curate", curate.run),
         ("split", split.run), ("validate", validate.run), ("stats", stats.run)]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", choices=[s for s, _ in STEPS], default="download")
    ap.add_argument("--force-download", action="store_true")
    a = ap.parse_args()
    started = False
    for name, fn in STEPS:
        if name == a.start:
            started = True
        if not started:
            continue
        print(f"[{name}]")
        if name == "download":
            fn(force=a.force_download)
        else:
            fn()
