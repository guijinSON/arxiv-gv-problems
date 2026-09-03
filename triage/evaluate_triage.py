#!/usr/bin/env python3
"""Score a triage prompt against triage/gold_coverage_set.jsonl.

WHY PER-FAMILY RECALL.  The pool this repo was built from is 80% discrete and
contains zero papers whose triage text mentions Lyapunov functions, symbolic
integration, telescoping or interval arithmetic (see triage/taxonomy.json,
certificate_vocabulary).  An aggregate accuracy number cannot see that: a screen
that is right about most papers and blind to three certificate families still
scores in the 80s.  So this harness refuses to report a single number.  It
reports recall PER certificate family and FAILS SEPARATELY, with its own exit
code, when overall accuracy looks fine while some family is at or near zero.
That masked case is the failure mode the corpus actually suffered.

EXIT CODES
  0  PASS            every family above --min-family-recall, and the aggregate
                     and specificity bars are met
  1  MASKED COLLAPSE aggregate accuracy and specificity look FINE, but at least
                     one certificate family is at or below --near-zero.  This is
                     the headline failure this script exists to catch.
  2  FAIL            an ordinary failure: aggregate below --min-overall, or
                     specificity below --min-specificity, or a family below
                     --min-family-recall without the masking condition
  3  USAGE / DATA ERROR

USAGE
  python3 triage/evaluate_triage.py --self-test
  python3 triage/evaluate_triage.py --prompt triage/stage1_prompt.md --classifier vocab
  python3 triage/evaluate_triage.py --prompt triage/stage2_prompt.md \
      --classifier cmd --cmd 'my-llm-cli --model X'   # real model, needs API access
"""
import argparse, hashlib, json, os, re, subprocess, sys
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GOLD = os.path.join(HERE, "gold_coverage_set.jsonl")
DEFAULT_PROMPT = os.path.join(HERE, "stage1_prompt.md")

REQUIRED_FIELDS = ("id", "certificate_family", "why_it_qualifies",
                   "expected_label", "source", "notes")
LABELS = ("keep", "drop")
NEGATIVE_FAMILY = "negative_control"

EXIT_PASS, EXIT_MASKED, EXIT_FAIL, EXIT_ERROR = 0, 1, 2, 3


# --------------------------------------------------------------------- gold set
def load_gold(path):
    if not os.path.exists(path):
        raise SystemExit(f"ERROR: gold set not found: {path}")
    entries, seen = [], set()
    for ln, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"ERROR: {path}:{ln}: bad JSON: {exc}")
        missing = [f for f in REQUIRED_FIELDS if f not in e]
        if missing:
            raise SystemExit(f"ERROR: {path}:{ln}: missing fields {missing}")
        if e["expected_label"] not in LABELS:
            raise SystemExit(f"ERROR: {path}:{ln}: expected_label must be one of {LABELS}")
        src = e["source"]
        if src != "constructed" and not src.startswith("arxiv:"):
            raise SystemExit(f"ERROR: {path}:{ln}: source must be 'constructed' or 'arxiv:<id>'")
        if e["id"] in seen:
            raise SystemExit(f"ERROR: {path}:{ln}: duplicate id {e['id']}")
        seen.add(e["id"])
        entries.append(e)
    if not entries:
        raise SystemExit(f"ERROR: {path} is empty")
    return entries


PROMPT_BEGIN = "<!-- PROMPT-BEGIN -->"
PROMPT_END = "<!-- PROMPT-END -->"


def load_prompt(path):
    """Return (body, full_text).

    A reconstructed prompt file carries disclaimers and reconstruction notes that
    are NOT part of the prompt.  If the file fences the prompt with
    <!-- PROMPT-BEGIN --> / <!-- PROMPT-END -->, only the fenced body is scored:
    otherwise a note saying 'this prompt never mentions Lyapunov functions' would
    itself make the vocabulary probe find the word Lyapunov.
    """
    full = open(path, encoding="utf-8").read()
    if PROMPT_BEGIN in full and PROMPT_END in full:
        body = full.split(PROMPT_BEGIN, 1)[1].split(PROMPT_END, 1)[0]
    else:
        body = full
    return body, full


def entry_text(e):
    """Everything a stage-1 screen would see, plus the gold rationale fields."""
    parts = [e.get("title", ""), e.get("categories", ""), e.get("blurb", ""),
             e.get("why_it_qualifies", ""), e.get("certificate_object", ""),
             e.get("verification", "")]
    return " ".join(str(p) for p in parts)


