"""Shared paths and helpers."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
REVIEW = ROOT / "review"

DATASET_ID = "RI14-1"          # prefix of every entity id
VOLUME_PREFIX = "RI XIV,1 n. "  # identifier prefix of volume 1 in RI_14.csv

# Source files in the RI Lab repository (ADW Mainz), branch main.
GITLAB_PROJECT = "adwmainz/regesta-imperii/lab/regesta-imperii-data"
GITLAB_RAW = f"https://gitlab.rlp.net/{GITLAB_PROJECT}/-/raw/main/"
SOURCES = {
    "RI_14.csv": "data/regesta-csv/RI_14.csv",
    "ri_14_1_register.doc": "archive/RegestenUndRegister/abt-14/"
                            "ri_14,1-maximilian_1493-1495/ri_14,1-maximilian_1493-1495_register.doc",
}

TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub("", s or "")).strip()


def strip_parens(s: str) -> str:
    """Remove balanced parenthesised groups, including nested ones."""
    out, depth = [], 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path: Path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
