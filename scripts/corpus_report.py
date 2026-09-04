#!/usr/bin/env python3
"""Report the corpus by native domain, computational core and certificate form.

An aggregate count hides the failure this exists to catch: a benchmark can look
domain-diverse while every problem is internally graph search.

Three things this file gets right that the first version did not.

1. **Unknown is not a domain.**  The first version derived a core from the keys of
   the instance and, when no keyword matched, called the result ``"other"`` -- then
   reported ``other`` beside ``graph`` and ``exact_cover`` as if it were a measured
   non-discrete core.  It was 31.7% of the shipped corpus and it meant *we did not
   look*.  Inspecting those 13 rows found sets, points, clue grids and a Seidel
   row-matrix: mostly discrete, none of them measured.  A no-match now yields
   ``unknown``, is counted separately, and never dilutes the discrete share.  The
   discrete share is printed twice -- over all modules, and over the modules whose
   core is actually determined -- because those are a lower and an upper bound and
   the honest number lies between them.

2. **In-progress work is visible.**  The first version walked only ``status=="done"``
   claims, so 6 of the 7 modules then built under the NATIVE machinery -- the entire
   evidence base for whether the new rules changed anything -- were invisible.  Both
   statuses are walked and labelled; ``--done-only`` restores the old scope.

3. **Provenance is recorded per module.**  ``PROBLEM_PROFILE`` if the module declares
   one, else ``NATIVE``, else derived from the instance the solver is handed.  A
   quota that a *stated arXiv family label* can satisfy is worthless -- AUDIT.md
   records "geometric configurations" rows that ship a 720-vertex adjacency matrix --
   so the positive quotas below only count declared rows.

Two sibling contracts this file is bound by:

* ``scripts/submit.sh`` states that its graph word list is mirrored here and that
  "the gate and the report must never disagree".  ``GRAPH_PATTERNS`` below is that
  list verbatim, and like submit.sh the graph test reads ``render(inst)`` as well as
  the instance keys -- renaming ``edges`` to ``pairs`` was enough to evade a
  keys-only test.  Change one, change both.
* ``scripts/pick_paper.py`` no longer steers at all -- it draws UNIFORMLY AT
  RANDOM from the free pool, so that acceptance rate and family share become
  unbiased estimates of what these 12,167 papers actually yield.  That makes this
  gate the only remaining place corpus skew is caught, and raises the odds it
  fires: the prior predicts ~75% of the free pool is constraint search, so a
  uniform draw is expected to push MAX_DISCRETE_SEARCH_SHARE over its 0.50 line.
  When it does, the gate is working.  The fix at that point is a better POOL --
  a new retrieval pass over arXiv -- not a cleverer scheduler over this one, and
  not a looser threshold here.

Usage:

    python3 scripts/corpus_report.py                    # summary
    python3 scripts/corpus_report.py --rows             # one line per module
    python3 scripts/corpus_report.py --gate             # quotas, non-zero on violation
    python3 scripts/corpus_report.py --gate --advisory  # quotas, always exit 0
    python3 scripts/corpus_report.py --done-only        # exclude in-progress claims

``profile_for_module`` is imported by ``scripts/emit.sh``, which stamps the same
profile onto every emitted dataset record so the release can be sliced afterwards
instead of being split in advance.  Keep it importable: nothing at module scope may
print, touch the network, or change global interpreter state.
"""
import argparse
import glob
import importlib.util
import json
import os
import re
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# QUOTAS.  Every threshold is named here and nowhere else.
#
# WHAT --gate IS FOR.  These are release-manifest quotas: they describe the shape of
# a *curated set* of problems chosen for publication.  They are NOT a per-submission
# gate and scripts/submit.sh does not call them.  A single paper cannot be 15%
# analytic; asking one submission to satisfy a distributional constraint would
# reject every honest module.
#
# WHY --advisory EXISTS.  A quota that cannot fail is decoration, but a quota that
# cannot be satisfied deadlocks the project.  The binding constraint here is the
# source pool, not the builders: the dynamics_opt arXiv-category bucket holds ~524
# papers at ~25% acceptance, so it can never supply more than about
# POOL_CAP_DYNAMICS_OPT_ANALYTIC families in total -- and under the uniform draw
# nothing is steering toward it any more, so it will arrive slower than that.  At a 15% floor that caps
# a fully compliant release at roughly POOL_CAP_DYNAMICS_OPT_ANALYTIC /
# MIN_DYNAMICS_OPT_ANALYTIC_SHARE problems; past that the quota is arithmetically
# unsatisfiable no matter how well anyone works.  `--gate --advisory` reports the
# violations and exits 0 so the numbers stay in front of people without blocking a
# pipeline on a bound the pipeline cannot move.  Fix the pool, then tighten the gate.
# ---------------------------------------------------------------------------
MAX_SINGLE_CORE_SHARE = 0.25            # no single computational_core above this
MAX_DISCRETE_SEARCH_SHARE = 0.50        # graph+csp_sat+exact_cover+subset_sum+permutation
MIN_SYMBOLIC_CERT_SHARE = 0.15          # exact-symbolic or polynomial certificate forms
MIN_GEOMETRY_LINALG_SHARE = 0.15        # native geometry / linear-algebraic
MIN_DYNAMICS_OPT_ANALYTIC_SHARE = 0.15  # dynamics / optimization / certified analytic
MAX_SINGLE_INTUITION_SHARE = 0.30       # no single intuition_type above this

