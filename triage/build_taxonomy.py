#!/usr/bin/env python3
"""Derive triage/taxonomy.json from papers/papers.jsonl.

Everything in taxonomy.json is a MEASUREMENT of the pool that stage-2 triage
actually produced.  Nothing in it is reconstructed or guessed -- unlike
stage1_prompt.md / stage2_prompt.md, which are reconstructions.  Re-run after
papers.jsonl changes:

    python3 triage/build_taxonomy.py            # writes triage/taxonomy.json
    python3 triage/build_taxonomy.py --check    # non-zero exit if stale
"""
import collections, json, os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, "papers", "papers.jsonl")
OUT = os.path.join(HERE, "taxonomy.json")

# Certificate vocabulary the corpus is supposed to cover.  Each entry is
# (label, regex) and is matched against the ONLY free text the pool carries:
# title + family + method + candidate_generator + candidate_verifier.
# papers.jsonl has no abstract, so a zero here means "this vocabulary never
# appears in triage's own output", NOT "no such paper is in the pool".
CERT_PROBES = [
    ("rational_sos",                r"sum[- ]of[- ]squares|\bSOS\b"),
    ("gram_matrix",                 r"Gram matrix"),
    ("nullstellensatz",             r"Nullstellensatz"),
    ("positivstellensatz",          r"Positivstellensatz"),
    ("farkas_lp_duality",           r"Farkas|\bLP dual|linear programming dual|primal[- ]dual"),
    ("algebraic_number",            r"minimal polynomial|isolating interval|real root isolation"),
    ("lyapunov_barrier",            r"Lyapunov|barrier certificate"),
    ("symbolic_identity",           r"symbolic integration|antiderivative|Risch"),
    ("telescoping_gosper_zeilberger", r"telescop|Gosper|Zeilberger"),
    ("certified_residual_interval", r"interval arithmetic|certified enclosure|residual bound"),
    ("exact_geometric_coordinates", r"exact coordinates|rational coordinates|order type"),
    ("primal_dual_optimality",      r"duality gap|complementary slackness|dual witness"),
]

# Coarse read of what a solver would actually be handed, inferred from the
# triage verifier sentence.  This is a HEURISTIC over one sentence of text and
# is much weaker than scripts/corpus_report.py, which imports the shipped
# module and inspects the real instance.  Treat it as an indication only.
CORE_PROBES = [
    ("graph",        r"\bgraph|vertic|vertex|edge|adjacen|colou?ring|clique|cycle|tree\b"),
    ("csp_sat",      r"clause|satisfiab|assignment|constraint|literal|\bCSP\b|\bSAT\b"),
    ("exact_cover",  r"cover|packing|partition|tiling|block design|disjoint"),
    ("permutation",  r"permutation|word|sequence of moves|rearrang"),
    ("arithmetic",   r"modul|congruen|prime|integer solution|divisib"),
    ("algebraic",    r"polynomial|ideal|matrix|field|group element|homomorph"),
    ("geometric",    r"coordinate|distance|point set|convex|embedding|realiz"),
]


def load():
    if not os.path.exists(SRC):
        sys.exit(f"ERROR: {SRC} not found")
    return [json.loads(l) for l in open(SRC) if l.strip()]


def blob(r):
    return " ".join(str(r.get(k, "")) for k in
                    ("title", "family", "method", "candidate_generator", "candidate_verifier"))