# ------------------------------------------------------------------ classifiers
def stub_oracle(e, prompt):
    return e["expected_label"]


# Families the pool actually reaches, read off triage/taxonomy.json's
# certificate_vocabulary counts (>= 7 papers).  Everything else the pool has
# essentially none of.  This stub simulates the measured bias directly.
POOL_REACHED = {"rational_sos", "gram_matrix", "exact_geometric_coordinates", "nullstellensatz"}


def stub_combinatorial_prior(e, prompt):
    if e["expected_label"] == "drop":
        return "drop"
    return "keep" if e["certificate_family"] in POOL_REACHED else "drop"


# Blind to exactly the three families with a zero count in the pool AND no
# discrete surrogate: this is the subtle version, and the one that masks.
BLIND_TO = {"lyapunov_barrier", "symbolic_identity", "telescoping_gosper_zeilberger"}


def stub_analysis_blind(e, prompt):
    if e["certificate_family"] in BLIND_TO:
        return "drop"
    return e["expected_label"]


def stub_accept_all(e, prompt):
    return "keep"


def stub_reject_all(e, prompt):
    return "drop"


STUBS = OrderedDict([
    ("oracle", stub_oracle),
    ("analysis_blind", stub_analysis_blind),
    ("combinatorial_prior", stub_combinatorial_prior),
    ("accept_all", stub_accept_all),
    ("reject_all", stub_reject_all),
])


def make_vocab_classifier(prompt_text):
    """Vocabulary-reachability probe.  Offline, no model.

    Keeps an entry iff at least one of its cue_terms occurs in the prompt.  This
    measures ONE thing: whether the prompt's own vocabulary can steer a screen
    toward that certificate family at all.  It is a crude LOWER BOUND on what a
    prompt can select for, NOT a prediction of model behaviour -- a model can
    generalise past its prompt's wording, and a prompt containing a word is no
    guarantee the model acts on it.  Read a vocab failure as 'this prompt cannot
    even name the family', which is still a real defect.
    """
    low = prompt_text.lower()

    def clf(e, prompt):
        cues = e.get("cue_terms") or []
        return "keep" if any(str(c).lower() in low for c in cues) else "drop"
    return clf


def make_cmd_classifier(cmd):
    """Shell out to a real classifier, one gold entry per call.

    stdin  : {"prompt": <prompt text>, "entry": <gold entry minus the answer>}
    stdout : either the bare word keep/drop, or JSON {"label": "keep"|"drop"}
    A non-zero exit or unparseable output counts as an ERROR, not as a drop --
    silently scoring API failures as rejections is how a broken harness reports
    a fake collapse.
    """
    def clf(e, prompt):
        payload = {k: v for k, v in e.items()
                   if k not in ("expected_label", "why_it_qualifies", "notes")}
        stdin = json.dumps({"prompt": prompt, "entry": payload})
        try:
            p = subprocess.run(cmd, shell=True, input=stdin, capture_output=True,
                               text=True, timeout=180)
        except subprocess.TimeoutExpired:
            return "error"
        if p.returncode != 0:
            return "error"
        out = p.stdout.strip()
        try:
            lab = json.loads(out).get("label", "")
        except Exception:
            lab = out
        lab = str(lab).strip().strip('"').lower()
        m = re.search(r"\b(keep|drop)\b", lab)
        return m.group(1) if m else "error"
    return clf


# ---------------------------------------------------------------------- scoring
def score(entries, clf, prompt_text):
    per_family = defaultdict(lambda: {"n": 0, "hit": 0})
    rows, errors = [], 0
    tp = fp = tn = fn = 0
    for e in entries:
        got = clf(e, prompt_text)
        if got not in LABELS:
            errors += 1
            rows.append({"id": e["id"], "family": e["certificate_family"],
                         "expected": e["expected_label"], "got": got})
            continue
        exp = e["expected_label"]
        rows.append({"id": e["id"], "family": e["certificate_family"],
                     "expected": exp, "got": got})
        if exp == "keep":
            fam = per_family[e["certificate_family"]]
            fam["n"] += 1
            if got == "keep":
                fam["hit"] += 1
                tp += 1
            else:
                fn += 1
        else:
            if got == "drop":
                tn += 1
            else:
                fp += 1
    n_scored = tp + fp + tn + fn
    fam_recall = {f: (d["hit"] / d["n"] if d["n"] else None)
                  for f, d in per_family.items()}
    live = [r for r in fam_recall.values() if r is not None]
    return {
        "entries_total": len(entries),
        "entries_scored": n_scored,
        "classifier_errors": errors,
        "keep_total": tp + fn, "drop_total": tn + fp,
        "overall_accuracy": (tp + tn) / n_scored if n_scored else 0.0,
        "keep_recall_micro": tp / (tp + fn) if (tp + fn) else 0.0,
        "specificity": tn / (tn + fp) if (tn + fp) else None,
        "macro_family_recall": sum(live) / len(live) if live else 0.0,
        "worst_family_recall": min(live) if live else None,
        "worst_family": (min(fam_recall.items(), key=lambda kv: (kv[1] is None, kv[1]))[0]
                         if live else None),
        "families_balanced": len({d["n"] for d in per_family.values()}) <= 1,
        "per_family": {f: {"keeps": per_family[f]["n"], "found": per_family[f]["hit"],
                           "recall": fam_recall[f]} for f in sorted(per_family)},
        "rows": rows,
    }


