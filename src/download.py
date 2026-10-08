"""Step 1: fetch the two source files and record provenance in raw/SOURCE.json."""
import hashlib
import json
import shutil
import subprocess
import urllib.request
from datetime import datetime, timezone

from .common import RAW, SOURCES, GITLAB_PROJECT

API = "https://gitlab.rlp.net/api/v4/projects/" + GITLAB_PROJECT.replace("/", "%2F")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ri14-register-dataset-build"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _libreoffice_version():
    exe = shutil.which("libreoffice") or shutil.which("soffice")
    if not exe:
        return None
    out = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout
    return out.strip().splitlines()[0] if out.strip() else None


def run(force: bool = False):
    RAW.mkdir(exist_ok=True)
    prev = RAW / "SOURCE.json"
    if prev.exists() and not force:
        # reproducible rebuild: stay on the commit recorded at first download
        commit = json.loads(prev.read_text(encoding="utf-8"))["commit"]
    else:
        commits = json.loads(_get(API + "/repository/commits?per_page=1"))
        commit = {"sha": commits[0]["id"], "committed_date": commits[0]["committed_date"]}
    raw_base = f"https://gitlab.rlp.net/{GITLAB_PROJECT}/-/raw/{commit['sha']}/"
    record = {
        "repository": f"https://gitlab.rlp.net/{GITLAB_PROJECT}",
        "commit": commit,
        "libreoffice": _libreoffice_version(),
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": {},
    }
    for local, remote in SOURCES.items():
        dest = RAW / local
        if dest.exists() and not force:
            data = dest.read_bytes()
        else:
            data = _get(raw_base + remote)
            dest.write_bytes(data)
        record["files"][local] = {
            "source_path": remote,
            "url": raw_base + remote,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        print(f"  {local}: {len(data):,} bytes")
    (RAW / "SOURCE.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
