"""Step 3: parse the register text into entities with frozen ids.

Register layout (after conversion): a two-column table flattened to lines.
    <headword>                      e.g.  Liechtenstein (<hi rend="kursiv">Lichtenstein</hi>),
    --- <subentry>                  e.g.  --- Paul von, Hofmarschall zu Innsbruck      (optional)
    <value>                         e.g.  39, 40, 84        or   s. Trient, Bf
The headword is repeated for every subentry.  A value that starts with "s."
is a redirect to another entry; such entries carry no regest numbers.

Every entry with regest numbers becomes one entity.  Its label is the
register's own form "headword, subentry".  Redirect entries are resolved and
attached to their target as aliases.  Classification into person / place /
other is rule based; uncertain cases are written to review/.
"""
import collections
import re

from .common import RAW, DATA, REVIEW, DATASET_ID, strip_tags, strip_parens, write_jsonl

HI_RE = re.compile(r'<hi rend="kursiv">(.*?)</hi>')
NUM_RE = re.compile(r"\b(\d+[a-z]?)\b")

# Words that open a title + name combination ("Bf Ulrich von Liechtenstein").
TITLES = {
    "Bf", "Ebf", "Kard.", "Kard", "Papst", "Abt", "Äbtissin", "Propst", "Prior", "Dechant", "Dekan",
    "Pfarrer", "Kaplan", "Kanoniker", "Domherr", "Domdechant", "Dompropst", "Generalvikar", "Weihbf",
    "Kg", "Kgin", "Hg", "Hgin", "Ehg", "Ehgin", "Gf", "Gfin", "Mgf", "Mgfin", "Pfgf", "Pfgfin", "Landgf",
    "Burggf", "Fst", "Fstin", "Frh", "Ritter", "Meister", "Dr.", "Mag.", "Lic.", "Doge", "Sultan", "Kaiser",
    "Ks.", "Kr", "Jude", "Jüdin", "Hofmeister", "Hofmarschall", "Kanzler", "Sekretär", "Hauptmann", "Pfleger",
    "Vogt", "Landvogt", "Bürgermeister", "Schultheiß", "Richter", "Kämmerer", "Schatzmeister", "Komtur",
    "Statthalter", "Landeshauptmann", "Landmarschall", "Marschall", "Truchseß", "Schenk", "Erbmarschall",
    "Erbtruchseß", "Kastellan", "Burggraf", "Prinz", "Prinzessin", "Infant", "Infantin", "Dauphin",
    "Deutschmeister", "Hochmeister", "Großmeister", "Protonotar", "Notar", "Prokurator", "Gesandter",
    "Orator", "Legat", "Nuntius", "Vizekanzler", "Rat", "Räte", "Kämmerin", "Herzog", "König", "Graf",
}
# First words that mark a non-person entry (family group, institution, office without holder, thing).
NON_PERSON = {
    "Familie", "Herren", "Grafen", "Gfen", "Hge", "Kge", "Mgfen", "Pfgfen", "Fsten", "Brüder", "Geschlecht",
    "Stadt", "Dorf", "Markt", "Schloß", "Schloss", "Burg", "Kloster", "Stift", "Btm", "Erzbtm", "Hochstift",
    "Erzstift", "Hft", "Gft", "Mgft", "Pfgft", "Landgft", "Fstm", "Hzm", "Kgr", "Kaisertum", "Reich",
    "Juden", "Bürger", "Regiment", "Landtag", "Reichstag", "Zoll", "Zölle", "Münze", "Kammer", "Hofstaat",
    "Gesandte", "Gesandtschaft", "Kaufleute", "Domkapitel", "Domherren", "Kapitel", "Universität", "Pfarre",
    "Pfarrkirche", "Kirche", "Orden", "Bruderschaft", "Zunft", "Zünfte", "Burgpflege", "Pflege", "Amt",
    "Gericht", "Landgericht", "Hauptmannschaft", "Vogtei", "Landvogtei", "Propstei", "Abtei", "Bund",
    "Liga", "Stände", "Landschaft", "Landstände", "Ritterschaft", "Adel", "Untertanen", "Einwohner",
    "Bewohner", "Räte", "Statthalter", "Regenten", "Kommissare", "Hauptleute", "Pfleger", "Söldner",
    "Truppen", "Heer", "Flotte", "Steuer", "Maut", "Bergwerk", "Salzwerk", "Hütte", "Hof", "Haus", "Spital",
    "Schule", "Bibliothek", "Archiv", "Kanzlei", "Hofkammer", "Hofgericht", "Kammergericht", "Rat",
    "Komturei", "Kommende", "Ballei", "Diözese", "Dekanat", "Kapelle", "Altar", "Reliquien", "Wappen",
    "Privileg", "Privilegien", "Urkunde", "Vertrag", "Verträge", "Frieden", "Krieg", "Schlacht", "Fehde",
    "Tag", "Tage", "Versammlung", "Synode", "Konzil", "Bergrecht", "Stadtrecht", "Freiheit", "Freiheiten",
    "Lehen", "Reichslehen", "Reichsstadt", "Reichsstädte", "Städte", "Dörfer", "Schlösser", "Burgen",
    "Gebiet", "Land", "Länder", "Herrschaft", "Grafschaft", "Herzogtum", "Fürstentum", "Königreich",
    "Republik", "Signorie", "Kommune", "Bischöfe", "Äbte", "Pröpste", "Geistlichkeit", "Klerus", "Mönche",
    "Nonnen", "Augustiner", "Augustinerkloster", "Benediktiner", "Dominikaner", "Franziskaner", "Kartause",
    "Kartäuser", "Zisterzienser", "Prämonstratenser", "Johanniter", "Deutschordenshaus", "Deutschorden",
    "Fürsten", "Kurfürsten", "Kfen", "Reichsstände", "Reichsfürsten", "Botschaft", "Boten", "Bote", "Wirt",
    "Wirte", "Handwerker", "Bauern", "Meer", "Fluß", "Fluss", "See", "Gebirge", "Paß", "Pass", "Straße",
    "Salz", "Aufschlag", "Aufschläge", "Pfründe", "Pfründen", "Erbländer", "Erblande", "Einkünfte", "Nutzen",
    "Gülten", "Gült", "Zinsen", "Zins", "Renten", "Rente", "Gefälle", "Urbar", "Vorstadt", "Bergleute", "Knappen",
    "Hgtm", "Hzgtm", "Ebtm", "Gfsch", "Mgfsch", "Pfgfsch", "Landgfsch", "Burggfsch", "Fstbtm", "Kfstm",
    "Hochmeistertum", "Ordensland", "Vogteien", "Pflegen", "Ämter", "Gerichte", "Herrschaften", "Lande",
    "Brücke", "Tor", "Turm", "Mauer", "Wald", "Forst", "Insel", "Küste", "Tal", "Kathedrale", "Dom",
    "Münster", "Student", "Studenten", "Professoren", "Magister", "Doktoren", "Hofgesinde", "Gesinde",
    "Diener", "Dienerschaft", "Hofkapelle", "Kapläne", "Kanoniker", "Chorherren", "Chorherrenstift",
    "Nonnenkloster", "Mönchskloster", "Frauenkloster", "Pfarrkirche", "Stadtpfarrkirche", "Spitalkirche",
    "Augustinerinnen", "Augustinerinnenkloster", "Benediktinerinnen", "Klarissen", "Dominikanerinnen",
    "Zisterzienserinnen", "Beginen", "Deutschordenskommende", "Johanniterkommende", "Hofrat", "Hofräte",
    "Kammerräte", "Hofkammerräte", "Landrechte", "Landrecht", "Landgerichte", "Landtage", "Reichstage",
}
ORDINAL_RE = re.compile(r"^[IVXL]+\.?$")
# Office nouns by suffix: bare = office without holder (other), followed by a name = person.
OFFICE_SUFFIX = re.compile(r"(meister|schreiber|richter|vogt|amtmann|hauptmann|marschall|kämmerer|kanzler|"
                           r"pfleger|verweser|zöllner|mautner|kaplan|arzt|diener|hüter|knecht|wirt|schmied|"
                           r"maler|propst|dechant|dekan|pfarrer|prediger|notar|sekretär|kastner|kellner|"
                           r"hubmeister|rentmeister|landvogt|untervogt|obervogt|schultheiß|bürgermeister|"
                           r"statthalter|verwalter|einnehmer|zahlmeister|zeugmeister|büchsenmeister|"
                           r"stallmeister|jägermeister|forstmeister|küchenmeister|hofmeister|organist|"
                           r"kantor|sänger|trompeter|pfeifer|herold|läufer|bote|kurier)$", re.I)