def verdict(s, args):
    """Return (exit_code, headline, [reasons])."""
    reasons = []
    zero, low = [], []
    for f, d in s["per_family"].items():
        r = d["recall"]
        if r is None:
            continue
        if r <= args.near_zero:
            zero.append((f, r))
        elif r < args.min_family_recall:
            low.append((f, r))

    agg_ok = s["overall_accuracy"] >= args.min_overall
    spec = s["specificity"]
    spec_ok = spec is None or spec >= args.min_specificity

    if s["classifier_errors"] and not args.allow_errors:
        reasons.append(f"{s['classifier_errors']} classifier errors "
                       f"(pass --allow-errors to score anyway)")
        return EXIT_FAIL, "FAIL (classifier errors)", reasons

    if not agg_ok:
        reasons.append(f"overall accuracy {s['overall_accuracy']:.3f} "
                       f"< --min-overall {args.min_overall}")
    if not spec_ok:
        reasons.append(f"specificity {spec:.3f} < --min-specificity "
                       f"{args.min_specificity} (negative controls are being kept)")
    for f, r in zero:
        reasons.append(f"family '{f}' recall {r:.2f} <= --near-zero {args.near_zero}")
    for f, r in low:
        reasons.append(f"family '{f}' recall {r:.2f} < --min-family-recall "
                       f"{args.min_family_recall}")

    if agg_ok and spec_ok and zero:
        reasons.insert(0, (f"aggregate looks fine (accuracy {s['overall_accuracy']:.3f}, "
                           f"specificity {spec:.3f}) while {len(zero)} certificate famil"
                           f"{'y is' if len(zero) == 1 else 'ies are'} at or below "
                           f"{args.near_zero}: {', '.join(f for f, _ in zero)}"))
        return EXIT_MASKED, "MASKED COLLAPSE", reasons
    if reasons:
        return EXIT_FAIL, "FAIL", reasons
    return EXIT_PASS, "PASS", []


# ----------------------------------------------------------------------- output
def bar(r, width=20):
    if r is None:
        return " " * width
    n = int(round(r * width))
    return "#" * n + "." * (width - n)


