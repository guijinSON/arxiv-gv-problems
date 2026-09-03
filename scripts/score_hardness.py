#!/usr/bin/env python3
"""Attach a WEAK, METADATA-ONLY hardness prior to every record in papers/papers.jsonl.

WHAT THIS IS NOT
================
This is **not** a verified hardness claim, and nothing downstream should treat it as
one.  `papers/papers.jsonl` carries no abstract.  The only text per record is:

    title, all_cats/primary_cat, family, method, candidate_generator, candidate_verifier

`family` / `method` are a controlled vocabulary; `candidate_generator` and
`candidate_verifier` are the triage model's one-line *hypothesis* about how an
instance would be built and checked -- they describe a construction, not a theorem.
So every score here is derived from **a paper title plus a triage hypothesis plus an
arXiv category**.  That is why `confidence` is hardcoded to `"metadata"` on every
record and no other value is reachable.

Concretely, what this cannot see:

  * a hardness theorem that is in the abstract or body but not the title -- which is
    the common case.  A title like "The Complexity of Finding and Counting
    Subtournaments" almost certainly wraps an NP-hardness result, and this script
    scores it `none`.
  * whether the hardness is for the *regime the builder would actually ship*.  Most
    hardness results are worst-case over a family; the generator draws random
    instances.  `AUDIT.md` documents five families that were provably in the right
    worst-case regime and still fell to a textbook solver in under a minute.
  * whether the paper's own algorithm section defeats the construction.

So: a `none` here means "no hardness word survived in the title", NOT "this paper has
no hardness result".  A non-`none` here means "a hardness word appears in the title",
NOT "this family is hard".  **The false-negative rate is large and unquantified.**
The right fix is a pass over abstracts -- available in the full arXiv metadata
snapshot, which is not in this repo -- and that pass would supersede this file
entirely.  Treat this as a cheap pre-read ranking signal only: it is meant to stop a
builder burning a 33-page read on a paper whose title already says there is nothing
to lean on, not to certify the ones it marks.

WHAT IT DOES
============
Adds, as the last field of each record:

    "hardness_evidence": {
        "class":      one of NP-hard / NP-complete / W[1] / ETH / #P / PSPACE /
                      coNP / ER / undecidable / crypto / none,
        "signal":     the matched substrings, each tagged by provenance,
        "confidence": "metadata"   (always -- see above),
        "regime":     short restriction string lifted from the title, or null
    }

Signal provenance tags keep text and category evidence distinguishable:

    title:<substr>   matched in the (normalised) title
    hyp:<substr>     matched in method / candidate_generator / candidate_verifier,
                     i.e. in the triage hypothesis, not in anything the authors wrote
    field:k=v        a controlled-vocabulary field value (method=trapdoor, ...)
    cat:<X>          X is the primary arXiv category
    xcat:<X>         X is cross-listed but not primary

CATEGORY IS A PRIOR, NOT A VERDICT
==================================
A category alone NEVER sets a class.  `cat:cs.CC` / `cat:cs.CR` are recorded as
priors so a reader can re-rank, but 718 of the 962 cs.CC papers have no hardness word
in the title and are scored `none` -- promoting them wholesale would manufacture
~700 unearned NP-hard labels.  Category is allowed to promote in exactly one narrow
case: a *weak* token that is uninformative on its own ("dichotomy", "fine-grained",
"conditional lower bound") is promoted to NP-hard only when cs.CC is present.  A CSP
dichotomy theorem does contain an NP-completeness proof for the hard side, so this is
defensible, but it is the weakest rule here and it is reported separately so it can
be subtracted.

Deliberately NOT used as signals, because they are dominated by false positives in
this corpus: bare "complexity" (749 title hits: "sample complexity", "Borel
complexity", "geometric complexity theory", "communication complexity"), bare "lower
bound" (110 hits, nearly all combinatorial bounds -- cap sets, van der Waerden
numbers), and bare "FPT"/"parameterized" (468 hits; fixed-parameter *tractability* is
an upper bound, not evidence of hardness).

KNOWN GAPS IN THE ENUM
======================
The class enum is fixed by the schema, so two EXPTIME-complete papers ("Cops and
Robbers is EXPTIME-complete", "Towards EXPTIME One Way Functions") score `none`
rather than being folded into PSPACE, which would be a mislabel in the wrong
direction.  `#P` is effectively dead: no title in the corpus contains "#P-hard" or
"#P-complete", so that class comes out empty -- an artifact of having only titles,
not evidence that no counting-hardness papers are in the pool.

USAGE
=====
    python3 scripts/score_hardness.py --dry-run     # distribution only, no write
    python3 scripts/score_hardness.py               # rewrite in place, then report
    python3 scripts/score_hardness.py --path X.jsonl

Idempotent: re-running replaces any existing hardness_evidence and keeps it last.
Existing fields are never re-serialised -- the original line text before the
appended field is preserved byte for byte -- and every rewritten line is parsed back
and compared against the original record before it is accepted.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter, OrderedDict

DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "papers", "papers.jsonl"
)

FIELD = "hardness_evidence"
MARKER = ', "%s": ' % FIELD
MAX_SIGNALS = 12

# --------------------------------------------------------------------------
# normalisation
# --------------------------------------------------------------------------
# Titles are LaTeX-ish: "$\exists\mathbb{R}$-Complete", "NP\nobreakdash-hard",
# "Mis\`ere".  Dropping backslashes and folding dashes/whitespace makes one pattern
# per concept enough.  Recorded signal substrings come from this normalised form, so
# "NP-Complete" and "np-complete" both record as "np-complete".
_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")


def normalise(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.translate(_DASHES).replace("\\", "")).lower()


# --------------------------------------------------------------------------
# class patterns, most specific first -- this ordering IS the precedence
# --------------------------------------------------------------------------
# Each entry: (class, compiled pattern).  Every pattern that fires contributes to
# `signal`; the first one in this list that fires decides `class`.
CLASS_PATTERNS = [
    ("undecidable", r"\bundecidab\w*|\bhalting problem\b"),
    ("PSPACE", r"\bpspace\w*"),
    ("ER", r"\ber-(?:hard|complete)\w*"
           r"|existential theory of the reals"
           r"|exists\s*mathbb\s*\{?r\}?"),
    ("#P", r"#\s*p-(?:hard|complete)\w*|\bsharp-?p-(?:hard|complete)\w*"),
    ("coNP", r"\bco-?np-(?:hard|complete)\w*"),
    ("W[1]", r"\bw\[[12tp]\]-(?:hard|complete)\w*"),
    ("ETH", r"\bs?eth\b|\bgap-eth\b|exponential[- ]time hypothesis"),
    ("NP-complete", r"\bnp-?complete\w*|\{np\}\$?-?complete\w*"),
    ("NP-hard", r"\bnp-?hard\w*|\(np-?\)\s*hard\w*|\{np\}\$?-?hard\w*"),
]
CLASS_PATTERNS = [(c, re.compile(p)) for c, p in CLASS_PATTERNS]

# Generic hardness language: asserts a hardness result without naming a class.
# Mapped to "NP-hard" as the weakest named class -- the real theorem may well be
# stronger (APX-hardness, W[1]-hardness) or in a class this enum does not carry.
GENERIC_HARD = re.compile(
    r"\bhardness\b"
    r"|\bintractab\w*"
    r"|\binapproximab\w*|\bapx-hard\b|\bhard to approximate\b"
    r"|\b(?:is|are|remains?|provably) hard\b"
    r"|\bhard to \w+"
    r"|\bhard problems?\b"
)

# Cryptographic hardness assumptions.  Curated: "hash", "signature", "secure" and
# friends are omitted because they fire on constructions rather than assumptions.
CRYPTO_TEXT = re.compile(
    r"\bone-?way (?:function|permutation)\w*"
    r"|\btrapdoor\w*"
    r"|\blwe\b|\blearning with errors\b|\bshort integer solution\b"
    r"|\bdiscrete logarith\w*"
    r"|\bpost-?quantum\b"
    r"|\blattice-?based (?:crypt|signature|scheme)\w*"
    r"|\bcollision[- ]resistan\w*"
    r"|\bcryptograph\w*|\bcryptanaly\w*|\bcryptosystem\w*"
    r"|\bzero-?knowledge\b"
    r"|\brsa\b"
)

# Crypto vocabulary that is ALSO ordinary mathematics.  "isogeny" is used by 18
# arithmetic-geometry papers in this pool with no cryptographic content at all
# ("Explicit isogenies of prime degree over number fields"), so these count only
# when a crypto context is already established.
CRYPTO_GATED = re.compile(r"\bisogen\w*|\bsupersingular\b|\bpreimage\b")

# Weak tokens: uninformative alone, promoted to NP-hard only alongside cs.CC.
WEAK_TEXT = re.compile(
    r"\bdichotom\w*|\bfine-?grained\b|\bconditional(?:ly)? lower bound\w*"
)

# --------------------------------------------------------------------------
# regime extraction
# --------------------------------------------------------------------------
REGIME_PATTERNS = [
    re.compile(r"\beven (?:for|on|in|when|if|with|without|under)\b\s+(.{3,60})"),
    re.compile(r"\bparameteri[sz]ed by\b\s+(.{3,60})"),
    re.compile(r"\brestricted to\b\s+(.{3,60})"),
    re.compile(r"-(?:hard|complete)(?:ness)?\s+(?:for|on|in|over)\s+(.{3,60})"),
    re.compile(r"\bremains?\b[^,]{0,30}?\b(?:on|for|in)\b\s+(.{3,60})"),
]
# A capture that runs into the class token again ("... is W[1]-hard") or into a
# second clause is noise; cut at the first of these.
REGIME_CUTS = re.compile(
    r"\b(?:is|are|and|but|with applications?)\b"
    r"|[,:;()]"
    r"|\s-\s|--"
    r"|\bnp-|\bpspace|\bw\[|\bhard\b|\bcomplete\b|\bhardness\b"
)


def extract_regime(title_norm):
    """Short restriction the hardness is claimed under, or None.

    Best-effort only: it recovers a regime for roughly 8% of classed records and is
    silent otherwise.  It says nothing about whether *random* instances in that
    regime are hard -- see AUDIT.md, where three families sat squarely in the stated
    worst-case regime and were still solved in seconds.
    """
    for pat in REGIME_PATTERNS:
        m = pat.search(title_norm)
        if not m:
            continue
        frag = m.group(1).strip()
        cut = REGIME_CUTS.search(frag)
        if cut:
            frag = frag[: cut.start()]
        frag = frag.strip(" -.$")
        if 3 <= len(frag) <= 48:
            return frag
    return None


# --------------------------------------------------------------------------
# buckets
# --------------------------------------------------------------------------
# Six buckets, assigned from arXiv category and triage family only.
#
# Precedence, and why:
#   1. an *object-specific non-discrete* primary category wins.  math.NT / cs.CG /
#      math.AG / math.OC tell you what the objects are; the author chose them.
#   2. otherwise the triage family, which names the constructed object.
#   3. otherwise a discrete category (math.CO / cs.DM / cs.DS / cs.CC say "this is a
#      combinatorial problem" and nothing more).
#   4. otherwise other.
#
# Rule 1 is deliberately generous toward the non-discrete buckets: a math.AG paper
# whose family says "graph structures" is counted as symbolic_algebra.  That biases
# the supply-ceiling numbers UPWARD, so the ceilings reported below are optimistic
# and the true count of usable non-discrete papers is lower, not higher.
CAT_NONDISCRETE = {}
for _c in ["math.NT"]:
    CAT_NONDISCRETE[_c] = "number_theory"
for _c in ["cs.CG", "math.MG", "math.GT", "math.AT", "math.DG", "math.SG", "math.GN"]:
    CAT_NONDISCRETE[_c] = "geometry_real"
for _c in ["math.AG", "math.AC", "math.RA", "math.GR", "math.QA", "math.RT",
           "math.CT", "math.KT", "cs.SC"]:
    CAT_NONDISCRETE[_c] = "symbolic_algebra"
for _c in ["math.OC", "math.DS", "math.AP", "math.CA", "math.CV", "math.FA",
           "math.NA", "math.PR", "math.SP", "math-ph", "cs.NA",
           "nlin.CD", "nlin.SI", "nlin.PS", "nlin.AO",
           # disordered systems / stat-mech is where continuous optimisation
           # landscapes live; that is exactly the supply this pool lacks.
           "cond-mat.dis-nn", "cond-mat.stat-mech"]:
    CAT_NONDISCRETE[_c] = "dynamics_opt"

CAT_DISCRETE = {"math.CO", "cs.DM", "cs.DS", "cs.CC", "cs.DB", "cs.DC", "cs.SI",
                "cs.MA", "cs.GT"}

FAMILY_BUCKET = {}
for _f in ["graph structures", "designs and codes", "reconfiguration",
           "constraint satisfaction", "words and permutations", "combinatorial games",
           "set system structures", "additive combinatorial structures",
           "schedules and allocations", "games and social choice",
           "matroid structures", "poset structures", "adversarial inputs"]:
    FAMILY_BUCKET[_f] = "discrete"
for _f in ["algebraic decomposition", "algebraic identity solutions",
           "algebraic geometric structures", "algebraic isomorphisms",
           "finite algebraic structures", "finite field constructions"]:
    FAMILY_BUCKET[_f] = "symbolic_algebra"
for _f in ["geometric configurations", "topological structures",
           "differential geometric structures", "polyhedral witnesses"]:
    FAMILY_BUCKET[_f] = "geometry_real"
for _f in ["integer equations", "number field constructions"]:
    FAMILY_BUCKET[_f] = "number_theory"
for _f in ["fixed point solutions"]:
    FAMILY_BUCKET[_f] = "dynamics_opt"
# left unmapped on purpose -> fall through to category, then "other":
#   cryptographic witnesses, program and circuit synthesis, formal proofs,
#   quantum strategies

BUCKETS = ["discrete", "symbolic_algebra", "geometry_real", "dynamics_opt",
           "number_theory", "other"]
NONDISCRETE_BUCKETS = [b for b in BUCKETS if b not in ("discrete", "other")]

CLASSES = ["NP-hard", "NP-complete", "W[1]", "ETH", "#P", "PSPACE", "coNP", "ER",
           "undecidable", "crypto", "none"]

PRIOR_CATS = {"cs.CC", "cs.CR"}


def bucket_of(rec):
    cat = (rec.get("primary_cat") or "").strip()
    fam = (rec.get("family") or "").strip()
    if cat in CAT_NONDISCRETE:
        return CAT_NONDISCRETE[cat]
    if fam in FAMILY_BUCKET:
        return FAMILY_BUCKET[fam]
    if cat in CAT_DISCRETE:
        return "discrete"
    return "other"


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------
def score(rec):
    """Return (hardness_evidence dict, provenance tag) for one record.

    provenance is for the report only: "explicit" (a class was named in text),
    "generic" (hardness asserted, class inferred as the weakest one), "crypto",
    "weak+cat" (promoted only because cs.CC is present), or "none".
    """
    title = normalise(rec.get("title"))
    hyp = normalise(" ".join(str(rec.get(k, "")) for k in
                             ("method", "candidate_generator", "candidate_verifier")))
    primary = (rec.get("primary_cat") or "").strip()
    all_cats = (rec.get("all_cats") or "").split()
    family = (rec.get("family") or "").strip()
    method = (rec.get("method") or "").strip()

    signals = []
    seen = set()

    def add(tag):
        if tag not in seen:
            seen.add(tag)
            signals.append(tag)

    # --- category priors (recorded, never decisive on their own) ---
    if primary in PRIOR_CATS:
        add("cat:%s" % primary)
    for c in all_cats:
        if c in PRIOR_CATS and c != primary:
            add("xcat:%s" % c)
    has_cc = primary == "cs.CC" or "cs.CC" in all_cats

    # --- named complexity classes, in text ---
    chosen = None
    for cls, pat in CLASS_PATTERNS:
        for where, text in (("title", title), ("hyp", hyp)):
            m = pat.search(text)
            if m:
                add("%s:%s" % (where, m.group(0)))
                if chosen is None:
                    chosen = cls
    provenance = "explicit" if chosen else None

    # --- generic hardness language -> weakest named class ---
    generic_hit = False
    for where, text in (("title", title), ("hyp", hyp)):
        m = GENERIC_HARD.search(text)
        if m:
            add("%s:%s" % (where, m.group(0)))
            generic_hit = True
    if chosen is None and generic_hit:
        chosen, provenance = "NP-hard", "generic"

    # --- cryptographic assumptions ---
    crypto_hit = False
    if method == "trapdoor":
        add("field:method=trapdoor")
        crypto_hit = True
    if family == "cryptographic witnesses":
        add("field:family=cryptographic witnesses")
        crypto_hit = True
    for where, text in (("title", title), ("hyp", hyp)):
        m = CRYPTO_TEXT.search(text)
        if m:
            add("%s:%s" % (where, m.group(0)))
            crypto_hit = True
    if crypto_hit or "cs.CR" in all_cats:
        for where, text in (("title", title), ("hyp", hyp)):
            m = CRYPTO_GATED.search(text)
            if m:
                add("%s:%s" % (where, m.group(0)))
                crypto_hit = True
    if chosen is None and crypto_hit:
        chosen, provenance = "crypto", "crypto"

    # --- weak tokens: only with a cs.CC category to lean on ---
    m = WEAK_TEXT.search(title)
    if m:
        add("title:%s" % m.group(0))
        if chosen is None and has_cc:
            chosen, provenance = "NP-hard", "weak+cat"

    if chosen is None:
        chosen, provenance = "none", "none"

    return (
        OrderedDict([
            ("class", chosen),
            ("signal", signals[:MAX_SIGNALS]),
            ("confidence", "metadata"),   # the only value this script can justify
            ("regime", extract_regime(title) if chosen != "none" else None),
        ]),
        provenance,
    )


# --------------------------------------------------------------------------
# line rewriting
# --------------------------------------------------------------------------
def rewrite_line(raw, evidence):
    """Append/replace hardness_evidence without touching any other byte.

    Existing fields are not re-serialised: the prefix of the original line up to the
    appended field is reused verbatim, so field order, spacing and escaping survive.
    """
    line = raw.rstrip("\n").rstrip("\r")
    stripped = line.rstrip()
    if not stripped.endswith("}"):
        raise ValueError("line does not end with '}'")

    idx = stripped.rfind(MARKER)
    if idx != -1:                      # re-run: drop our previous suffix
        base = stripped[:idx]
    else:
        base = stripped[:-1].rstrip()

    tail = json.dumps(evidence)
    if base.rstrip() == "{":
        return '{"%s": %s}' % (FIELD, tail)
    return "%s, \"%s\": %s}" % (base, FIELD, tail)


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------
def report(class_counts, bucket_class, bucket_counts, prov_counts, total):
    print("papers scored: %d\n" % total)

    print("=== hardness_evidence.class ===")
    width = max(len(c) for c in CLASSES)
    for cls in CLASSES:
        n = class_counts.get(cls, 0)
        bar = "#" * int(round(50.0 * n / total)) if total else ""
        print("  %*s %6d  %5.1f%%  %s" % (width, cls, n, 100.0 * n / total, bar))
    nonzero = total - class_counts.get("none", 0)
    print("\n  any non-'none' class: %d/%d = %.1f%%" %
          (nonzero, total, 100.0 * nonzero / total))

    print("\n=== how the class was reached ===")
    labels = {
        "explicit": "class named in title/hypothesis text",
        "generic":  "hardness asserted, class inferred as NP-hard (weakest)",
        "crypto":   "crypto assumption (method/family/text)",
        "weak+cat": "weak token promoted only because cs.CC is present",
        "none":     "no signal",
    }
    for k in ("explicit", "generic", "crypto", "weak+cat", "none"):
        print("  %6d  %-9s %s" % (prov_counts.get(k, 0), k, labels[k]))

    print("\n=== bucket x class ===")
    cols = [c for c in CLASSES if class_counts.get(c, 0)]
    head = "  %-17s" % "bucket" + "".join("%8s" % c[:7] for c in cols) + "%9s%9s" % ("any", "total")
    print(head)
    print("  " + "-" * (len(head) - 2))
    for b in BUCKETS:
        tot = bucket_counts.get(b, 0)
        row = [bucket_class.get((b, c), 0) for c in cols]
        any_h = tot - bucket_class.get((b, "none"), 0)
        print("  %-17s" % b + "".join("%8d" % v for v in row) +
              "%9d%9d" % (any_h, tot))
    print("  " + "-" * (len(head) - 2))
    tot_row = [class_counts.get(c, 0) for c in cols]
    print("  %-17s" % "ALL" + "".join("%8d" % v for v in tot_row) +
          "%9d%9d" % (nonzero, total))

    print("\n=== supply ceiling for a non-discrete quota ===")
    print("  papers per non-discrete bucket carrying a non-'none' class.")
    print("  These are OPTIMISTIC upper bounds and they are not a hardness")
    print("  guarantee -- see the module docstring.")
    ceiling = 0
    for b in NONDISCRETE_BUCKETS:
        tot = bucket_counts.get(b, 0)
        any_h = tot - bucket_class.get((b, "none"), 0)
        ceiling += any_h
        pct = (100.0 * any_h / tot) if tot else 0.0
        print("    %-17s %5d / %5d in bucket  (%.1f%%)" % (b, any_h, tot, pct))
    nd_total = sum(bucket_counts.get(b, 0) for b in NONDISCRETE_BUCKETS)
    print("    %-17s %5d / %5d" % ("TOTAL", ceiling, nd_total))


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--path", default=DEFAULT_PATH,
                    help="papers.jsonl to score (default: papers/papers.jsonl)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the distribution without writing anything")
    args = ap.parse_args()

    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        sys.exit("ERROR: no such file: %s" % path)

    class_counts, bucket_counts, prov_counts = Counter(), Counter(), Counter()
    bucket_class = Counter()
    out_lines = []
    total = 0

    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw, object_pairs_hook=OrderedDict)
            except ValueError as e:
                sys.exit("ERROR: line %d is not valid JSON: %s" % (lineno, e))
            total += 1

            evidence, provenance = score(rec)
            bucket = bucket_of(rec)

            class_counts[evidence["class"]] += 1
            bucket_counts[bucket] += 1
            bucket_class[(bucket, evidence["class"])] += 1
            prov_counts[provenance] += 1

            if args.dry_run:
                continue

            try:
                new = rewrite_line(raw, evidence)
            except ValueError as e:
                sys.exit("ERROR: line %d: %s" % (lineno, e))

            # Verify before accepting: parses, keeps every original field with an
            # identical value, and carries exactly the evidence we built, last.
            check = json.loads(new, object_pairs_hook=OrderedDict)
            before = OrderedDict((k, v) for k, v in rec.items() if k != FIELD)
            after = OrderedDict((k, v) for k, v in check.items() if k != FIELD)
            if list(before.items()) != list(after.items()):
                sys.exit("ERROR: line %d: rewrite changed existing fields" % lineno)
            if list(check.keys())[-1] != FIELD or check[FIELD] != evidence:
                sys.exit("ERROR: line %d: evidence not appended cleanly" % lineno)
            out_lines.append(new + "\n")

    if not args.dry_run:
        d = os.path.dirname(path) or "."
        mode = os.stat(path).st_mode & 0o777      # mkstemp gives 0600; keep the original
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".score_hardness.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                out.writelines(out_lines)
                out.flush()
                os.fsync(out.fileno())
            os.chmod(tmp, mode)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        print("wrote %s (%d lines)\n" % (path, len(out_lines)))
    else:
        print("DRY RUN -- %s not modified\n" % path)

    report(class_counts, bucket_class, bucket_counts, prov_counts, total)


if __name__ == "__main__":
    main()