# Ceiling on how many dynamics/optimization/analytic families the 12,167-paper pool
# can ever yield: ~524 papers in the dynamics_opt arXiv-category bucket at the ~25%
# acceptance rate measured across the corpus so far.
POOL_CAP_DYNAMICS_OPT_ANALYTIC = 131

UNKNOWN = "unknown"            # we did not measure it
UNCLASSIFIED = "unclassified"  # free text that no taxonomy entry matched

# Cores that are discrete combinatorial search, per prompts/codex_task.md STEP 1.
# Mirrors DISCRETE_CORE in scripts/submit.sh.
DISCRETE_SEARCH_CORES = frozenset(
    {"graph", "csp_sat", "exact_cover", "subset_sum", "permutation"})
# Certificate forms that are exact-symbolic or polynomial rather than a tuple of
# small integers.  CERTIFICATE_LANGUAGE exists precisely because search_space came
# back an int 40/40 across the first shipped generators.
SYMBOLIC_CERT_FORMS = frozenset(
    {"exact_symbolic", "polynomial", "rational", "sos", "telescoping",
     "symbolic_integral", "algebraic_number", "matrix_certificate", "interval"})
GEOMETRY_LINALG_DOMAINS = frozenset({"geometry"})
GEOMETRY_LINALG_CORES = frozenset({"linear_algebra"})
DYNAMICS_OPT_ANALYTIC_DOMAINS = frozenset({"dynamics", "optimization", "analysis"})
DYNAMICS_OPT_ANALYTIC_CORES = frozenset({"interval_bound", "symbolic_integration"})

# A row counts toward a positive quota only if its labels were DECLARED by the
# module.  A derived label is an inference from instance keys or, worse, from the
# stated arXiv family -- and the family label is exactly what AUDIT.md caught lying
# on 11 of 40 rows.
DECLARED_PROVENANCE = frozenset({"profile", "native"})
# ...and only if the family is stated in the paper's own objects.  A discretised
# analogue of a dynamics paper is not dynamics coverage.
NATIVE_ESSENTIALITY = "native"

# ---------------------------------------------------------------------------
# Derivation heuristics.  These run ONLY when the module declares nothing.  They
# are deliberately one-sided: they can recognise a discrete core, and they refuse to
# guess a non-discrete one.  A wrong "unknown" costs a row in the denominator; a
# wrong "analysis" would manufacture exactly the diversity this file exists to
# measure.
# ---------------------------------------------------------------------------
# MIRRORED from scripts/submit.sh -- see the module docstring.  Read what the SOLVER
# is shown, not the dict key names.
#
# WORD-BOUNDED regexes, not substrings.  Reading render() costs false positives from
# prose, and plain substrings made that far worse than necessary: "graph" matched
# "cryptographic" and "degree of" matched "degree of the polynomial", both of which
# fired on 1912.02640, a finite-field module with no graph in it.  Bounding the words
# keeps the render() signal and drops that whole class.
GRAPH_PATTERNS = (
    r"\badjacen(?:t|cy)\b", r"\bedges?\b", r"\bneighbou?r",
    r"\bvert(?:ex|ices)\b", r"\bconflict", r"\bcliques?\b",
    r"\b(?:sub|multi|di|hyper)?graphs?\b", r"\binciden(?:t|ce)\b",
    r"\bdegree of (?:a |the )?(?:vertex|vertices|node|nodes)\b",
)
ASSIGN = ("clause", "assign", "variab", "literal", "colour", "color", "constraint")
COVER = ("lengths", "items", "weights", "subset", "blocks", "target", "capacit")
PERM = ("permutation", "ordering", "ranking", "bracket", "seeding")