def report(s, args, meta, code, headline, reasons, fh=sys.stdout):
    w = fh.write
    w("=" * 74 + "\n")
    w(f"triage prompt evaluation\n")
    w("=" * 74 + "\n")
    w(f"  gold set    : {meta['gold']}\n")
    w(f"  entries     : {s['entries_total']} "
      f"({s['keep_total']} keep / {s['drop_total']} drop)\n")
    w(f"  prompt      : {meta['prompt']}\n")
    w(f"  prompt sha256: {meta['prompt_sha256'][:16]}  (whole file)\n")
    if "prompt_body_chars" in meta:
        w(f"  prompt body : {meta['prompt_body_chars']} of "
          f"{meta['prompt_file_chars']} chars"
          f"{' (PROMPT-BEGIN/END fenced; disclaimers excluded)' if meta['prompt_fenced'] else ' (whole file - no fence markers found)'}\n")
    w(f"  classifier  : {meta['classifier']}\n")
    w("\n-- aggregate (deliberately NOT the headline) -------------------------\n")
    spec = s["specificity"]
    w(f"  overall accuracy    : {s['overall_accuracy']:.3f}\n")
    w(f"  keep recall (micro) : {s['keep_recall_micro']:.3f}\n")
    w(f"  specificity (drops) : {'n/a' if spec is None else f'{spec:.3f}'}\n")
    w(f"  macro family recall : {s['macro_family_recall']:.3f}\n")
    gapnote = ("0 by construction: every family has the same number of keeps"
               if s["families_balanced"]
               else "large positive = big families are carrying small ones")
    w(f"  micro - macro gap   : "
      f"{s['keep_recall_micro'] - s['macro_family_recall']:+.3f}   ({gapnote})\n")
    if s["worst_family"] is not None:
        w(f"  worst family recall : {s['worst_family_recall']:.3f}  "
          f"({s['worst_family']})   <-- the number the aggregate hides\n")
    if s["classifier_errors"]:
        w(f"  classifier errors   : {s['classifier_errors']}\n")
    w("\n-- recall per certificate family (the headline) ----------------------\n")
    w(f"  {'certificate family':32s} {'found/keeps':>11s} {'recall':>7s}  {'':20s} status\n")
    for f, d in s["per_family"].items():
        r = d["recall"]
        if r is None:
            st = "n/a"
        elif r <= args.near_zero:
            st = "ZERO-ish  <-- collapse"
        elif r < args.min_family_recall:
            st = "LOW"
        else:
            st = "ok"
        w(f"  {f:32s} {d['found']:>5d}/{d['keeps']:<5d} {r:>7.2f}  {bar(r)} {st}\n")
    w("\n-- verdict -----------------------------------------------------------\n")
    w(f"  {headline}   (exit {code})\n")
    for r in reasons:
        w(f"    - {r}\n")
    if code == EXIT_PASS:
        w("    - no certificate family below the bar\n")
    w("=" * 74 + "\n")


# -------------------------------------------------------------------- self-test
SELFTEST_CASES = [
    ("oracle", EXIT_PASS,
     "a perfect screen must pass"),
    ("analysis_blind", EXIT_MASKED,
     "blind to 3 families but right about everything else: aggregate stays high, "
     "so this MUST be caught as a masked collapse, not reported as a pass"),
    ("combinatorial_prior", EXIT_FAIL,
     "keeps only the families the real pool reaches: aggregate collapses too, so "
     "this is an ordinary failure"),
    ("accept_all", EXIT_FAIL,
     "keeps everything: per-family recall is a perfect 1.00 everywhere and "
     "accuracy still looks respectable, so the specificity bar is what must catch it"),
    ("reject_all", EXIT_FAIL,
     "drops everything: every family at zero and the aggregate is gone too"),
]


def self_test(args):
    print("#" * 74)
    print("# evaluate_triage.py --self-test")
    print("#   Offline. No API, no network, no prompt file needed. This tests the")
    print("#   HARNESS, not any prompt: each stub classifier has a known failure")
    print("#   mode and a required exit code.")
    print("#" * 74)

    entries = load_gold(args.gold)
    fams = sorted({e["certificate_family"] for e in entries
                   if e["expected_label"] == "keep"})
    n_keep = sum(1 for e in entries if e["expected_label"] == "keep")
    n_drop = len(entries) - n_keep
    n_real = sum(1 for e in entries if str(e["source"]).startswith("arxiv:"))

    print(f"\n[gold] {args.gold}")
    print(f"[gold] {len(entries)} entries: {n_keep} keep, {n_drop} drop")
    print(f"[gold] {n_real} real arXiv papers, {len(entries) - n_real} constructed exemplars")
    print(f"[gold] {len(fams)} certificate families with keeps: {', '.join(fams)}")

    problems = []
    if len(entries) < 40:
        problems.append(f"gold set has {len(entries)} entries, spec requires >= 40")
    if n_drop == 0:
        problems.append("gold set has no negative controls, so specificity is meaningless")
    thin = [f for f in fams
            if sum(1 for e in entries
                   if e["certificate_family"] == f and e["expected_label"] == "keep") < 3]
    if thin:
        problems.append(f"families with fewer than 3 keeps (recall too coarse): {thin}")

    failures = list(problems)
    for name, want, why in SELFTEST_CASES:
        s = score(entries, STUBS[name], "")
        code, headline, reasons = verdict(s, args)
        ok = code == want
        print(f"\n{'-' * 74}\n[stub] {name}   expect exit {want}, got exit {code}   "
              f"{'OK' if ok else 'MISMATCH'}")
        print(f"       why: {why}")
        report(s, args, {"gold": args.gold, "prompt": "(none - stub)",
                         "prompt_sha256": "0" * 64,
                         "classifier": f"stub:{name}"}, code, headline, reasons)
        if not ok:
            failures.append(f"stub {name}: expected exit {want}, got {code}")

    print("#" * 74)
    if failures:
        print("# SELF-TEST FAILED")
        for f in failures:
            print(f"#   - {f}")
        print("#" * 74)
        return EXIT_FAIL
    print(f"# SELF-TEST PASSED: {len(SELFTEST_CASES)} stub scenarios, "
          f"gold set validated ({len(entries)} entries, {len(fams)} families)")
    print("#" * 74)
    return EXIT_PASS