# Things and institutions by suffix (never a person).
THING_SUFFIX = re.compile(r"(hof|höfe|wiesen|wiese|gut|güter|zehent|zehnt|ungeld|steuer|maut|zoll|mühle|"
                          r"acker|äcker|wald|weingarten|gericht|amt|ämter|pflege|vogtei|kirche|kapelle|"
                          r"stift|kloster|spital|schloß|schloss|burg|haus|häuser|turm|tor|brücke|straße|"
                          r"markt|platz|gasse|bad|bergwerk|hütte|werk|lehen|lehn|rechte|recht|freiheit|"
                          r"privileg|ordnung|bund|liga|tag|landtag|reichstag|kapitel|stände|schaft|tum|reich)$", re.I)
GIVEN_HEAD_RE = re.compile(r"^[A-ZÄÖÜ][\wäöüß'\-]+(?: [A-ZÄÖÜ][\wäöüß'\-]+)*(?: [IVXL]+\.?)?$")
STOP_IN_NAME = {"von", "zu", "zum", "zur", "van", "de", "der", "des", "di", "da", "d'", "aus", "bei", "genannt",
                "gen.", "und", "oder", "in", "im", "am", "an", "auf", "the", "of", "le", "la", "del", "della",
                "degli", "dei", "do", "dos", "y", "el", "al"}


