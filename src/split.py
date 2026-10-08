"""Step 7: fixed catalogue / test split of the digests (ids only).

Digests that mention at least one person are shuffled with a fixed seed and
20 % are held out.  The lists are the published split; task files (catalogue
profiles, test items with gold) are derived from them by the consumer.
"""
import random

from .common import DATA, read_jsonl

SEED = 20261006
TEST_SHARE = 0.2


def run():
    digests = read_jsonl(DATA / "digests.jsonl")
    with_person = [d["id"] for d in digests if d["entities"]["person"]]
    order = with_person[:]
    random.Random(SEED).shuffle(order)
    n_test = round(len(order) * TEST_SHARE)
    pos = {d: i for i, d in enumerate(with_person)}
    test_ids = sorted(order[:n_test], key=pos.get)
    cat_ids = sorted(order[n_test:], key=pos.get)
    (DATA / "splits").mkdir(exist_ok=True)
    (DATA / "splits" / "catalogue_digests.txt").write_text("\n".join(cat_ids) + "\n", encoding="utf-8")
    (DATA / "splits" / "test_digests.txt").write_text("\n".join(test_ids) + "\n", encoding="utf-8")
    print(f"  catalogue digests {len(cat_ids)}, test digests {len(test_ids)} (seed {SEED})")