# ------------------------------------------------------------------------- main
def main(argv=None):
    p = argparse.ArgumentParser(
        description="Score a triage prompt against the gold coverage set, "
                    "reporting recall per certificate family.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    p.add_argument("--gold", default=DEFAULT_GOLD)
    p.add_argument("--prompt", nargs="+", default=[DEFAULT_PROMPT],
                   help="prompt file(s) under test. Several are concatenated in "
                        "order, so a base prompt can be scored against "
                        "base + addendum without editing either file.")
    p.add_argument("--classifier", default="vocab",
                   help="vocab | cmd | stub:<name> "
                        f"({', '.join(STUBS)})")
    p.add_argument("--cmd", default=None, help="shell command for --classifier cmd")
    p.add_argument("--min-overall", type=float, default=0.70)
    p.add_argument("--min-family-recall", type=float, default=0.50)
    p.add_argument("--near-zero", type=float, default=0.20,
                   help="a family at or below this counts as collapsed")
    p.add_argument("--min-specificity", type=float, default=0.50)
    p.add_argument("--allow-errors", action="store_true",
                   help="score even if the classifier errored on some entries")
    p.add_argument("--json", default=None, help="also write the full result as JSON here")
    p.add_argument("--self-test", action="store_true",
                   help="offline harness test with stub classifiers; no prompt or API needed")
    args = p.parse_args(argv)

    if args.near_zero > args.min_family_recall:
        print("ERROR: --near-zero must be <= --min-family-recall", file=sys.stderr)
        return EXIT_ERROR

    try:
        if args.self_test:
            return self_test(args)

        entries = load_gold(args.gold)
        bodies, fulls, fenced = [], [], False
        for path in args.prompt:
            if not os.path.exists(path):
                print(f"ERROR: prompt file not found: {path}", file=sys.stderr)
                return EXIT_ERROR
            b, f = load_prompt(path)
            fenced = fenced or len(b) < len(f)
            bodies.append(b)
            fulls.append(f)
        prompt_text = "\n\n".join(bodies)
        prompt_full = "\n\n".join(fulls)
        sha = hashlib.sha256(prompt_full.encode("utf-8")).hexdigest()

        spec = args.classifier
        if spec.startswith("stub:"):
            name = spec.split(":", 1)[1]
            if name not in STUBS:
                print(f"ERROR: unknown stub {name!r}; have {list(STUBS)}", file=sys.stderr)
                return EXIT_ERROR
            clf = STUBS[name]
        elif spec == "vocab":
            clf = make_vocab_classifier(prompt_text)
        elif spec == "cmd":
            if not args.cmd:
                print("ERROR: --classifier cmd requires --cmd", file=sys.stderr)
                return EXIT_ERROR
            clf = make_cmd_classifier(args.cmd)
        else:
            print(f"ERROR: unknown --classifier {spec!r}", file=sys.stderr)
            return EXIT_ERROR
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return EXIT_ERROR

    s = score(entries, clf, prompt_text)
    code, headline, reasons = verdict(s, args)
    meta = {"gold": args.gold, "prompt": " + ".join(args.prompt), "prompt_sha256": sha,
            "prompt_body_chars": len(prompt_text),
            "prompt_file_chars": len(prompt_full),
            "prompt_fenced": bool(fenced),
            "classifier": spec if spec != "cmd" else f"cmd: {args.cmd}"}
    report(s, args, meta, code, headline, reasons)
    if args.json:
        out = {"meta": meta, "thresholds": {
                   "min_overall": args.min_overall,
                   "min_family_recall": args.min_family_recall,
                   "near_zero": args.near_zero,
                   "min_specificity": args.min_specificity},
               "exit_code": code, "verdict": headline, "reasons": reasons,
               **{k: v for k, v in s.items() if k != "rows"},
               "rows": s["rows"]}
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1)
            fh.write("\n")
        print(f"wrote {args.json}")
    return code


if __name__ == "__main__":
    sys.exit(main())