def _tokens(s: str):
    return [t for t in re.split(r"[\s]+", s) if t]


def _first_clause(s: str) -> str:
    """Text before the first comma that is not inside parentheses."""
    out, depth = [], 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            break
        out.append(ch)
    return "".join(out).strip()


def _has_name_after_title(tokens):
    """tokens[0] is a title: is it followed by a proper name?"""
    for t in tokens[1:]:
        if t.lower() in STOP_IN_NAME or ORDINAL_RE.match(t) or t in TITLES:
            continue
        if t[:1].isupper() and t.strip("(),.") not in NON_PERSON:
            return True
        return False
    return False


def classify_rest(rest: str, given_name_vocab: set, strong_vocab: set = frozenset()):
    """Classify the identifying part of an entry (subentry, or headword part
    after the comma).  Returns (type, confidence, reason)."""
    clause = strip_parens(_first_clause(rest)) or strip_parens(rest)
    toks = _tokens(clause)
    if not toks:
        return "other", "low", "empty"
    first = toks[0].strip(",.;")
    if first in NON_PERSON or first.rstrip("s") in NON_PERSON or first in {"St.", "Hl.", "NN", "NN."}:
        return "other", "high", "non-person word"
    if THING_SUFFIX.search(first) and first not in TITLES and not OFFICE_SUFFIX.search(first):
        return "other", "high", "thing/institution suffix"
    if first in TITLES or first.rstrip(".") in TITLES or OFFICE_SUFFIX.search(first):
        if _has_name_after_title(toks):
            return "person", "high", "title + name"
        if first in {"Jude", "Jüdin"}:
            return "person", "medium", "Jude without name"
        return "other", "medium", "bare office/title"
    clauses = [c.strip() for c in strip_parens(rest).split(",") if c.strip()]
    if len(clauses) > 1:
        t2 = _tokens(clauses[1])
        if t2 and (t2[0].strip(".;") in NON_PERSON or THING_SUFFIX.search(t2[0])) and first not in strong_vocab:
            return "other", "high", "non-person word in second clause"
    if first in given_name_vocab:
        return "person", "high", "given name"
    if first[:1].isupper() and not first.isupper():
        # unknown capitalised word: probably a rare given name, needs review
        return "person", "low", "unknown capitalised first word"
    return "other", "low", "unclassified"