def build(rows):
    n = len(rows)
    fam = collections.Counter(r["family"] for r in rows)
    meth = collections.Counter(r["method"] for r in rows)
    pcat = collections.Counter(r.get("primary_cat", "?") for r in rows)
    pairs = collections.Counter((r["family"], r["method"]) for r in rows)
    fields = sorted({k for r in rows for k in r})

    fam_meth = collections.defaultdict(collections.Counter)
    fam_cat = collections.defaultdict(collections.Counter)
    fam_ex = collections.defaultdict(list)
    for r in rows:
        fam_meth[r["family"]][r["method"]] += 1
        fam_cat[r["family"]][r.get("primary_cat", "?")] += 1
        if len(fam_ex[r["family"]]) < 3:
            fam_ex[r["family"]].append(r["arxiv_id"])

    families = [{
        "name": f,
        "papers": c,
        "share": round(c / n, 5),
        "top_methods": [{"method": m, "papers": k} for m, k in fam_meth[f].most_common(3)],
        "top_primary_cats": [{"cat": p, "papers": k} for p, k in fam_cat[f].most_common(3)],
        "example_arxiv_ids": fam_ex[f],
    } for f, c in fam.most_common()]

    meth_fam = collections.defaultdict(collections.Counter)
    for r in rows:
        meth_fam[r["method"]][r["family"]] += 1
    methods = [{
        "name": m,
        "papers": c,
        "share": round(c / n, 5),
        "top_families": [{"family": f, "papers": k} for f, k in meth_fam[m].most_common(3)],
    } for m, c in meth.most_common()]

    certs = []
    for label, pat in CERT_PROBES:
        hits = [r["arxiv_id"] for r in rows if re.search(pat, blob(r), re.I)]
        certs.append({"certificate_family": label, "regex": pat,
                      "papers": len(hits), "share": round(len(hits) / n, 6),
                      "example_arxiv_ids": hits[:3]})

    cores = []
    for label, pat in CORE_PROBES:
        c = sum(1 for r in rows if re.search(pat, blob(r), re.I))
        cores.append({"core_hint": label, "regex": pat,
                      "papers": c, "share": round(c / n, 5)})

    return {
        "_meta": {
            "what_this_is": "DERIVED from papers/papers.jsonl. Measured, not reconstructed.",
            "not_reconstructed": ("Unlike triage/stage1_prompt.md and triage/stage2_prompt.md, "
                                  "which are unverified reconstructions, every number in this "
                                  "file is recomputed from the committed pool by "
                                  "triage/build_taxonomy.py."),
            "generated_by": "triage/build_taxonomy.py",
            "generated_at_utc": datetime.datetime.now(datetime.timezone.utc)
                                 .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_file": "papers/papers.jsonl",
            "records": n,
            "observed_record_fields": fields,
            "taxonomy_levels": {"level_1": "family", "level_2": "method"},
            "caveat_free_text": ("papers.jsonl carries NO abstract. The certificate_vocabulary "
                                 "and core_hint probes below search only title + family + method "
                                 "+ candidate_generator + candidate_verifier, i.e. triage's own "
                                 "output. A zero means the vocabulary never appears in what "
                                 "triage wrote, not that no such paper exists in the 348k pool."),
            "caveat_core_hint": ("core_hint is a one-sentence regex heuristic and is much weaker "
                                 "than scripts/corpus_report.py, which imports each shipped "
                                 "module and inspects the actual instance. Categories overlap; "
                                 "shares do not sum to 1."),
        },
        "agreement": dict(collections.Counter(r.get("agreement", "?") for r in rows)),
        "year_histogram": dict(sorted(collections.Counter(
            str(r.get("year", "?")) for r in rows).items())),
        "families": families,
        "methods": methods,
        "top_family_method_pairs": [
            {"family": f, "method": m, "papers": c} for (f, m), c in pairs.most_common(15)],
        "primary_categories": [
            {"cat": c, "papers": k, "share": round(k / n, 5)} for c, k in pcat.most_common()],
        "certificate_vocabulary": certs,
        "core_hint_distribution": cores,
    }


def main():
    rows = load()
    data = build(rows)
    if "--check" in sys.argv:
        if not os.path.exists(OUT):
            sys.exit("STALE: triage/taxonomy.json missing")
        old = json.load(open(OUT))
        # Compare everything except the timestamp.  An earlier version of this
        # check dropped the whole _meta block, which made it blind to a SCHEMA
        # change: another engineer added a `hardness_evidence` column to
        # papers.jsonl and --check still reported "current", because
        # observed_record_fields lives in _meta.
        a, b = json.loads(json.dumps(old)), json.loads(json.dumps(data))
        for d in (a, b):
            d.get("_meta", {}).pop("generated_at_utc", None)
        if a != b:
            diffs = [k for k in set(a) | set(b) if a.get(k) != b.get(k)]
            if "_meta" in diffs:
                m1, m2 = a.get("_meta", {}), b.get("_meta", {})
                diffs = [d for d in diffs if d != "_meta"] + [
                    f"_meta.{k}" for k in set(m1) | set(m2) if m1.get(k) != m2.get(k)]
            sys.exit("STALE: triage/taxonomy.json disagrees with papers/papers.jsonl; "
                     f"differing sections: {sorted(diffs)}")
        print("taxonomy.json is current")
        return
    with open(OUT, "w") as fh:
        json.dump(data, fh, indent=1)
        fh.write("\n")
    print(f"wrote {OUT}  ({data['_meta']['records']} records, "
          f"{len(data['families'])} families, {len(data['methods'])} methods)")


if __name__ == "__main__":
    main()