def derive_core(inst, shown=""):
    """Core inferred from what the solver is actually handed, or UNKNOWN.

    Never returns a non-discrete core: nothing about a dict of instance keys is
    evidence that a family is analytic.  "other" is a legitimate *declared* value (a
    module saying "my core is none of the listed ones"); it is not a legitimate
    *derived* one, and conflating the two is the bug this function was rewritten to
    remove.
    """
    if not isinstance(inst, dict):
        return UNKNOWN
    keys = " ".join(k for k in inst if k != "answer").lower()
    both = keys + " " + (shown or "").lower()
    # Do NOT resolve by priority order.  Testing graph first pushed graph from 17 to
    # 25 of 42 (the graph test now also reads render(), and nearly every combinatorial
    # statement says "vertex" somewhere); testing the specific cores first pushed
    # csp_sat from 4 to 10.  Both are artefacts of the tie-break, not measurements.
    # Require an UNAMBIGUOUS structural match on the instance keys instead, and admit
    # ambiguity as ambiguity -- an over-attributed histogram is worse than a wide one,
    # because a quota is computed on top of it.
    # ASSIGN/COVER/PERM stay plain substrings -- they are stems ("variab", "capacit")
    # chosen to match key names, and key names are short and controlled.  The graph
    # test is regex because it also reads prose, where substrings misfire.
    def _hit(words, text, rx):
        return any(re.search(w, text) for w in words) if rx else any(w in text for w in words)
    hits = [name for name, words, rx in (("csp_sat", ASSIGN, False),
                                         ("exact_cover", COVER, False),
                                         ("permutation", PERM, False),
                                         ("graph", GRAPH_PATTERNS, True))
            if _hit(words, keys, rx)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        return UNKNOWN            # ambiguous: several cores match the same instance
    # Nothing in the instance keys.  The rendered statement is weaker evidence -- use
    # it only for graph, and only when the keys said nothing at all.
    if any(re.search(w, both) for w in GRAPH_PATTERNS):
        return "graph"
    return UNKNOWN


# Ordered: the more specific certificate languages are tested before the generic
# "has coefficients" one, so an SOS description is not filed as a polynomial.
CERT_PATTERNS = (
    ("sos", r"sum[\s-]*of[\s-]*squares|\bsos\b|positivstellensatz"),
    ("telescoping", r"telescop|gosper|zeilberger|wz\s+pair"),
    ("symbolic_integral", r"antideriv|indefinite\s+integral|risch|"
                          r"integration\s+in\s+closed\s+form"),
    ("algebraic_number", r"minimal\s+polynomial|isolating\s+interval|algebraic\s+number"),
    ("matrix_certificate", r"\b(gram|seidel|positive[\s-]*semidefinite|psd|cholesky|"
                           r"eigenvalue)\b"),
    ("interval", r"interval\s+(arithmetic|enclosure)|rigorous\s+enclosure|"
                 r"certified\s+bound"),
    ("polynomial", r"polynomial|monomial|nullstellensatz|coefficient\s+vector"),
    ("rational", r"\brational\b|\bfraction\b|numerator|denominator|\bover\s+Q\b"),
    ("integer_tuple", r"integer|tuple|index|indices|subset|permutation|bitmask|"
                      r"assignment|colou?r|vertex|vertices|bit\s*string"),
)

REGIME_PATTERNS = (
    ("continuous_analytic", r"\breal\s+(number|coordinate|vector|valued)|manifold|"
                            r"trajector|\bflow\b|\bODE\b|differential\s+equation|"
                            r"floating|\bR\^|ℝ"),
    ("real_algebraic", r"algebraic\s+number|minimal\s+polynomial|isolating\s+interval|"
                       r"real\s+algebraic"),
    ("rational_exact", r"\brational\b|\bover\s+Q\b|ℚ|fraction|exact\s+arithmetic"),
    ("finite_field", r"finite\s+field|\bGF\(|\bF_?\d+\b|\bmod(ulo)?\s+p\b"),
    ("integer_lattice", r"lattice|integer\s+(point|coordinate)|\bZ\^"),
    ("finite_discrete", r"graph|adjacen|hypergraph|set\s+system|permutation|clause|"
                        r"colou?r|bitmask|tournament|matroid|\bword\b|design|"
                        r"incidence|partition|sequence"),
)

# Free-text NATIVE["intuition"] normalised into a bounded vocabulary.  Without this
# the "no single intuition_type above 30%" quota is decoration: every module writes a
# different sentence, so no bucket ever holds more than one row and the quota cannot
# fail.  Order is priority order -- "constraint satisfaction under signal-switching
# symmetry" is a symmetry problem, not a propagation problem.
INTUITION_PATTERNS = (
    ("symmetry", r"symmetr|equivarian|orbit|group\s+action|relabel"),
    ("invariant", r"invariant|conserved|parity\s+argument|monovariant|"
                  r"potential\s+function|cancellation"),
    ("duality", r"\bdual|complement|polar\b|lp\s+relaxation|farkas|"
                r"certificate\s+of\s+infeasibility"),
    ("change_of_variables", r"change\s+of\s+variable|substitut|reparam|"
                            r"coordinate\s+change|transform\s+to"),
    ("ansatz", r"ansatz|guess\s+(a|the)\s+form|template|parametric\s+family"),
    ("extremal_bound", r"extremal|tight\s+bound|threshold|density\s+argument|"
                       r"counting\s+bound"),
    ("decomposition", r"decompos|factor|split\s+into|recursive|"
                      r"divide[\s-]and[\s-]conquer|block\s+structure"),
    ("constraint_propagation", r"propagat|constraint|unit\s+clause|consistency|forcing"),
    ("reduction_recognition", r"recogni[sz]e|reduction|encode|reduces?\s+to|"
                              r"is\s+really\s+a|hidden\s+\w+\s+instance"),
    ("search_pruning", r"prun|backtrack|branch\s+and\s+bound|search\s+order"),
)


def _match(patterns, text, default):
    if not text:
        return default
    t = str(text).lower()
    for label, rx in patterns:
        if re.search(rx, t, re.I):
            return label
    return default


def _cert_from_answer(ans):
    """Last-resort certificate form, from the shape of the planted answer.

    Deliberately cannot return a symbolic form.  A polynomial serialised as a string
    is indistinguishable here from a rendered word, so this returns "string" and the
    symbolic quota cannot be satisfied by accident.  Declare CERTIFICATE_LANGUAGE.
    """
    def _flat(x):
        if isinstance(x, (list, tuple)):
            for y in x:
                yield from _flat(y)
        else:
            yield x
    if isinstance(ans, bool):
        return "boolean"
    if isinstance(ans, int):
        return "integer"
    if isinstance(ans, float):
        return "numeric"
    if isinstance(ans, str):
        return "string"
    if isinstance(ans, dict):
        return "structured"
    if isinstance(ans, (list, tuple)):
        vals = list(_flat(ans))
        if vals and all(isinstance(v, int) and not isinstance(v, bool) for v in vals):
            return "integer_tuple"
        if any(isinstance(v, float) for v in vals):
            return "numeric_tuple"
        return "structured"
    return UNKNOWN


def _regime_from_instance(inst):
    if not isinstance(inst, dict):
        return UNKNOWN
    def _flat(x):
        if isinstance(x, dict):
            for v in x.values():
                yield from _flat(v)
        elif isinstance(x, (list, tuple, set)):
            for v in x:
                yield from _flat(v)
        else:
            yield x
    vals = list(_flat({k: v for k, v in inst.items() if k != "answer"}))
    # One-sided, for the same reason derive_core is: a derived regime may recognise
    # a discrete instance but must never CLAIM a continuous one.  The first version
    # returned "continuous_analytic" whenever any float appeared anywhere, and
    # results/2001.09362 -- a clue-grid puzzle over small integers -- tripped it on a
    # `clue_density: 0.4` tuning knob.  A float-valued parameter is not a continuous
    # object regime; floats in the data might be, and the module should say so in
    # PROBLEM_PROFILE["object_regime"] rather than have it guessed from a dict.
    if vals and all(isinstance(v, (int, str, bool)) or v is None for v in vals):
        return "finite_discrete"
    return UNKNOWN


def _reduction_text(reduction):
    """NATIVE['reduction'] is a string; PROBLEM_PROFILE['reduction'] is a dict with
    a 'citation' (scripts/submit.sh names that path).  Accept either."""
    if reduction in (None, "", False, {}, []):
        return ""
    if isinstance(reduction, dict):
        return " ".join(str(reduction.get(k, ""))
                        for k in ("citation", "section", "theorem", "text", "why"))
    return str(reduction)


def _reduction_kind(reduction):
    """none | paper_licensed | convenience.

    HEURISTIC, and a reviewer should spot-check it: "the text names a section" is the
    only mechanical signal available for whether the source paper actually licenses
    the surrogate.  A reduction can cite Section 3.1 and then admit in the next
    clause that it ships something else -- results/2604.25734 does exactly that, and
    this classifier calls it paper_licensed and is wrong.
    """
    text = _reduction_text(reduction)
    if not text.strip():
        return "none"
    if re.search(r"(section|theorem|lemma|proposition|corollary|chapter|§)\s*\d",
                 text, re.I):
        return "paper_licensed"
    return "convenience"


def profile_for_module(m, inst=None, family=None):
    """The full profile for one generator module.

    Precedence: PROBLEM_PROFILE, then NATIVE, then derived from `inst`.
    `core_provenance` records which of the three answered.  Returns every key
    scripts/emit.sh stamps onto a dataset record, plus `intuition_type`.

    `family` is the stated arXiv family from papers/papers.jsonl.  It is used only as
    a last-resort `native_domain` and is never trusted by a quota -- it is a triage
    label, and AUDIT.md documents it disagreeing with the shipped core on 11 of 40
    rows.

    NOTE ON `track`.  prompts/codex_task.md now requires a module-level
    ``TRACK = "A" | "B"`` (structural hardness vs no-tool compression).  That is the
    distinction carried here, because the native/discretised-analogue split is
    already carried -- with more resolution -- by `domain_essentiality` and
    `reduction_kind`, and duplicating it would waste the column.  No module declares
    TRACK yet, so today the field reads "unknown" everywhere, which is the true
    measurement: the prompt itself says every family shipped so far is an unlabelled
    Track A claim.
    """
    prof = getattr(m, "PROBLEM_PROFILE", None)
    nat = getattr(m, "NATIVE", None)
    cl = getattr(m, "CERTIFICATE_LANGUAGE", None)
    prof = prof if isinstance(prof, dict) else None
    nat = nat if isinstance(nat, dict) else None
    cl = cl if isinstance(cl, dict) else None

    provenance = "profile" if prof else ("native" if nat else "derived")

    def p(*names):
        for n in names:
            if prof and prof.get(n) not in (None, ""):
                return prof[n]
        return None

    # --- native_domain ----------------------------------------------------
    domain = p("native_domain", "domain")
    if domain is None and nat:
        domain = nat.get("domain")
    if domain is None:
        domain = family or UNKNOWN

    # --- computational_core -----------------------------------------------
    core = p("computational_core", "core")
    if core is None and nat:
        core = nat.get("core")
    if core is None:
        shown = ""
        if inst is not None:
            try:
                shown = m.render(inst)
            except Exception:                        # noqa: BLE001
                shown = ""
        core = derive_core(inst, shown)
    core = core or UNKNOWN

    # --- certificate_form --------------------------------------------------
    cert = p("certificate_form")
    if cert is None and cl:
        blob = " ".join(str(cl.get(k, "")) for k in ("description", "form", "language"))
        bounds = cl.get("bounds")
        if isinstance(bounds, dict):
            blob += " " + " ".join(map(str, bounds.keys()))
        cert = _match(CERT_PATTERNS, blob, None)
    if cert is None and isinstance(inst, dict):
        cert = _cert_from_answer(inst.get("answer"))
    cert = cert or UNKNOWN

    # --- object_regime -----------------------------------------------------
    regime = p("object_regime")
    if regime is None and nat:
        regime = _match(REGIME_PATTERNS,
                        " ; ".join(map(str, nat.get("objects") or [])), None)
    if regime is None and cl:
        regime = _match(REGIME_PATTERNS, str(cl.get("description", "")), None)
    if regime is None:
        regime = _regime_from_instance(inst)
    regime = regime or UNKNOWN

    # --- reduction / essentiality -------------------------------------------
    reduction = p("reduction")
    if reduction is None and nat:
        reduction = nat.get("reduction")
    kind = p("reduction_kind")
    if kind is None:
        kind = _reduction_kind(reduction) if (prof or nat) else UNKNOWN

    ess = p("domain_essentiality")
    if ess is None:
        if not (prof or nat):
            ess = UNKNOWN
        elif kind == "none":
            ess = "native"
        elif kind == "paper_licensed":
            ess = "licensed_reduction"
        else:
            ess = "discretised_analogue"

    # --- track (hardness track A/B; see the docstring) ----------------------
    track = p("track", "hardness_track")
    if track is None:
        track = getattr(m, "TRACK", None)
    track = str(track).strip().upper() if track else UNKNOWN
    if track not in ("A", "B"):
        track = UNKNOWN

    # --- intuition ---------------------------------------------------------
    intuition_raw = p("intuition_type", "intuition")
    if intuition_raw is None and nat:
        intuition_raw = nat.get("intuition")
    intuition = _match(INTUITION_PATTERNS, intuition_raw, UNCLASSIFIED)

    return {
        "native_domain": domain,
        "computational_core": core,
        "certificate_form": cert,
        "object_regime": regime,
        "domain_essentiality": ess,
        "reduction_kind": kind,
        "track": track,
        "core_provenance": provenance,
        "intuition_type": intuition,
        "intuition_raw": intuition_raw or "",
    }


# ---------------------------------------------------------------------------
# Corpus walk
# ---------------------------------------------------------------------------
_PAPERS = None


def _papers():
    global _PAPERS
    if _PAPERS is None:
        _PAPERS = {}
        # Per-line, not per-file: papers.jsonl is written by other tooling while this
        # runs, and one half-written line must not silently truncate the index --
        # a missing family reads as native_domain="unknown", which looks like a
        # measurement.
        try:
            fh = open(os.path.join(REPO, "papers", "papers.jsonl"))
        except OSError:
            return _PAPERS
        with fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if "arxiv_id" in r:
                    _PAPERS[r["arxiv_id"]] = r
    return _PAPERS


def family_for(pid):
    return _papers().get(pid, {}).get("family")


def load_module(path):
    name = "gv_" + re.sub(r"\W", "_", os.path.basename(path))
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def shipping_instance(m):
    D = getattr(m, "DIFFICULTY", {}) or {}
    name = getattr(m, "SHIPPING_DIFFICULTY", None) or next(iter(D), None)
    params = D.get(name, {}) if name else {}
    return m.make_instance(seed=1, **params)


def collect(statuses=("done", "in_progress")):
    rows = []
    for f in sorted(glob.glob(os.path.join(REPO, "claims", "*.json"))):
        try:
            d = json.load(open(f))
        except (OSError, ValueError):
            continue
        st = d.get("status")
        if st not in statuses:
            continue
        pid = d.get("paper") or os.path.basename(f)[:-5]
        mods = sorted(glob.glob(os.path.join(REPO, "results", pid, "gen_*.py")))
        if not mods:
            continue
        inst, err, m = None, None, None
        try:
            m = load_module(mods[0])
            inst = shipping_instance(m)
        except Exception as e:                       # noqa: BLE001 - report, never abort
            m, err = None, f"{type(e).__name__}: {e}"[:70]
        if m is None:
            prof = {k: UNKNOWN for k in
                    ("native_domain", "computational_core", "certificate_form",
                     "object_regime", "domain_essentiality", "reduction_kind",
                     "track", "core_provenance")}
            prof["core_provenance"] = "load-failed"
            prof["intuition_type"] = UNCLASSIFIED
            prof["intuition_raw"] = ""
        else:
            prof = profile_for_module(m, inst, family=family_for(pid))
        # measured certificate shape -- what the module actually returns, which
        # can differ from the CERTIFICATE_LANGUAGE it declares
        try:
            prof["answer_shape"] = answer_shape(inst["answer"]) if inst is not None else None
        except Exception:                            # noqa: BLE001
            prof["answer_shape"] = None
        prof.update(paper=pid, status=st, error=err)
        rows.append(prof)
    return rows


def _hist(rows, key, title, out):
    tot = len(rows) or 1
    out.append(f"=== {title} ===")
    for v, n in Counter(r[key] for r in rows).most_common():
        bar = "#" * int(36 * n / tot)
        out.append(f"  {n:3} ({100*n/tot:5.1f}%)  {str(v):<24} {bar}")
    out.append("")


# ---------------------------------------------------------------------------
# Quotas
# ---------------------------------------------------------------------------
def _declared(r):
    return r["core_provenance"] in DECLARED_PROVENANCE


def evaluate_quotas(rows):
    """[(label, measured_text, target_text, passed, note)] -- one entry per quota."""
    tot = len(rows) or 1
    cores = Counter(r["computational_core"] for r in rows)
    quotas = []

    # 1. no single computational_core above MAX_SINGLE_CORE_SHARE.
    # UNKNOWN is a bucket here on purpose: a corpus whose largest bucket is "we did
    # not measure it" has not demonstrated diversity, it has demonstrated that the
    # question was never asked.  It stays satisfiable -- declaring PROBLEM_PROFILE or
    # NATIVE moves a row out of it, and submit.sh already requires NATIVE.
    top_core, top_n = (cores.most_common(1) or [(UNKNOWN, 0)])[0]
    quotas.append((
        "no single computational_core above",
        f"{100*top_n/tot:5.1f}%  ({top_core}, {top_n}/{tot})",
        f"<= {100*MAX_SINGLE_CORE_SHARE:.0f}%",
        top_n / tot <= MAX_SINGLE_CORE_SHARE,
        "unknown counts as a bucket",
    ))

    # 2. combined discrete search below MAX_DISCRETE_SEARCH_SHARE.
    disc = sum(n for c, n in cores.items() if c in DISCRETE_SEARCH_CORES)
    quotas.append((
        "combined discrete-search core below",
        f"{100*disc/tot:5.1f}%  ({disc}/{tot})",
        f"<  {100*MAX_DISCRETE_SEARCH_SHARE:.0f}%",
        disc / tot < MAX_DISCRETE_SEARCH_SHARE,
        "graph+csp_sat+exact_cover+subset_sum+permutation",
    ))

    # 3. exact-symbolic or polynomial certificate forms.
    sym = sum(1 for r in rows if r["certificate_form"] in SYMBOLIC_CERT_FORMS)
    quotas.append((
        "exact_symbolic/polynomial certificates",
        f"{100*sym/tot:5.1f}%  ({sym}/{tot})",
        f">= {100*MIN_SYMBOLIC_CERT_SHARE:.0f}%",
        sym / tot >= MIN_SYMBOLIC_CERT_SHARE,
        "read from CERTIFICATE_LANGUAGE",
    ))

    # 4. native geometry / linear-algebraic.  Declared and native only: the stated
    # family "geometric configurations" shipped as a plain graph twice.
    geo = sum(1 for r in rows if _declared(r)
              and r["domain_essentiality"] == NATIVE_ESSENTIALITY
              and (r["native_domain"] in GEOMETRY_LINALG_DOMAINS
                   or r["computational_core"] in GEOMETRY_LINALG_CORES))
    quotas.append((
        "native geometry / linear-algebraic",
        f"{100*geo/tot:5.1f}%  ({geo}/{tot})",
        f">= {100*MIN_GEOMETRY_LINALG_SHARE:.0f}%",
        geo / tot >= MIN_GEOMETRY_LINALG_SHARE,
        "declared + essentiality=native only",
    ))

    # 5. dynamics / optimization / certified analytic, same rule.
    dyn = sum(1 for r in rows if _declared(r)
              and r["domain_essentiality"] == NATIVE_ESSENTIALITY
              and (r["native_domain"] in DYNAMICS_OPT_ANALYTIC_DOMAINS
                   or r["computational_core"] in DYNAMICS_OPT_ANALYTIC_CORES))
    quotas.append((
        "dynamics / optimization / analytic",
        f"{100*dyn/tot:5.1f}%  ({dyn}/{tot})",
        f">= {100*MIN_DYNAMICS_OPT_ANALYTIC_SHARE:.0f}%",
        dyn / tot >= MIN_DYNAMICS_OPT_ANALYTIC_SHARE,
        f"pool caps this at ~{POOL_CAP_DYNAMICS_OPT_ANALYTIC} families ever",
    ))

    # 6. no single intuition_type above MAX_SINGLE_INTUITION_SHARE.
    ints = Counter(r["intuition_type"] for r in rows)
    top_int, top_in = (ints.most_common(1) or [(UNCLASSIFIED, 0)])[0]
    quotas.append((
        "no single intuition_type above",
        f"{100*top_in/tot:5.1f}%  ({top_int}, {top_in}/{tot})",
        f"<= {100*MAX_SINGLE_INTUITION_SHARE:.0f}%",
        top_in / tot <= MAX_SINGLE_INTUITION_SHARE,
        "unclassified counts as a bucket",
    ))
    return quotas


def print_gate(rows, advisory, out):
    n_done = sum(1 for r in rows if r["status"] == "done")
    n_prog = len(rows) - n_done
    out.append("=== release quotas ===")
    out.append(f"  measured over {len(rows)} module(s): {n_done} done + {n_prog} in progress")
    out.append("  scope: a CURATED RELEASE MANIFEST.  These are distributional quotas; they")
    out.append("         are NOT a per-submission gate -- no single paper can be 15%")
    out.append("         analytic.  scripts/submit.sh does not and must not call this.")
    out.append("")
    quotas = evaluate_quotas(rows)
    width = max(len(q[0]) for q in quotas)
    for label, measured, target, ok, note in quotas:
        out.append(f"  [{'PASS' if ok else 'FAIL'}] {label:<{width}}  "
                   f"measured {measured:<26} target {target:<7}  ({note})")
    failed = [q[0] for q in quotas if not q[3]]
    out.append("")
    deadlock = int(POOL_CAP_DYNAMICS_OPT_ANALYTIC / MIN_DYNAMICS_OPT_ANALYTIC_SHARE)
    out.append(f"  note: the pool holds ~{POOL_CAP_DYNAMICS_OPT_ANALYTIC} papers that could "
               f"ever yield a dynamics/optimization/analytic")
    out.append(f"        family, so a release above ~{deadlock} problems cannot satisfy the "
               f"{100*MIN_DYNAMICS_OPT_ANALYTIC_SHARE:.0f}% floor at all.")
    out.append("        That is a pool defect, not a builder defect -- which is why --advisory")
    out.append("        exists.  Retrieve more non-discrete papers before tightening this.")
    out.append("")
    if not failed:
        out.append(f"  {len(quotas)}/{len(quotas)} quotas PASS")
        return 0
    out.append(f"  {len(failed)}/{len(quotas)} quotas FAIL: " + "; ".join(failed))
    if advisory:
        out.append("  --advisory: reporting only, exiting 0.")
        return 0
    return 1


# ---------------------------------------------------------------------------
# --------------------------------------------------------------------------
# MEASURED SOLVER FAMILY.  audit/attack_families.json records what actually
# cracked each family, which is a more honest label than anything the builder
# declares: 2411.04916 calls itself geometric (kissing numbers in 17-21
# dimensions) and is solved by constraint search.  Under a tools-free eval a
# cheap mechanical route is not a defect -- it is aging risk plus a statement
# about which SKILL the question exercises.
def load_measured(root="."):
    try:
        with open(os.path.join(root, "audit", "attack_families.json")) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def report_solver_families(out, root="."):
    data = load_measured(root)
    meas = data.get("measured", {})
    if not meas:
        return
    counts, secs = {}, {}
    for pid, m in meas.items():
        f = m.get("family", "?")
        counts[f] = counts.get(f, 0) + 1
        if isinstance(m.get("seconds"), (int, float)):
            secs.setdefault(f, []).append(m["seconds"])
    tot = sum(counts.values()) or 1
    out.append("")
    out.append("=== MEASURED SOLVER FAMILY (what actually cracks it) ===")
    out.append(f"  {tot} shipped families have been attacked; the rest are UNMEASURED,")
    out.append("  which is absence of evidence, not evidence of hardness.")
    out.append("")
    for f, n in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "#" * int(40 * n / tot)
        med = ""
        if secs.get(f):
            v = sorted(secs[f]); med = f"  median {v[len(v)//2]:.3f}s"
        out.append(f"   {n:3} ({100*n/tot:5.1f}%)  {f:28} {bar}{med}")
    top = max(counts.values()) / tot
    two = sum(sorted(counts.values(), reverse=True)[:2]) / tot
    out.append("")
    out.append(f"  largest single skill: {100*top:.0f}%   top two combined: {100*two:.0f}%")
    out.append("  A benchmark whose questions share one solver family is one question")
    out.append("  restated N times, however varied the source papers look.")


def answer_shape(a, depth=0):
    """Structural shape of a certificate, e.g. list[int] or dict{x:list[int]}.

    Measured rather than declared. CERTIFICATE_LANGUAGE says what a builder
    intended; this says what the module actually returns, and the two can differ.
    """
    if isinstance(a, bool): return "bool"
    if isinstance(a, int): return "int"
    if isinstance(a, float): return "float"
    if isinstance(a, str): return "str"
    if isinstance(a, dict):
        if depth > 1: return "dict{...}"
        return "dict{" + ",".join(f"{k}:{answer_shape(v, depth+1)}"
                                  for k, v in list(a.items())[:3]) + "}"
    if isinstance(a, (list, tuple)):
        if not a: return "list[]"
        return "list[" + "|".join(sorted({answer_shape(x, depth+1) for x in a[:6]})) + "]"
    return type(a).__name__


def report_answer_shapes(out, rows):
    """Empirical certificate diversity.

    82% of the first 55 modules answered with plain integers or lists of integers
    and search_space() returned an int 55/55 -- not because richer certificates are
    forbidden, but because every gate is cheapest to satisfy with a tuple of small
    ints. This section exists so that collapse is visible instead of implicit.
    """
    shapes = Counter()
    for r in rows:
        sh = r.get("answer_shape")
        if sh: shapes[sh] += 1
    if not shapes: return
    tot = sum(shapes.values())
    out.append("")
    out.append("=== ANSWER SHAPE (measured, not declared) ===")
    for sh, n in shapes.most_common(12):
        out.append(f"   {n:3} ({100*n/tot:5.1f}%)  {sh[:52]:52} {'#'*int(30*n/tot)}")
    flat = sum(n for sh, n in shapes.items()
               if sh in ("int", "list[int]", "list[list[int]]"))
    out.append("")
    out.append(f"  plain integers / lists of integers: {flat}/{tot} = {100*flat/tot:.0f}%")
    out.append("  A corpus whose every answer is a tuple of small integers tests one")
    out.append("  output skill. See prompts/codex_task.md for the certificate menu.")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Report the corpus by native domain and computational core.")
    ap.add_argument("--rows", action="store_true", help="one line per module")
    ap.add_argument("--gate", action="store_true",
                    help="check release quotas; exit non-zero on violation")
    ap.add_argument("--advisory", action="store_true",
                    help="with --gate: report violations but always exit 0")
    ap.add_argument("--done-only", action="store_true",
                    help="exclude in-progress claims (default: include, labelled)")
    args = ap.parse_args(argv)
    if args.advisory and not args.gate:
        ap.error("--advisory only means something together with --gate")

    import warnings
    warnings.filterwarnings("ignore")

    statuses = ("done",) if args.done_only else ("done", "in_progress")
    rows = collect(statuses)
    out = []

    n_done = sum(1 for r in rows if r["status"] == "done")
    n_prog = len(rows) - n_done
    n_fail = sum(1 for r in rows if r["core_provenance"] == "load-failed")
    out.append(f"modules with a generator: {len(rows)}  "
               f"({n_done} done, {n_prog} in progress"
               + (f", {n_fail} load-failed" if n_fail else "") + ")")
    out.append("")

    if args.gate:
        code = print_gate(rows, args.advisory, out)
        print("\n".join(out))
        return code

    tot = len(rows) or 1
    cores = Counter(r["computational_core"] for r in rows)
    _hist(rows, "computational_core", "computational core", out)

    unk = cores.get(UNKNOWN, 0)
    det = len(rows) - unk
    disc = sum(n for c, n in cores.items() if c in DISCRETE_SEARCH_CORES)
    out.append("  'unknown' means the module declared no PROBLEM_PROFILE/NATIVE and the")
    out.append("  instance matched no keyword.  It is NOT a measured non-discrete core --")
    out.append("  the old report called this bucket 'other' and counted 31.7% of the corpus")
    out.append("  as non-discrete on the strength of it.")
    out.append(f"  core determined: {det}/{len(rows)} ({100*det/tot:.1f}%);  "
               f"unknown: {unk}/{len(rows)} ({100*unk/tot:.1f}%)")
    out.append(f"  discrete-search core: {disc}/{len(rows)} = {100*disc/tot:.1f}% of ALL "
               f"modules (lower bound; unknowns counted as non-discrete)")
    out.append(f"                        {disc}/{det} = "
               + (f"{100*disc/det:.1f}%" if det else "n/a")
               + " of modules whose core is DETERMINED (upper bound)")

    report_solver_families(out)
    report_answer_shapes(out, rows)
    out.append("")

    _hist(rows, "native_domain", "native domain", out)
    _hist(rows, "certificate_form", "certificate form", out)
    _hist(rows, "object_regime", "object regime", out)
    _hist(rows, "domain_essentiality", "domain essentiality", out)
    _hist(rows, "track", "hardness track (TRACK: A structural / B no-tool)", out)
    _hist(rows, "intuition_type", "intuition type", out)
    _hist(rows, "core_provenance", "core provenance", out)
    out.append("  legend: profile = module declares PROBLEM_PROFILE; native = declares")
    out.append("          NATIVE; derived = inferred from the shipped instance and its")
    out.append("          render() text (and, for native_domain only, from the stated arXiv")
    out.append("          family, which AUDIT.md found disagreeing with the real core on")
    out.append("          11/40 rows).  Under 'native', certificate_form and object_regime")
    out.append("          are still derived -- NATIVE does not carry them.")
    out.append("")

    _hist(rows, "status", "claim status", out)

    mism = [r for r in rows if r["core_provenance"] == "derived"
            and r["computational_core"] == "graph"
            and "graph" not in str(r["native_domain"])]
    if mism:
        out.append(f"=== stated family disagrees with derived core ({len(mism)}) ===")
        for r in mism:
            out.append(f"  {r['paper']:12} family={r['native_domain']!r} -> core=graph")
        out.append("")

    bad = [r for r in rows if r["error"]]
    if bad:
        out.append(f"=== modules that would not load ({len(bad)}) ===")
        for r in bad:
            out.append(f"  {r['paper']:12} [{r['status']}] {r['error']}")
        out.append("")

    if args.rows:
        out.append("=== rows ===")
        out.append(f"  {'paper':<12} {'status':<12} {'domain':<26} {'core':<13} "
                   f"{'cert':<14} {'regime':<20} {'essentiality':<20} {'track':<8} "
                   f"{'prov':<11} intuition")
        for r in sorted(rows, key=lambda r: r["paper"]):
            out.append(f"  {r['paper']:<12} {r['status']:<12} "
                       f"{str(r['native_domain'])[:25]:<26} "
                       f"{r['computational_core']:<13} {r['certificate_form']:<14} "
                       f"{r['object_regime']:<20} {r['domain_essentiality']:<20} "
                       f"{r['track']:<8} {r['core_provenance']:<11} {r['intuition_type']}")
        out.append("")

    out.append("run `--gate` for the release quotas (`--gate --advisory` to not fail).")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
