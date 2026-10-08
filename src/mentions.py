"""Step 6: find the mention string of every entity link in the digest text.

The index links a person to a digest but does not say where the name stands.
This step searches the digest text for the name forms the index gives
(headword, given name, source spellings, aliases) and records the string with
character offsets.  Match types, from strong to weak:

  exact       a surname token of the index label stands in the text
  variant     a source spelling from the index (italic parentheses) stands in the text
  stem        a word shares the first five letters with the surname and is similar
  given_name  only the given name is found (rulers: "Hg Albrecht von Bayern"),
              accepted when it is unambiguous or supported by a context word
  none        nothing found: the person is mentioned indirectly (office, title,
              "the queen's household") or under a spelling the index does not list

Everything below "exact" needs a human check; "none" needs manual annotation
(review/mentions_unmatched.tsv).  Offsets refer to the `text` field of the digest.
"""
import difflib
import re
import unicodedata

from .common import DATA, REVIEW, strip_parens, read_jsonl, write_jsonl
from .parse_register import TITLES, STOP_IN_NAME, ORDINAL_RE

TITLE_WORDS = {t.rstrip(".").lower() for t in TITLES} | {"kg", "hg", "gf", "bf", "ebf", "mgf", "pfgf", "fst",
                                                         "frh", "ritter", "dr", "mag", "hgin", "kgin", "ehg", "kr", "ks"}
# titles that belong to the name phrase ("Hg Albrecht", "Bf Friedrich", "Dr. Konrad"); role nouns
# such as "Rat", "Sekretär", "Kammermeister" do not
SPAN_TITLES = {"kg", "kgin", "kr", "ks", "hg", "hgin", "ehg", "ehgin", "gf", "gfin", "mgf", "mgfin", "pfgf", "pfgfin",
               "landgf", "burggf", "fst", "fstin", "frh", "bf", "ebf", "kard", "papst", "abt", "äbtissin", "abtissin",
               "propst", "dr", "mag", "lic", "ritter", "meister", "doge", "sultan", "hochmeister", "deutschmeister",
               "infant", "infantin", "prinz", "prinzessin", "dauphin", "kfst", "kaiser", "könig", "herzog", "graf",
               "jude", "jüdin", "judin"}
GLUE = {"von", "zu", "zum", "zur", "van", "de", "der", "des", "di", "da", "d", "aus", "genannt", "gen", "und", "del",
        "della", "degli", "dei", "do", "dos", "y", "el", "al", "le", "la", "the", "of", "d'", "il", "lo"}
MIN_TOKEN = 4


def fold(s: str) -> str:
    """Lowercase, diacritics removed, same length as the input (offsets stay valid)."""
    out = []
    for ch in s:
        d = unicodedata.normalize("NFKD", ch)
        base = d[0] if d else ch
        out.append(base.lower() if base.isalnum() else ch.lower())
    return "".join(out)


