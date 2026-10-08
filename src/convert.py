"""Step 2: convert the Word register to plain text with headless LibreOffice.

The .doc keeps the italic source spellings as <hi rend="kursiv"> markup in the
text export, which the parser relies on.
"""
import shutil
import subprocess

from .common import RAW


def run():
    src = RAW / "ri_14_1_register.doc"
    dst = RAW / "ri_14_1_register.txt"
    if dst.exists():
        print("  register text already converted")
        return
    exe = shutil.which("libreoffice") or shutil.which("soffice")
    if not exe:
        raise SystemExit("LibreOffice (libreoffice/soffice) is required to convert the .doc register")
    subprocess.run([exe, "--headless", "--convert-to", "txt:Text", str(src), "--outdir", str(RAW)],
                   check=True, capture_output=True)
    if not dst.exists():
        raise SystemExit("conversion failed: " + str(dst))
    print(f"  wrote {dst.name}")