def parse_lines(path):
    raw = [l.rstrip("\n").lstrip("\ufeff") for l in open(path, encoding="utf-8")]
    raw = [l for l in raw if l.strip() and l.strip() not in ("Stichwort", "Regestennummer")]
    entries, i = [], 0
    while i < len(raw):
        head = raw[i]; i += 1
        subs = []
        while i < len(raw) and raw[i].startswith("---"):
            subs.append(raw[i][3:].strip()); i += 1
        val = raw[i].strip() if i < len(raw) else ""
        if val[:1].isdigit() or val.startswith("s. "):
            i += 1
        else:
            val = ""
        # several "---" lines in a row = nested sub-entry ("Bf Ascanio Maria Sforza," + "Gft")
        sub = None
        if subs:
            sub = subs[0]
            for extra in subs[1:]:
                if extra.startswith(","):      # continuation of the previous line
                    sub = sub.rstrip(",").rstrip() + ", " + extra.lstrip(", ")
                else:                          # repeated/truncated parent line: discard it
                    sub = extra
        entries.append({"line": i, "head_raw": head, "sub_raw": sub, "value": val})
    # Sub-entry markers lost in the Word export: "Aibling (Aybling)/Bayern Kastenamt"
    # -> region "Bayern", sub-entry "Kastenamt".  Known regions = region strings
    # that occur at least twice on their own.
    regions = collections.Counter()
    for e in entries:
        h = strip_tags(e["head_raw"])
        if "/" in h:
            regions[h.split("/", 1)[1].strip().rstrip(",").strip()] += 1
    frequent = {r for r, n in regions.items() if n >= 2}
    # "Rh.-Pf. Vorstadt" occurring twice is still region + lost sub-entry, not a region
    frequent = {r for r in frequent if len(r) >= 3 and re.search(r"[A-Za-zÄÖÜäöü]", r)}   # "?" is not a region
    known = {r for r in frequent if not any(r.startswith(k + " ") for k in frequent if k != r)}
    for e in entries:
        h = e["head_raw"]
        plain = strip_tags(h)
        if "/" not in plain:
            continue
        region = plain.split("/", 1)[1].strip().rstrip(",").strip()
        if region in known:
            continue
        cands = [k for k in known if region.startswith(k + " ") or region.startswith(k + ",")]
        if not cands:
            continue
        k = max(cands, key=len)
        m = re.search(r"/\s*" + re.escape(k), h)
        if not m:
            continue
        before, after = h[:m.start()], h[m.end():]
        rest_raw = after.strip().lstrip(",").strip()
        e["head_raw"] = before + "/" + k
        e["sub_raw"] = rest_raw if e["sub_raw"] is None else rest_raw.rstrip(",") + ", " + e["sub_raw"].lstrip(", ")
    return entries


def variants_of(*raws):
    out = []
    for r in raws:
        if not r:
            continue
        for hit in HI_RE.findall(r):
            for v in hit.split(","):
                v = v.strip(" ;")
                if v and v not in out:
                    out.append(v)
    return out