def fold_token(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def name_tokens(s: str):
    """Capitalised, non-title, non-glue tokens of a name string."""
    toks = []
    for t in re.findall(r"[^\s,;:()]+", strip_parens(s)):
        t = t.strip(".,;")
        if not t or ORDINAL_RE.match(t) or t.lower() in GLUE or t.lower() in TITLE_WORDS or t.rstrip(".") in TITLES:
            continue
        if t[:1].isupper() and len(t) >= 2:
            toks.append(t)
    return toks


def variant_pattern(v: str) -> str:
    """'Li(e)cht(t)enstain' -> regex with optional letters; 'Aw' -> 'aw'."""
    pat = ""
    for part in re.split(r"(\([^)]*\))", v):
        if part.startswith("(") and part.endswith(")"):
            inner = re.escape(fold_token(part[1:-1]))
            pat += f"(?:{inner})?"
        else:
            pat += re.escape(fold_token(part))
    return pat


def entity_forms(e):
    """-> (surname tokens, given tokens, variant patterns, context tokens)"""
    head = e["headword"].split("/")[0]
    sub = e.get("subentry") or ""
    if e["type"] == "place":
        variants = [variant_pattern(v) for v in e.get("variants", []) if v]
        return name_tokens(head), [], variants, []
    if e["type"] == "other":
        # "Wien, Regiment" / "Frankfurt, Oberrad, Dorf": every clause can carry the name
        toks = name_tokens(head) + [t for c in sub.split(",") for t in name_tokens(c)]
        variants = [variant_pattern(v) for v in e.get("variants", []) if v]
        return toks, [], variants, []
    if e.get("parent_place"):
        # "Trient, Bf Ulrich von Liechtenstein": the name is in the sub-entry
        name_part = sub.split(",")[0]
        toks = name_tokens(name_part)
        given, surname = toks[:1], toks[1:] or toks[:1]
        context = [e["parent_place"]] + name_tokens(",".join(sub.split(",")[1:]))
    elif e["classification"]["reason"] in ("ruler headword + title", "given-name headword") or \
            (sub and name_tokens(sub.split(",")[0]) and name_tokens(sub.split(",")[0])[0].lower() in TITLE_WORDS):
        # "Albrecht IV., Hg von Bayern-München": headword is the given name
        given = name_tokens(head)
        surname = []
        context = name_tokens(sub)
    else:
        surname = name_tokens(head)
        first = sub.split(",")[0] if sub else ""
        given = name_tokens(first)
        context = name_tokens(",".join(sub.split(",")[1:])) if sub else []
    variants = [variant_pattern(v) for v in e.get("variants", []) if v]
    for a in e.get("aliases", []):
        if "/" in a:        # "Innsbruck/Tirol, Marschall": office alias, not a name form
            continue
        for t in name_tokens(a.split(",")[0]):
            variants.append(re.escape(fold_token(t)))
    return surname, given, variants, context


def loose(token_folded: str) -> str:
    """'neuotting' -> regex that also matches '(neu-)otting'."""
    return r"[()\-]*".join(re.escape(ch) for ch in token_folded)


def find_word(pattern: str, ftext: str):
    """All whole-word matches (allowing German inflection endings) of a folded pattern."""
    return list(re.finditer(r"(?<![a-z0-9])" + pattern + r"(?:s|n|en|er|ern|in)?(?![a-z0-9])", ftext))


def extend_span(text, ftext, start, end, forms):
    """Grow a surname hit leftwards over given names / titles / glue and
    rightwards over 'von <known token>'."""
    surname, given, variants, context = forms
    known = {fold_token(t) for t in surname + given + context}
    given_stems = {fold_token(t)[:4] for t in given if len(t) >= 4}
    # right: ordinal ("Friedrichs III.") and "von <known token>" ("Albrecht von Bayern", "Christoph von Liechtenstein")
    for _ in range(3):
        m = re.match(r"\s+((?:[ivxl]+\.)|(?:d\.\s*[äa]\.)|(?:d\.\s*j\.))", ftext[end:])
        if m:
            end += m.end(); continue
        m = re.match(r"\s+(?:von|zu|de|di|da|van|der)\s+(\(?[a-z0-9\-]+\)?)", ftext[end:])
        if m:
            tok = m.group(1).strip("()")
            if tok in known or not surname and tok[:1].isalpha() and text[end + m.start(1)].isupper() or \
                    any(re.fullmatch(v + r"(?:s|n|en|er)?", tok) for v in variants):
                end += m.end(); continue
        m = re.match(r"\s*(\(-?[a-z0-9\-]+\))", ftext[end:])   # "(-Nikolsburg)"
        if m and m.group(1).strip("(-)") in known:
            end += m.end(); continue
        break
    # left: given names, name-phrase titles, glue; never role nouns or "und"
    for _ in range(4):
        m = re.search(r"([a-z0-9\.'\-]+)[\s\-]*$", ftext[:start])
        if not m:
            break
        tok = m.group(1).strip(".'")
        is_given = tok in known or (tok[:4] in given_stems and len(tok) >= 4) or any(re.fullmatch(v, tok) for v in variants)
        if is_given or tok in GLUE - {"und", "aus", "genannt", "gen"} or tok in SPAN_TITLES or ORDINAL_RE.match(tok.upper()):
            start = m.start(1)
        else:
            break
    # never start on a glue word
    m = re.match(r"(?:von|zu|zum|zur|de|der|des|di|da|van)\s+", ftext[start:end])
    if m:
        start += m.end()
    while start < end and text[start] in " ,;(":
        start += 1
    return start, end


def locate(e, text):
    ftext = fold(text)
    surname, given, variants, context = entity_forms(e)
    forms = (surname, given, variants, context)

    def best(hits):
        m = hits[0]
        s, t = extend_span(text, ftext, m.start(), m.end(), forms)
        return s, t, len(hits)

    for tok in surname:
        ft = fold_token(tok)
        if len(ft) < MIN_TOKEN:
            continue
        hits = find_word(loose(ft), ftext)
        if hits:
            s, t, n = best(hits)
            return "exact", s, t, n
    for v in variants:
        if len(v) < MIN_TOKEN:
            continue
        hits = find_word(v, ftext)
        if hits:
            s, t, n = best(hits)
            return "variant", s, t, n
    for tok in surname:
        ft = fold_token(tok)
        if len(ft) < 6:
            continue
        stem = re.escape(ft[:5])
        cands = [m for m in re.finditer(r"(?<![a-z0-9])" + stem + r"[a-z]*", ftext)
                 if difflib.SequenceMatcher(None, ft, m.group(0)).ratio() >= 0.75]
        if cands:
            s, t, n = best(cands)
            return "stem", s, t, n
    ctx = {fold_token(c) for c in context if len(c) >= MIN_TOKEN}
    for tok in given:
        ft = fold_token(tok)
        if len(ft) < 3:
            continue
        hits = find_word(re.escape(ft), ftext)
        if not hits:
            continue
        supported = [m for m in hits if any(c in ftext[max(0, m.start() - 60): m.end() + 60] for c in ctx)]
        if supported or len(hits) == 1:
            s, t, n = best(supported or hits)
            return "given_name", s, t, n
    return "none", None, None, 0


def run():
    entities = {e["id"]: e for e in read_jsonl(DATA / "entities.jsonl")}
    digests = read_jsonl(DATA / "digests.jsonl")
    rows, unmatched = [], []
    for d in digests:
        for etype in ("person", "place", "other"):
            for eid in d["entities"][etype]:
                e = entities[eid]
                match, s, t, n = locate(e, d["text"])
                rows.append({"digest_id": d["id"], "entity_id": eid, "entity_type": etype, "label": e["label"],
                             "match": match, "kind": "direct" if match != "none" else None,
                             "text": d["text"][s:t] if s is not None else None, "start": s, "end": t,
                             "occurrences": n, "confidence": "high" if match == "exact" else "medium"
                             if match in ("variant", "stem") else "low" if match == "given_name" else "none",
                             "source": "auto"})
                if match == "none":
                    unmatched.append((d["id"], eid, e["label"], d["text"][:160].replace("\t", " ")))
    write_jsonl(DATA / "mentions.jsonl", rows)
    REVIEW.mkdir(exist_ok=True)
    with open(REVIEW / "mentions_unmatched.tsv", "w", encoding="utf-8") as f:
        f.write("digest_id\tentity_id\tlabel\tmention_text\tdigest_start\n")
        for d, p, lab, snippet in unmatched:
            f.write(f"{d}\t{p}\t{lab}\t\t{snippet}\n")
    import collections
    c = collections.Counter(r["match"] for r in rows)
    print(f"  mentions {len(rows)} (all types): " + ", ".join(f"{k} {c[k]}" for k in ("exact", "variant", "stem", "given_name", "none")))
    cp = collections.Counter(r["match"] for r in rows if r["entity_type"] == "person")
    print(f"  persons {sum(cp.values())}: " + ", ".join(f"{k} {cp[k]}" for k in ("exact", "variant", "stem", "given_name", "none")))