def run():
    entries = parse_lines(RAW / "ri_14_1_register.txt")

    # Pass 1: normalise text, split numbers / redirects.
    for e in entries:
        e["head"] = strip_tags(e["head_raw"])
        e["sub"] = strip_tags(e["sub_raw"]) if e["sub_raw"] is not None else None
        e["head_norm"] = strip_parens(e["head"]).rstrip(",").strip()
        e["variants"] = variants_of(e["head_raw"], e["sub_raw"])
        e["is_place_lemma"] = "/" in e["head_norm"]
        if e["is_place_lemma"]:
            place_part, region = e["head_norm"].split("/", 1)
            alts = [a.strip() for a in place_part.split("=") if a.strip()]
            e["place_alts"] = alts
            e["head_norm"] = f"{alts[0]}/{region.strip()}"
            for a in alts[1:]:
                if a not in e["variants"]:
                    e["variants"].append(a)
        if e["value"].startswith("s. "):
            e["redirect"] = [t.strip() for t in e["value"][3:].split(";") if t.strip()]
            e["numbers"], e["notes"] = [], []
        else:
            e["redirect"] = None
            notes = re.findall(r"\(([^)]*)\)", e["value"])
            e["notes"] = [n.strip() for n in notes if n.strip()]
            nums = NUM_RE.findall(re.sub(r"\([^)]*\)", "", e["value"]))
            e["numbers"] = list(dict.fromkeys(nums))
        # identifying clause: subentry, or the headword part after the first comma
        if e["sub"] is not None:
            e["rest"] = strip_parens(e["sub"])
        else:
            h = strip_parens(e["head"])
            e["rest"] = h[len(_first_clause(h)):].lstrip(", ").strip() if "," in h else ""
        if e["sub"] is not None:
            e["label"] = f"{e['head_norm']}, {strip_parens(e['sub'])}"
        else:
            e["label"] = strip_parens(e["head"]).strip(",").strip()

    # Build a vocabulary of given names from the data: first words of the
    # identifying clause that occur in several different entries.
    first_words = collections.Counter()
    for e in entries:
        toks = _tokens(strip_parens(_first_clause(e["rest"])))
        if toks:
            first_words[toks[0].strip(",.;")] += 1
    given_vocab = {w for w, n in first_words.items()
                   if n >= 2 and w not in NON_PERSON and w not in TITLES and w[:1].isupper()}
    strong_vocab = {w for w, n in first_words.items() if n >= 3 and w in given_vocab}

    # Pass 2: classify.
    for e in entries:
        if e["redirect"] is not None:
            e["type"] = "redirect"; e["confidence"] = "high"; e["reason"] = "redirect"
            continue
        if e["sub"] is None:
            if e["is_place_lemma"]:
                e["type"], e["confidence"], e["reason"] = "place", "high", "place lemma"
                e["label"] = e["head_norm"].split("/")[0].strip()
                e["region"] = e["head_norm"].split("/", 1)[1].strip()
                continue
            head_clause = strip_parens(_first_clause(e["head"]))
            head_toks = _tokens(head_clause)
            head_is_given = bool(head_toks) and GIVEN_HEAD_RE.match(head_clause) and (
                head_toks[0] in given_vocab or ORDINAL_RE.match(head_toks[-1]) or " von " in head_clause)
            if not e["rest"]:
                if head_is_given and (" von " in head_clause or len(head_toks) > 1):
                    e["type"], e["confidence"], e["reason"] = "person", "medium", "given-name headword"
                else:
                    e["type"], e["confidence"], e["reason"] = "other", "medium", "single headword without identifying part"
                continue
            t, c, r = classify_rest(e["rest"], given_vocab, strong_vocab)
            if head_is_given and head_toks[0] not in NON_PERSON and (ORDINAL_RE.match(head_toks[-1]) or t != "person"):
                # "Ferdinand I., Kr" / "Albrecht IV., Hg von Bayern": headword is the given name
                t, c, r = "person", "high", "ruler headword + title"
            e["type"], e["confidence"], e["reason"] = t, c, r
        else:
            t, c, r = classify_rest(e["rest"], given_vocab, strong_vocab)
            if e["is_place_lemma"]:
                e["parent_place"] = e["head_norm"].split("/")[0].strip()
                e["label"] = f"{e['parent_place']}, {strip_parens(e['sub'])}"
                if t == "person" and r == "given name":
                    c = "low"; r = "given name directly under a place lemma"
            e["type"], e["confidence"], e["reason"] = t, c, r

    # Entries without numbers and without redirect (editorial leftovers, or a
    # redirect whose "s." was lost) are logged and skipped.
    REVIEW.mkdir(exist_ok=True)
    with open(REVIEW / "entries_without_numbers.tsv", "w", encoding="utf-8") as f:
        f.write("register_line\tlabel\n")
        for e in entries:
            if e["type"] != "redirect" and not e["numbers"]:
                f.write(f"{e['line']}\t{e['label']}\n")
    entries = [e for e in entries if e["type"] == "redirect" or e["numbers"]]

    # Place names that occur in several regions get the region in their label.
    place_regions = collections.defaultdict(set)
    for e in entries:
        if e["is_place_lemma"]:
            place_regions[e["head_norm"].split("/")[0].strip()].add(e["head_norm"].split("/", 1)[1].strip())
    ambiguous_places = {p for p, rs in place_regions.items() if len(rs) > 1}
    for e in entries:
        if e["is_place_lemma"]:
            p, reg = e["head_norm"].split("/")[0].strip(), e["head_norm"].split("/", 1)[1].strip()
            e["region"] = reg
            if p in ambiguous_places:
                shown = f"{p} ({reg})"
                e["label"] = shown if e["sub"] is None else f"{shown}, {strip_parens(e['sub'])}"

    # Assign ids per type in register order (frozen once published).
    counter = 0
    entities, by_label, by_head = [], {}, {}
    for e in entries:
        if e["type"] == "redirect":
            continue
        counter += 1
        e["id"] = f"{DATASET_ID}-E{counter:04d}"      # neutral: the id says nothing about the type
        ent = {
            "id": e["id"], "type": e["type"], "label": tidy(e["label"]),
            "headword": tidy(e["head_norm"] if e["sub"] is not None or not e["rest"]
                             else _first_clause(strip_parens(e["head"]))),
            "subentry": tidy(strip_parens(e["sub"])) if e["sub"] else (tidy(e["rest"]) or None),
            "parent_place": e.get("parent_place"), "region": e.get("region"),
            "variants": e["variants"], "aliases": [], "digests": e["numbers"], "notes": e["notes"],
            "classification": {"confidence": e["confidence"], "reason": e["reason"]},
            "register_line": e["line"],
        }
        entities.append(ent)
        by_label[_key(tidy(e["label"]))] = ent
        if e.get("is_place_lemma"):
            plain_place = e["head_norm"].split("/")[0].strip()
            by_label.setdefault(_key(plain_place if e["sub"] is None else f"{plain_place}, {strip_parens(e['sub'])}"), ent)
        by_head.setdefault(_key(e["head_norm"].split("/")[0]), []).append(ent)
        for a in e.get("place_alts", [])[1:]:
            by_head.setdefault(_key(a), []).append(ent)
            if e["sub"]:
                by_label.setdefault(_key(f"{a}, {strip_parens(e['sub'])}"), ent)

    # Resolve redirects into aliases.
    labels_sorted = list(by_label.items())
    unresolved = []
    for e in entries:
        if e["type"] != "redirect":
            continue
        for target in e["redirect"]:
            tk = _key(strip_parens(target))
            hit = by_label.get(tk)
            hits = [hit] if hit is not None else []
            if not hits:
                # "s. Trient, Bf" -> "Trient, Bf Ulrich von Liechtenstein (†1505)"
                cands = [ent for k, ent in labels_sorted if k.startswith(tk + ",") or k.startswith(tk + " ")]
                uniq = list({c["id"]: c for c in cands}.values())
                if len(uniq) > 1:
                    ctx = _key(e["head_norm"].split("/")[0])
                    pref = [c for c in uniq if ctx and ctx in _key(c["label"])]
                    uniq = pref or [c for c in uniq if c["type"] == "person"] or uniq
                if len(uniq) == 1:
                    hits = uniq
            if not hits and "," not in tk and tk in by_head:
                # family-level spelling redirect ("Freuntsperg s. Freundsberg"): alias for all members
                hits = by_head[tk]
                alias = e["label"]
                for h in hits:
                    if alias and alias not in h["variants"] and alias != h["headword"]:
                        h["variants"].append(alias)
                continue
            if not hits:
                unresolved.append((e["line"], e["label"], target))
                continue
            alias = e["label"]
            for h in hits:
                if alias and alias not in h["aliases"] and alias != h["label"]:
                    h["aliases"].append(alias)

    write_jsonl(DATA / "entities.jsonl", entities)
    REVIEW.mkdir(exist_ok=True)
    with open(REVIEW / "uncertain_entities.tsv", "w", encoding="utf-8") as f:
        f.write("id\ttype\tconfidence\treason\tlabel\tregests\n")
        for ent in entities:
            if ent["classification"]["confidence"] != "high" and ent["type"] != "place":
                f.write(f"{ent['id']}\t{ent['type']}\t{ent['classification']['confidence']}\t"
                        f"{ent['classification']['reason']}\t{ent['label']}\t{','.join(ent['digests'])}\n")
    with open(REVIEW / "unresolved_redirects.tsv", "w", encoding="utf-8") as f:
        f.write("register_line\tfrom_entry\tto_target\n")
        for line, lab, target in unresolved:
            f.write(f"{line}\t{lab}\t{target}\n")
    n = collections.Counter(ent["type"] for ent in entities)
    print(f"  entries {len(entries)}, entities {len(entities)} ({dict(n)}), "
          f"redirects {sum(1 for e in entries if e['type']=='redirect')}, unresolved {len(unresolved)}")


def _key(s: str) -> str:
    s = re.sub(r"\s+", " ", s.lower()).strip(" ,")
    return re.sub(r"\s+,", ",", s)


def tidy(s):
    if s is None:
        return None
    s = re.sub(r"\s+,", ",", re.sub(r"\s+", " ", s)).strip(" ,")
    return re.sub(r",(?=\S)", ", ", s)


if __name__ == "__main__":
    run()
