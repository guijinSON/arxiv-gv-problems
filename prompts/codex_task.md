# TASK: turn this paper into a self-contained, verified problem generator

You are given one arXiv paper. Produce a single Python module that manufactures an
unlimited supply of instances of ONE problem family from that paper, together with
everything needed to pose the problem to a solver and grade the answer
automatically.

A family is only acceptable if all three hold:

- **G — generatable.** You can build an instance *and know a certificate for it by
  construction*. Four routes count:
  - **inverse generation** — sample the answer first and build the problem around it;
  - **theorem-backed construction** — a theorem in the paper guarantees the object you
    just assembled has the property, and the certificate is what its proof produces;
  - **transformation of a known instance** — apply a structure-preserving map to an
    instance whose certificate you hold, and carry the certificate through the map;
  - **composition of identities** — build the instance from pieces whose certificates
    compose: a product of telescoping terms, a sum of squares assembled from known
    squares, a substitution chain with a known inverse.

  What is forbidden is shipping a family whose answer you obtained by *solving* the
  instance. If you had to search for it, so will your generator, and the family will
  not scale.
- **H — hard.** Hard in the sense your `TRACK` declares — see **TWO TRACKS** below.
  Under either track the answer space must be far too large to guess.
- **V — verifiable.** A candidate answer is checked cheaply and exactly: substitute,
  expand, recompute, compare.

## The witness rule

The answer must be a **witness**: a concrete object whose validity is decided by
inspecting only the object and the instance. No search, no oracle, no appeal to a
theorem the checker cannot execute.

That is a statement about the *checker*, not about the answer's type. So certified
negatives, certified optima and numeric answers **are admissible** — provided the
certificate is itself such an object:

| the claim | the certificate that makes it admissible |
|---|---|
| no solution exists | a Farkas certificate, a Nullstellensatz or Positivstellensatz certificate, a bounded-length refutation |
| this is the optimum | a primal–dual pair with complementary slackness, or a feasible point plus a dual bound that meets it |
| this real number | an algebraic number as (minimal polynomial, isolating interval with rational endpoints) |
| this quantity lies here | a rigorous enclosure with **exact rational** endpoints |
| this system is stable | a Lyapunov or barrier certificate with rational coefficients |

**But — the discriminating test, and it is the one that matters:**

> If the certificate is simply the output of a polynomial-time algorithm run on the
> instance, you have not found a way past H. You have found the reason the family
> fails it.

An LP dual, a Gram matrix read off by coefficient matching, an SOS certificate that an
SDP returns, a Lyapunov function that a linear solve produces, a root isolation — each
is a perfectly good *witness* and a disqualifying *family*. The witness rule and the
hardness rule are separate gates, and a certificate can clear the first while failing
the second.

Ask this at **STEP 0, before you write any code.** It is one question — *what algorithm
produces this certificate, and what does it cost?* — and the paper's own theorem
statements usually answer it in a line.

The five algebraic papers rejected most recently were all rejected on exactly this
point, and every one of them cost a full builder run first:

| paper | what produces the certificate |
|---|---|
| `2605.28674` | disjunctive SOS: the paper reduces certificate search to an SDP, with SOCP and LP refinements |
| `2504.18110` | the Gram matrix and the switching root are written out explicitly in Section 2 |
| `2211.12582` | a necessary-and-sufficient spectral characterisation; the dimension is read off an eigenvalue multiplicity |
| `1910.13133` | the witness is given by an explicit matrix formula |
| `2512.19313` | the witness is a direct evaluation of a displayed trinomial construction — found after reading all 31 pages and the LaTeX source |

One sentence applied at triage would have stopped all five. Instead each was claimed,
read end to end, and rejected: five builder runs, roughly 90 minutes and 1.5M tokens, to
rediscover a fact stated in each paper's own main theorem.

---

## TWO TRACKS — say which hardness you are claiming

Declare `TRACK = "A"` or `TRACK = "B"` at module level. Required.

**Track A — structural hardness.** No known efficient general method for the
distribution you generate. Note *distribution*, not *worst case*: worst-case NP-hardness
is a different claim and does not imply this one. `2503.01929` sat exactly inside the
strongly NP-hard 3-PARTITION band and fell to Algorithm X in under five seconds, because
random instances in that band are not hard. `PROBLEM_PROFILE["hardness_basis"]` must
name the theorem *and* the parameter regime; G5's baseline cost is the evidence.

**Track B — no-tool compression.** An efficient algorithm exists, and you say so. The
claim is narrower and different: the evaluated model has no sandbox, no CAS and no
solver, so it must find and execute a compact route unaided. The difficulty is the gap
between the mechanical route (10⁶ operations — fine for a solver, impossible by hand)
and the compact one (a change of variables, an invariant, a symmetry — a dozen
operations, if you see it).

**Track B families must be honest about the algorithm that exists.** In
`hardness_basis`, name it, give its complexity, and give its measured cost at the
shipping preset. A Track B family that hides the algorithm is a Track A claim, and a
false one.

The track also changes what G6 means:

- **Track A** — every entry in `attacks` must have `successes == 0`, the domain-standard
  algorithm included. Unchanged from today.
- **Track B** — the domain-standard algorithm is *expected* to succeed. Report it under
  a separate key `reference_algorithm` (name, complexity, wall-clock, operation count),
  **not** inside `attacks`; that number is your `hardness_basis`, not a failure.
  `attacks` still needs its ≥4 failing entries, and for Track B the fourth is an attack a
  solver could actually run *in context, without tools* — the by-hand heuristic, the
  greedy route, the obvious ansatz. If you cannot find a fourth in-context attack that
  fails, the family is guessable by hand and you should reject it.

Why the label is mandatory: without it the project drifts silently between
complexity-theoretic hardness and practical model difficulty. Both are defensible
benchmarks. They are not the same benchmark, and a corpus that mixes them unlabelled can
support neither claim. Every family shipped so far is an unlabelled Track A claim, and
`AUDIT.md` records five where that claim was simply false.

---

## STEP 0 — read the actual paper, not just the abstract

**Do this first. Do not skip it.** Fetch and read the full text
(`https://arxiv.org/abs/<id>`, or the LaTeX source at
`https://arxiv.org/e-print/<id>`).

The abstract will not tell you the four things that decide whether your generator
works:

1. **The exact definition.** Informal phrasings hide precise constraints. "Balanced"
   turned out to mean *exactly f from each colour class* — a completely different
   problem from what the abstract suggested.
2. **Which parameter regime is hard.** Papers prove hardness for specific settings.
   Find the theorem and use *its* parameters.
3. **What makes it EASY.** This is the one that kills generators. Look specifically
   for: polynomial-time algorithms for special cases, **FPT algorithms** (an FPT
   algorithm parameterised by *k* means instances with small *k* are tractable — so
   *k* must grow with instance size), approximation schemes, and any explicit
   construction that solves the search directly.
4. **What produces the certificate.** Find the theorem that hands you the witness and
   ask what algorithm it is. If the answer is "an SDP", "a linear solve", "a spectral
   characterisation", "an explicit formula" or "a classification table", then **the
   family fails H on Track A** — not the witness rule, and *not necessarily at all*.
   The certificate is a perfectly good witness; what it is not is hard to obtain on
   Track A. Those are separate gates (see the discriminating test above).

   **This is the single most expensive mistake made on this project so far, so do it
   in this order.** An independent audit re-read 12 rejected papers against their
   actual arXiv text: **7 of the 12 should have been built.** Every miss came from
   stopping at "a method exists" without asking the next question. One rejected paper
   was dismissed because "Theorem 1 gives u by a short linear formula" — while the
   paper's own mechanical route was enumerating **16,689,170 dual-lattice vectors,
   788 seconds and 4.6 GB in Magma**. A fifteen-step shortcut against 16.7 million
   enumerations is not a non-family. It is the definition of Track B.

   **FIRST ask whether it is Track B. Only then consider rejecting.**

   Write down two numbers before you decide:

   | | what to record |
   |---|---|
   | **mechanical cost** | operations the standard method needs at your shipping size — the paper often states it, or you can measure it |
   | **compact route** | steps a solver needs who sees the structure: the invariant, symmetry, or change of variable |

   - **`TRACK = "B"`** when the mechanical cost is out of reach by hand and the compact
     route is short. Name the algorithm and both numbers in `hardness_basis`. An SDP
     over a 40×40 Gram matrix is not something a model does in its head; a 2×2 linear
     solve is.
   - **Reject** only when the compact route is *no shorter* than the mechanical one —
     that is, when there is nothing to see, so the question tests nothing. Say both
     numbers in `REJECTED.md` and show they are comparable. "An algorithm exists" on
     its own is **not a sufficient reason to reject** and will be sent back.

   What is never acceptable is declaring Track A while knowing the algorithm exists.

### Build in the paper's own objects first

Before you reduce anything, write down the problem **in the objects the theorem and
proof actually use** — vectors, Gram matrices, polynomials over ℚ or ℚ(i),
coordinates, functions, trajectories, group elements. Ask whether a finite exact
certificate exists *for that* object: a Gram or Seidel matrix, a rational SOS
decomposition, a minimal polynomial with an isolating interval, a telescoping
certificate, an antiderivative, a coordinate/sign construction checked by exact
inner products, a dual witness. Verification stays exact — the *object* may be
continuous even when its *certificate* is a finite symbolic thing.

Only after that may you consider a discrete reduction.

**Do not replace a problem over ℝ, ℂ, manifolds, functions or trajectories with a
graph, SAT/CSP, finite field or integer-coordinate surrogate unless that reduction
is central to the source paper.** If you do reduce, name the theorem or section that
licenses it. If you reduce for convenience, the result is a *discretised analogue*:
declare `reduction_kind="convenience"` in `PROBLEM_PROFILE` (and mirror the citation
text in `NATIVE["reduction"]`), and do not present it as coverage of the paper's native
domain. Such a family is archived, never counted in the native release — see
PROBLEM_PROFILE in STEP 1.

This has gone wrong repeatedly and silently. Real examples from this corpus:

- An equiangular-lines paper (Gram matrices, Seidel matrices, eigenvalue
  interlacing) shipped as a 720-vertex adjacency matrix with `verify` documented as
  *"check any size-k clique"*. **The instance contained no vectors at all.**
- A quantum-satisfiability paper about complex polynomial systems shipped as an
  assignment problem over 𝔽₁₁.
- A kissing-number paper with explicit real coordinates and sign patterns shipped as
  a conflict graph.

In each case the paper's mathematics was discarded before the solver saw anything,
every gate passed, and the row was counted as geometric or algebraic coverage.

If after reading you conclude the family fails G, H or V, **say so and stop**. A
correct rejection is a good outcome. Common disqualifiers: the task is in P; the
paper's contribution *is* a complete classification (so the answer is a lookup); the
witness is a proof or an unbounded-length object; verification needs research-level
machinery.

---

## STEP 1 — the module

One file, deterministic given `(n, seed)`. No file IO, no network, no printing at
import. Use `random.Random(seed)`, never global `random`.

**What you may import.** The standard library, and `gvlib/` from the repo root. `gvlib`
is standard-library-only itself, so importing it keeps the module dependency-free: it
carries exact rationals with JSON encoding (`gvlib.rationals`), multivariate polynomials
over ℚ (`gvlib.sparse_poly`), rational matrices with Bareiss determinant, rank, solve,
Gram and LDL/PSD (`gvlib.exact_matrices`), and Sturm sequences and real-root isolation
(`gvlib.roots`). Use it — a certificate that is a polynomial identity, a Gram matrix or
an isolating interval should not cost you a day of writing `Fraction` row reduction for
the fifth time. Nothing else may be imported.

`gvlib` sits at the repo root and your module sits in `results/<id>/`, so the import
needs the root on `sys.path` — `emit.sh` and `submit.sh` run from the root and find it,
but `harden.py` is invoked from your own directory and will not. Do it once, at the top,
and degrade gracefully:

```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # not present: stay standard-library-only
    exact_matrices = rationals = None
```

If it does not import, stay standard-library-only and say so in the README rather than
adding a dependency. Do not let a missing helper library become the reason a family
ships as a graph.

**`inst["answer"]` must be JSON-native.** `emit.sh` writes it straight into
`artifacts/<id>.jsonl` with `json.dumps`, so a `Fraction`, a `complex` or a custom class
does not fail your selftest — it fails the emit, after the expensive part is paid for.
Serialise: **rationals as `[num, den]`**, **monomials as exponent lists**, polynomials as
lists of `[[num, den], [e1, e2, ...]]`, matrices as lists of lists. `json.loads(
json.dumps(a)) == a` must hold for every answer the family produces, and whatever
`verify` accepts, `parse_answer` must be able to return.

```python
TRACK: str                  # "A" or "B" -- see TWO TRACKS.  Required.
    # scripts/corpus_report.py reads this straight into its `track` column; anything
    # that is not "A" or "B" is recorded as "unknown", which is what every family
    # shipped before this prompt reads as today.

PROBLEM_PROFILE: dict       # what this family really is, on a controlled vocabulary.
    # PREFERRED.  NATIVE (below) is the LEGACY form and is still what submit.sh reads,
    # so declare BOTH and keep them consistent.  Seven shipped modules declare only
    # NATIVE; they stay valid and nothing here orphans them.
    #
    # The token spellings below are the ones scripts/corpus_report.py reads.  Inventing
    # a synonym does not produce a warning -- it silently drops your row out of the
    # coverage counts, which is the exact failure mode this schema exists to stop.
    #
    # {"native_domain":  combinatorics|algebra|geometry|analysis|dynamics|
    #                    optimization|number_theory|logic
    #                    -- what the SOLVER reasons about, NOT the arXiv category.
    #
    #  "object_regime":  what kind of object the solver actually manipulates:
    #      finite_discrete     finite, exactly representable as ints and structures
    #      finite_field        elements of GF(q)
    #      integer_lattice     integer vectors / lattice points
    #      rational_exact      rationals, polynomials, matrices over Q; exact
    #                          arithmetic end to end, no approximation anywhere
    #      real_algebraic      the object is a real number, but the certificate is a
    #                          finite exact symbolic thing -- (minimal polynomial,
    #                          isolating interval with rational endpoints)
    #      continuous_analytic the object lives in R, C, a manifold, a function space
    #                          or a trajectory.  Then the certificate MUST be exact:
    #                          a rational SOS, a Lyapunov function over Q, or a
    #                          rigorous enclosure with exact rational endpoints
    #                          (declare certificate_form="interval" for that last one).
    #                          A float anywhere in verify() is a bug, not a regime.
    #
    #  "computational_core":  what the solver actually searches, one of
    #                    graph|csp_sat|exact_cover|subset_sum|permutation|
    #                    linear_algebra|polynomial_identity|sos|telescoping|
    #                    symbolic_integration|interval_bound|other
    #
    #  "certificate_form":  the shape of the answer, one of
    #                    sos|telescoping|symbolic_integral|algebraic_number|
    #                    matrix_certificate|interval|polynomial|rational|exact_symbolic
    #                        -- these count toward the release quota on symbolic
    #                           certificates
    #                    integer_tuple
    #                        -- this one does not, and it is what the corpus already
    #                           has far too much of.  Do not reach for it by reflex:
    #                           an answer that IS a tuple of small ints is one thing,
    #                           an answer flattened into one to make G4 easy to report
    #                           is the collapse this schema exists to measure.
    #  "native_objects": the objects the solver is HANDED, e.g.
    #                    ["Gram matrix over Q", "unit vectors"].  If the honest answer
    #                    is ["adjacency matrix"], write that and take the consequence.
    #  "verification_operations": the exact operations verify() performs, e.g.
    #                    ["exact rational inner product", "PSD check via LDL",
    #                     "sign comparison"].  If this list is nothing but set
    #                    membership and integer comparison, your core is discrete
    #                    whatever native_domain says.
    #
    #  "domain_essentiality":  how load-bearing the paper's mathematics is:
    #      native               ESSENTIAL -- the paper's objects are handed to the
    #                           solver AND verify() operates on them; delete the domain
    #                           structure and the problem is gone
    #      licensed_reduction   REPRESENTATIONAL -- a reduction the paper itself
    #                           licenses; the native objects are visible but the search
    #                           is carried by the surrogate
    #      discretised_analogue ANALOGUE -- the paper's mathematics was compiled away
    #                           before the solver saw anything
    #
    #  "reduction_kind":  none | paper_licensed | convenience
    #  "reduction":       None when reduction_kind == "none" -- it MUST be falsy then,
    #                     or the report labels a native family a discretised analogue.
    #                     Otherwise the citation string: "Section 5, Lemma 5 (...)".
    #  "reduction_source": paper_central | external_standard | benchmark_convenience
    #                     -- the finer distinction reduction_kind cannot spell.
    #                     paper_central     -> reduction_kind "paper_licensed"
    #                     external_standard -> reduction_kind "convenience": a textbook
    #                                          reduction is not this paper's
    #                                          mathematics and must not buy coverage
    #                     benchmark_convenience -> reduction_kind "convenience"
    #
    #  "intuition_type":  one of, and write it with SPACES, not underscores --
    #                     "symmetry" | "invariant" | "duality" |
    #                     "change of variables" | "ansatz" | "extremal bound" |
    #                     "decomposition" | "constraint propagation" |
    #                     "reduction recognition" | "search pruning".
    #                     The reporter matches this as prose: "change_of_variables"
    #                     with underscores does NOT match and lands as
    #                     "unclassified".  All ten match when written with spaces.
    #  "intuition_description": one sentence: the insight, and what a solver who does
    #                     not have it must do instead.
    #  "hardness_basis":  one sentence, and it must match TRACK.  Track A: the theorem
    #                     and the parameter regime.  Track B: the algorithm that
    #                     exists, its complexity, its measured cost at the shipping
    #                     preset, and why the compact route is not mechanically
    #                     executable in context.
    #  "max_answer_tokens": your MEASURED worst-case serialised answer length at the
    #                     shipping preset, in tokens.  See G9(c) for the cap.}
    #
    # **Only `domain_essentiality == "native"` together with `reduction_kind` in
    # {none, paper_licensed} counts toward native-domain coverage.**  Everything else
    # is recorded honestly and reported separately, and `benchmark_convenience` is
    # archived and excluded from the native release entirely.  Declaring
    # `discretised_analogue` costs you a coverage row.  Declaring `native` when the
    # solver is handed an adjacency matrix costs the corpus its credibility, which is
    # the failure this schema exists to prevent.

NATIVE: dict                # LEGACY form.  Still REQUIRED: submit.sh reads this one.
    # {"domain":    one of combinatorics|algebra|geometry|analysis|dynamics|
    #                       optimization|number_theory|logic
    #  "core":      what a solver actually searches, one of
    #               graph|csp_sat|exact_cover|subset_sum|permutation|
    #               linear_algebra|polynomial_identity|sos|telescoping|
    #               symbolic_integration|interval_bound|other
    #  "objects":   the mathematical objects the solver is handed, e.g.
    #               ["adjacency matrix"] or ["Gram matrix over Q", "unit vectors"]
    #  "intuition": the insight the problem is meant to test, e.g. "symmetry",
    #               "invariant", "change of variables", "ansatz", "duality"
    #  "reduction": None if the family is stated in the paper's own objects;
    #               otherwise the section/theorem that licenses the surrogate.}
    # Derive it from PROBLEM_PROFILE and keep the two consistent:
    #   domain    <- native_domain        core      <- computational_core
    #   objects   <- native_objects       reduction <- reduction  (same value)
    #   intuition <- intuition_type + ": " + intuition_description
    # `domain` is NOT the arXiv category -- it is what the solver reasons about.
    # A geometry paper rendered as an adjacency matrix has domain="combinatorics"
    # and core="graph".  Labelling it "geometry" is the failure this field exists
    # to prevent.

DIFFICULTY: dict            # exactly four presets, named "demo", "easy", "medium"
                            # and "hard", in that order -- harden.py walks the dict
                            # in insertion order, so it is the ladder, ascending.
                            # Each maps to kwargs for make_instance.
                            # "demo" is the smallest setting the family supports:
                            # a person must be able to solve it and check the
                            # answer on paper.  It is an illustration, not a
                            # difficulty level -- harden.py skips it, and
                            # SHIPPING_DIFFICULTY must never name it.

def make_instance(n, seed=0, **params) -> dict
    """Build an instance whose certificate you know BY CONSTRUCTION -- by inverse
    generation, theorem-backed construction, transformation of a known instance, or
    composition of identities (see G above). Never by solving the instance you just
    built. Returns a dict containing key "answer" (the certificate, JSON-native)
    plus all data the solver needs. `n` is the size parameter; larger n must mean
    harder."""

def render(inst) -> str
    """The complete problem statement a solver reads. See the OUTPUT CONTRACT.

    Hint modes, for G9: when os.environ.get("GV_HINT_MODE") is "structural" append
    STRUCTURAL_HINT, when it is "placebo" append PLACEBO_HINT, and otherwise append
    NOTHING. The default MUST be no hint -- emit.sh, submit.sh and the STEP 4
    hardening run all call render(), and a hint leaking into artifacts/ would
    silently change what the dataset is."""

STRUCTURAL_HINT: str        # ONE sentence naming the structural insight -- the thing
                            # intuition_description says this family tests.  Required.
                            # "The columns of the Gram matrix repeat with period 7."
PLACEBO_HINT: str           # ONE sentence of the same length and register carrying no
                            # structural information.  Required.  "This problem
                            # rewards being careful with the indexing."  See G9(a).

def parse_answer(text) -> object | None
    """Extract an answer from raw solver output. Return None if absent/malformed.
    Must tolerate surrounding prose, markdown fences, and whitespace."""

def verify(inst, answer) -> tuple[bool, str]
    """(True,"ok") or (False, reason). Accept ANY valid witness, not only
    inst["answer"] — other correct answers may exist. NEVER read inst["answer"]."""

### The answer format is collapsing too — pick from this menu

Measured across the 55 shipped modules: **82% of answers are plain integers or lists
of integers**, 65% are literally `list[int]`, and `search_space()` returned an `int`
**55 times out of 55**. There is not one rational, polynomial, matrix or symbolic
answer in the corpus.

Nothing forbids those. The gates just happen to be *cheapest* to satisfy with a tuple
of small integers — `search_space` is easy to count, `random_candidate` is easy to
sample, G4 is easy to measure. So every builder lands in the same place. Do not let
the path of least resistance choose your certificate for you.

`gvlib/` exists so the richer options cost about the same: exact rationals, sparse
multivariate polynomials over ℚ, exact matrices with Bareiss determinant and LDL
PSD-testing, and Sturm root isolation. Standard library only, already tested. Import
it rather than hand-rolling arithmetic.

| certificate | JSON-native form | `search_space` | `random_candidate` |
|---|---|---|---|
| tuple of indices | `[3, 17, 42]` | C(n,k) | sample k of n |
| **rational vector** | `[[num, den], ...]` | bound heights: (2H+1)^d | sample numerators/denominators in range |
| **polynomial** | `[[coef, [e1,e2,...]], ...]` | #monomials under the degree bound, coefficients bounded | sample a support set, then coefficients |
| **matrix over ℚ or F_q** | `[[...],[...]]` | q^(mn), or bounded heights | sample entries |
| **SOS decomposition** | list of polynomials | as polynomial, times the number of squares | sample squares, sum them |
| **primal–dual pair** | `{"x": [...], "y": [...]}` | product of the two spaces | sample both |
| **algebraic number** | `{"minpoly": [...], "interval": [[a,b],[c,d]]}` | #polynomials under degree+height bound | sample a squarefree minpoly, isolate |
| **group element / word** | `["a","b","a^-1", ...]` | (2g)^L for length L | sample a reduced word |
| **permutation / ordering** | `[2, 0, 1, ...]` | n! | Fisher–Yates |
| **set system / partition** | `[[...],[...]]` | Bell or Stirling number | sample a random partition |

`search_space` may return `None` when the declared language is genuinely uncountable —
then G5 carries a **sampled density estimate** instead. That path exists and has never
been used; if your certificate is naturally continuous-but-certified, use it rather
than discretising the answer to keep the counter happy.

**Before you settle on `list[int]`, write down what the paper's own objects are.** If
the theorem is about polynomials, the answer should probably be a polynomial. Reducing
it to indices is the same failure as reducing geometry to a graph — it survives the
gates and loses the mathematics.

CERTIFICATE_LANGUAGE: dict  # the BOUNDED language the answer is written in. Required.
    # {"description": a human-readable grammar/bounds statement, e.g.
    #                 "SOS: <=6 squares, each a poly of degree <=4 over the fixed
    #                  monomial basis, rational coefficients with |num|,|den| < 2^32"
    #  "bounds":      the numeric bounds that make it finite, e.g.
    #                 {"n_squares": 6, "max_degree": 4, "basis": 45, "coeff_bits": 32}}
    #
    # This field exists because requiring an integer `search_space` silently forces
    # every family to be a tuple of small integers.  Measured over the first 40
    # shipped generators: search_space returned an int 40/40 and None 0/40, and not
    # one answer was a rational, a polynomial or a symbolic expression -- because a
    # symbolic answer has no uniformly-sampleable candidate set, so G4 could not be
    # reported and the family was never built.
    #
    # Declaring bounds fixes that.  An antiderivative is infinite; an antiderivative
    # over a fixed operator set with depth <= 4 and coefficients under 2^16 is a
    # finite, countable, samplable space.  Bound the language and the continuous
    # families become expressible without weakening exact verification at all.

def random_candidate(inst, rng) -> object
    """A random candidate that ALREADY SATISFIES every constraint a solver would
    trivially enforce from reading the statement (shape, size, and any structural
    rule that is obvious once stated). Used to measure P(random guess). Must not
    bias toward the planted answer. See G4 — do NOT sample from the naive space."""

def search_space(inst) -> int | None
    """Size of CERTIFICATE_LANGUAGE at these parameters -- the space
    `random_candidate` samples from, not a looser superset. Return None ONLY if
    the declared language is genuinely uncountable; then G5 must carry a sampled
    density estimate instead."""

def enumerate_all(inst) -> int | None
    """Exact count of valid answers by brute force; None if the space is too big.
    Cap the work — return None rather than hanging."""

def canonical_key(inst) -> str
    """This family's definition of "the same problem". Two instances that map to
    each other by relabelling — vertex numbering, permutation of the ground set,
    reordering of the input — MUST return the same key, so that emit.sh can tell
    a genuinely new instance from a recolouring of one it already has.

    Do NOT hash the seed, and do NOT hash render(inst). Both make every instance
    look distinct and silently disable the diversity check, which is worse than
    having no check at all. Build the key from the instance data in a canonical
    order: sort what can be sorted, normalise what has a normal form, and if the
    family's isomorphism is genuinely intractable say so in the README caveats
    and key on the strongest invariant you can compute cheaply.

    Must be deterministic: same seed and params => same key. submit.sh checks this."""

def escalate(params) -> dict | str | None
    """Parameters strictly harder than `params`.

    GROW THE HAYSTACK, NOT THE NEEDLE.  This is the rule, and 61% of shipped
    modules break it: they escalate by raising `n`, which lengthens the ANSWER,
    which hits the output cap, at which point they return None and the harness
    calls the family `too_easy` and the paper is thrown away.  Ten papers have
    been discarded that way -- judged un-writable rather than unsuitable.

    Difficulty should scale with the SPACE THE ANSWER IS DRAWN FROM, not with the
    NUMBER OF THINGS IN THE ANSWER.  A planted clique is the model: n goes from
    512 to 4096 while k stays 16, so the search explodes and the answer stays
    sixteen numbers long.

    Axes that raise difficulty at FIXED answer length -- reach for these first:
      - enlarge the ground set / ambient space, keeping the witness size fixed
      - raise the modulus, field size or coefficient range, so each answer
        element carries more entropy without taking more characters
      - raise decoy density or crowding: more near-misses per real element
      - move the plant closer to the feasibility boundary
      - delete redundant clues from the instance -- less given, same answer
      - tighten the constraints, shrinking the solution set

    Only after those are exhausted should you consider a longer answer.

    RETURN VALUES, and the distinction matters:
      dict          -- harder parameters. Preferred.
      "cap_bound"   -- the family CAN be made harder, but only by pushing the
                       answer past the output cap.  Say this instead of None.
                       It parks the paper rather than condemning it: the limit
                       is our answer format, not the paper's mathematics.
      None          -- genuinely nothing left on ANY axis.  Rare.  If you are
                       returning None because the answer got too long, you mean
                       "cap_bound"."""
```

---

## STEP 2 — the OUTPUT CONTRACT (render + parse_answer)

`render` must be **self-contained** — a solver sees only this string, never the
paper — and must end with explicit output instructions that `parse_answer` can
consume. Use a delimited block:

```
Give your final answer inside <answer></answer> tags, as <exact format>.
Example: <answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

Rules for the statement:

- Define every term used. Do not assume the solver knows the paper's notation.
- **Pin down every ambiguity that could make a correct answer look wrong.** Closed
  vs open intervals, inclusive vs exclusive bounds, 0- vs 1-indexing, whether order
  matters, whether repeats are allowed. Each unstated convention is a grading bug.
- State the required size/shape of the answer explicitly.
- Give all instance data inline, in a simple parseable layout.
- **Keep the answer writable.** The solver has to type it out, by hand, with no
  scratchpad. An answer running to thousands of elements measures transcription
  stamina, not intuition, and the failures it produces tell you nothing. G9(c) puts a
  hard cap on this.
- **Serialise rationals and polynomials the way `parse_answer` reads them back**, and
  say so in the statement: rationals as `num/den`, monomials as exponent lists. The
  rendered form and the JSON form must agree.

`parse_answer` must round-trip: `parse_answer(render_of_answer) == answer`, and must
return `None` — not raise — on garbage.

---

## STEP 3 — mandatory gates

Implement `selftest()` running all of these and returning a dict. **Every gate must
pass at the difficulty you ship** — except where a part is explicitly marked
*recorded, not gated*, which is true of G9(a) and of nothing else.

| gate | requirement |
|---|---|
| **G1 planted verifies** | `verify(inst, inst["answer"])` is True — for **every** preset × several seeds. Re-run this after *any* change. |
| **G2 rejects corruption** | Perturbed answers (drop one element, swap one, duplicate, empty, out-of-range) are all rejected, each with a distinct reason. |
| **G3 round-trip** | `parse_answer` recovers an answer from a realistic model-style response with prose around it. |
| **G4 guess resistance** | `P(random guess) < 1e-6` from ≥200k samples drawn from `CERTIFICATE_LANGUAGE`, measured **structure-aware** (see below). Report hits/total. |
| **G5 density + baseline cost** | A real number, never "not feasible": an exact solution count where enumeration works at any preset, otherwise a sampled density estimate — **plus** the measured cost of your strongest attack. See below. |
| **G6 adversary panel** | ≥4 attacks in `attacks`, each FAILING across ≥8 seeds. Track A: three cheap probes **plus the standard algorithm for the problem class**. Track B: three cheap probes plus an in-context attack, with the standard algorithm reported separately under `reference_algorithm`. See TWO TRACKS and below. |
| **G7 scales** | Difficulty grows with `n`; a size-doubled instance still builds and still passes G1. |
| **G8 canonical_key** | The key is invariant under every relabelling that preserves the family, and distinct across unrelated instances. See below — `submit.sh` cannot check this. |
| **G9 no-tool suitability** | Two gated parts — the family still defeats the oracle pool **with** its structural hint, and the answer and route fit the caps — plus a three-arm diagnostic (bare / hinted / placebo) that is **recorded, never gated**. See below. |

### G4: measure P(guess) against a solver, not against noise

The naive candidate space is almost always a wild overestimate of the difficulty,
and reporting it makes a guessable family look impossible. `random_candidate` must
sample from the space **a solver who has read the statement would search**, with
every freely-deducible constraint already applied.

Measured on a real run of this prompt — an exact-tiling family where the statement
implies exactly 3 items fill each block:

| n | P(guess), uniform over all shift vectors | P(guess), structure-aware |
|---|---|---|
| 2 | 2.0e-10 | **0.20** |
| 3 | 6.6e-16 | 4.3e-2 |
| 4 | 7.0e-22 | 3.1e-3 |

The uniform column says "impossible" for an instance that is in fact guessed one
time in five. Eighty orders of magnitude of self-deception.

So: before sampling, ask what a solver gets for free from the statement — the
arity, the partition shape, the degree, the range, the sum constraint — and build
those into `random_candidate`. If you also report the naive number, label it
clearly as the naive one. The structure-aware number is the one that must pass.

### G5: measure difficulty, do not infer it from cardinality

Across the first 40 shipped generators, `enumerate_all` returned `None` at the
**shipping** preset **40/40**. G5 was therefore measured on a reduced instance
(n = 4–40, against shipping n up to 512) or carried no number at all (7/40). It
never described the instance that actually ships — and a density at n=4 says
nothing about n=32.

Worse, a reduced-preset number can be passed while being alarming: `2104.04330`
reported a solution fraction of **5.7e-4** at n=18 — roughly one candidate in 1768
is valid — and passed G5 anyway.

A large space is not difficulty. `2503.01929` reported a 1536-bit candidate space
and fell to Algorithm X in under five seconds. Report both of these, as numbers,
**at the shipping preset**:

1. **Density at the shipping preset.** Exact count if `enumerate_all` terminates
   there; otherwise sample `random_candidate` and report the observed fraction of
   valid answers with the sample size. A count from a smaller preset may be given
   in addition, labelled with its `n` — never instead. `None` is not an answer.
2. **Baseline cost.** Run your strongest G6 attack at the *shipping* preset and
   record what it actually cost: wall-clock seconds, and nodes/restarts/iterations.
   A family whose best attack fails in 0.2 s is not obviously hard — it may simply
   be unsatisfiable-looking to that attack. Cost is the honest difficulty signal.

### G6: the adversary panel — this is where generators actually die

A planted instance can pass every correctness gate and still be trivial, because
the planting leaves a statistical signature. **Write attacks that exploit how you
built it**, and prove they fail. At minimum:

- **Outlier attack** — is the planted element distinguishable by any per-element
  statistic? Position, magnitude, width, degree, frequency, ordering.
- **Greedy attack** — does an obvious greedy/left-to-right rule solve it?
- **Random restart** — does sampling with a mild heuristic find a solution?
- **The standard algorithm for the problem class — REQUIRED, not optional.** The
  three above are generic and they are *not sufficient*; they probe how you built
  the instance, not what is known about the problem. Ask what a specialist would
  reach for first and run *that*:

  | the problem is about | run at least |
  |---|---|
  | satisfiability / CSP | a SAT or SMT solver, or DPLL with unit propagation |
  | covering, packing, assignment, scheduling | an ILP/LP relaxation, or matching |
  | a planted subgraph, colouring, partition, or community | **a spectral method** — top eigenvectors of the adjacency/Laplacian, and an SDP or nuclear-norm relaxation if the paper mentions one |
  | subset sum, knapsack, lattice, or small-coefficient integer relations | LLL / lattice reduction |
  | exact cover, tiling, set partition | Algorithm X / DLX, or a CP solver |
  | paths, cycles, flows, connectivity | the classical polynomial algorithm for the relaxed version, then repair |
  | permutations, words, group elements | normal forms and the natural rewriting/canonicalisation |

  If no library is available, implement the cheap version — power iteration is a
  dozen lines and breaks most planted-subgraph constructions. If you genuinely
  cannot run the standard attack, say so explicitly in the README caveats and name
  the attack you could not run. Never silently omit it.

**Report G6 in this shape**, so the panel can be checked mechanically rather than
read prose-by-prose:

```python
report["G6_adversary_panel"] = {
    "pass": all_failed,
    "attacks": {                      # one entry per attack, name -> result
        "outlier_degree":     {"successes": 0, "attempts": 8},
        "greedy_largest_first":{"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "spectral_top_eigenvector": {"successes": 0, "attempts": 8},   # the domain attack
    },
}
```

Extra keys alongside `attacks` are fine. `submit.sh` requires `attacks` to be
present with **at least 4 entries** — three generic probes plus the domain attack — and
it **recomputes `pass` from the `successes` on disk**: a panel that records a solved
attack is refused no matter what `pass` says. `2410.07666` logged walksat at 8/8 and
honestly set `pass=false`; nothing else would have caught it.

That recomputation is exactly why a **Track B** family must not put its
domain-standard algorithm in `attacks`. On Track B that algorithm is *supposed* to
succeed — it is the `hardness_basis`, not a failure — so it goes in a sibling key and
`attacks` keeps its meaning:

```python
report["G6_adversary_panel"]["reference_algorithm"] = {   # Track B only
    "name": "Bareiss elimination over Q",
    "complexity": "O(n^3) exact",
    "wall_clock_sec": 0.4,
    "operations": 1_240_000,      # this number IS the Track B hardness claim
    "solves": "8/8, as expected",
}
```

Track B still needs four *failing* entries in `attacks`, and its fourth is an attack a
solver could actually run in context without tools — the by-hand heuristic, the greedy
route, the obvious ansatz. If you cannot find one that fails, the family is guessable by
hand and you should reject it.

Real failures from previous attempts, so you know what this looks like:

- Planted intervals placed at multiples of 100 while decoys clustered elsewhere:
  "pick the positional outlier" solved **37%** with no search.
- Fixing that by widening decoys made them 10× wider than plants: "pick the
  narrowest" solved **25%**.
- A planted graph partition was so sparse that brute force cracked n=22 in 0.03 s,
  yet adding edges to harden it made instances *unsatisfiable* — the usable window
  was narrow and had to be found by sweeping.
- A zero-sum family had a 3×10⁶ space but **7.7% of all candidates were valid** —
  a huge space and a worthless problem.
- **A bounded Token Jumping family (arXiv:2408.04743) passed every gate, and the
  four-vendor oracle pool returned `hardened`.** A construction-aware spectral
  attack then recovered a verified witness on **20/20 shipping instances in
  polynomial time** — the planted colour classes formed an exact −3 eigenvector.
  The generic outlier/greedy/restart panel saw nothing. This is why the domain
  attack is mandatory: gates passing and the oracle failing to solve are jointly
  *not* evidence of hardness, and this family would have shipped on that evidence.

**Draw plants and decoys from the SAME distribution.** Get difficulty from
crowding/density/size, never from making the planted object look different.

### G8: canonical_key must be invariant under relabelling

`submit.sh` emits sample instances and counts distinct keys. It checks only that
the key is **deterministic** — it cannot tell a real invariant from a fake one.
So a key built on the seed, or on `hashlib.sha256(render(inst))`, makes every
instance look distinct, reports a perfect diversity score, and silently turns the
duplicate check into a no-op that can never fail. That is worse than shipping no
check at all, and nothing downstream will catch it. This gate is the only thing
standing between that bug and the corpus.

Prove the key is structural, in `selftest()`:

1. **Invariance.** Enumerate the transformations that map an instance to *the same
   problem* — permuting the ground set, renumbering vertices, reordering the input
   list, and any family-specific symmetry (an affine map `x -> u*x + t` on a cyclic
   group, a change of basis, a global translation). Apply each, and each composed
   with the others, over ≥20 seeds. Assert the key is unchanged every time.
2. **The transformation is real.** For at least one relabelling, assert the
   transformed instance still verifies against the *original, untransformed*
   answer — or against the answer carried through the relabelling. A key that is
   invariant under a map that does not preserve the problem is over-collapsing
   distinct instances, which is the opposite failure and just as bad.
3. **Distinctness.** Over ≥20 unrelated seeds, assert all keys differ.

Report all three counts in the gate dict. If the family's isomorphism is genuinely
intractable, say so explicitly in the README caveats and key on the strongest
cheap invariant you can — but still run steps 2 and 3 against it.

### G9: is the failure informative? — measured, mostly not gated

Every family here is built so that a model fails it. That makes "the model failed"
almost uninformative on its own: a model also fails a question whose answer is forty
thousand tokens long, and one that needs ten thousand exact multiplications. Those
failures say nothing about mathematical intuition, and a corpus full of them measures
patience.

G9 separates the two. **It is not a "the model must succeed" gate.** That would be the
exact negation of STEP 4, which holds a level only when all three oracles fail, and it
would delete every family that survives the hardening loop. Three parts, and only two of
them are gates.

#### (a) The three-arm diagnostic — recorded, never gated

Run the shipping preset three times and record solved/attempts for each arm:

| arm | prompt |
|---|---|
| bare | `render(inst)` as shipped |
| hinted | `render(inst)` + `STRUCTURAL_HINT` |
| placebo | `render(inst)` + `PLACEBO_HINT` |

**Why the placebo arm exists.** Appending *any* sentence changes the prompt — its
length, its register, and the signal that the asker thought a hint was warranted.
Comparing hinted against bare confounds all of that with the hint's actual content. The
placebo holds everything fixed except the structural information, so **hinted − placebo**
is the estimate of real structural help; hinted − bare is contaminated by prompt leakage
and is not.

If hinted ≈ placebo, your hint carried no information: either it is badly written, or
the family does not respond to the intuition you claimed in `intuition_type`. That is a
finding, not a failure. Record the three numbers and say what you conclude in the
README. **It does not block the ship** — this arm exists so the corpus knows what it is
measuring, and gating on it would let a builder tune the hint instead of the family.

#### (b) The polarity-flipped gate — this part IS gated

> The family must still defeat the oracle pool **when it is given its one-sentence
> structural hint.**

This is strictly stronger than today's bar and it contradicts nothing: STEP 4 already
requires the pool to fail on the bare statement; this requires it to fail on an easier
version of the same statement. A family that survives bare but dissolves the moment you
name the trick was never testing whether a model can *find* the structure — it was
testing whether the model had already memorised it.

Run it with the harness, not by hand:

```bash
mkdir -p g9_hinted && cp gen_<arxiv_id>.py g9_hinted/
# in the COPY, cut DIFFICULTY down to the shipping preset alone, so the ladder
# has one rung and the verdict is about that rung
cd g9_hinted && GV_HINT_MODE=structural python3 ../../../scripts/harden.py gen_<arxiv_id>.py
```

`harden.py` opens `llm_loop_transcript.jsonl` and `.meta.json` with mode `"w"` — it
**overwrites**. Run every G9 arm in its own scratch directory, never in the result
directory, or you will destroy the STEP 4 evidence you already paid for. Copy the
finished transcripts back as `g9_<arm>_transcript.jsonl`.

Read the verdict with the polarity flipped: `hardened` means the hint did not break the
family and G9(b) passes. `too_easy` means the hint broke it, and the family fails G9(b).
You may then move **one** rung up the `DIFFICULTY` ladder and re-run STEP 4 bare *and*
this arm at the new level, **once**. If the hint still breaks it, write `REJECTED.md`
citing G9(b) and stop. This is not hand-tuning past a verdict — the bare verdict was
`hardened` and the whole loop is re-run at the new level — but the cap of one is there
so that it cannot become hand-tuning.

#### (c) The size and effort caps — gated

| cap | limit at the shipping preset |
|---|---|
| serialised answer | ≤ **2,000 characters** (≈ **500 tokens**) and ≤ **256 atomic elements** |
| intended route | ≤ **300 exact arithmetic operations** |

Measure both, put the numbers in the gate dict, and put the token figure in
`PROBLEM_PROFILE["max_answer_tokens"]`.

"Intended route" means the operations left **after** the insight — the compact route the
family claims to test, not the search it replaces. A family over the answer cap is a
transcription test. A family whose intended method needs thousands of arithmetic
operations is a calculator test, and the evaluated model has no calculator; that is a
fact about the harness, not a property of the mathematics.

If you are genuinely over a cap and believe the family should ship anyway, say so in the
README caveats with the measured number and expect to be argued with. Do not quietly
round it down.

Report the gate like this:

```python
report["G9_no_tool_suitability"] = {
    "pass": hinted_still_hardened and within_caps,     # (b) and (c) only
    "arms": {                                          # (a): recorded, not gated
        "bare":    {"solved": 0, "attempts": 3},
        "hinted":  {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_minus_placebo": 0.0,
    "hinted_verdict": "hardened",                      # (b)
    "answer_chars": 412, "answer_tokens": 104, "answer_elements": 32,   # (c)
    "intended_route_operations": 47,                   # (c)
}
```

---

## STEP 4 — the LLM hardening loop (required)

**You do not write this loop.** `scripts/harden.py` owns it. Run it from your
working directory once the module passes STEP 3:

```bash
python3 ../../scripts/harden.py gen_<arxiv_id>.py
```

It requires **`OPENROUTER_API_KEY`** in the environment. An OpenAI key alone is not
enough: the oracle pool spans four vendors and is reached through OpenRouter.

What it does, so you know what its output means:

- The oracle is drawn **fresh from a four-vendor pool on every single call**, at
  reasoning effort `medium`. A family that only defeats one model has not been shown
  to be hard — it has been fitted to that model's blind spots. The builder model is
  excluded from the pool for the same reason.
- Each difficulty level gets **three attempts against three distinct models**, each on
  a randomly drawn seed. The level is defeated if **any** of them solves it; it is
  held only if **all three fail**.
- A call that errors is redrawn against another model and does not consume an attempt.
  An API failure is never recorded as the model failing to solve.
- The ladder starts at `easy`. `demo` is skipped: it is built to be solvable, so
  starting there would spend an escalation proving exactly that.
- When a level is solved the harness escalates: to the next named preset, and once
  `DIFFICULTY` is exhausted, by calling your `escalate()`. After **3 escalations** — or
  as soon as `escalate()` returns None — it stops and reports `verdict: "too_easy"`.
- It writes `llm_loop_transcript.jsonl` itself, and records the master seed, the pool
  and its verdict in `.meta.json`. Do not write either file by hand; `submit.sh`
  validates their schema and will reject a hand-rolled one.
- It opens both files with mode `"w"`. **A second run in the same directory overwrites
  the evidence from the first.** This run — bare, no hint — is the one that ships, so
  G9's extra arms run in their own scratch directories. See G9(b).

Read the verdict it prints:

- `{"verdict": "hardened", ...}` — `shipping_params` is the level that held. If it came
  from `escalate()` rather than a named preset, the four names are already taken, so
  **slide the ladder up**: drop the rung the oracle solved, keep the survivors in
  ascending order, and put the escalated level in as the new `hard`, leaving
  `demo`/`easy`/`medium`/`hard` still spelled that way. Point `SHIPPING_DIFFICULTY` at
  whichever name now carries the level that held, then re-run STEP 3's gates at it.
  `demo` never moves: it stays the hand-solvable rung.
- `{"verdict": "too_easy", ...}` — the family is **given up on**. Write `REJECTED.md`
  saying which theorem or regime you were relying on and why you now think it does not
  bite, and stop. Do not keep escalating by hand, and do not ship it. Three escalations
  against four vendors is the bar; a family that clears the bar only after you retune
  it by hand is a family tuned to that run.

Your remaining job in this step is the renderer, not the loop: if the transcript shows
`parse_answer` returning None on a reply that visibly *contains* an answer, that is a
**G3 bug in your output contract**. Fix the contract and re-run the harness — do not
celebrate a false negative.

---

## STEP 5 — deliverables

Write these as **files in the working directory**, not only as chat output — the
repo collects them and a report that exists only in the run log is not machine
readable.

1. `gen_<arxiv_id>.py` — the module. Set `SHIPPING_DIFFICULTY` to the preset you ship.
2. `selftest_report.json` — the dict `selftest()` returns: every gate with its
   measured number (P(guess) as hits/total, solution counts, per-attack results,
   G9's three arms and its measured answer size and operation count).
3. `llm_loop_transcript.jsonl` — **written by `scripts/harden.py`, not by you.** One
   JSON object per oracle call, carrying `schema_version, model, effort, preset,
   params, seed, escalation_round, solved, parsed, verify_ok, verify_reason, reply,
   error, elapsed_sec, http_status, finish_reason`. This is the evidence for the hardness claim.
   `.meta.json` is likewise owned by the scripts (master seeds, oracle pool, verdict,
   duplicate rate) — leave both alone.
4. `g9_hinted_transcript.jsonl` and `g9_placebo_transcript.jsonl` — the G9 arms,
   produced by `harden.py` in scratch directories and copied back. See G9(b).
5. A `NOTES` string in the module: which paper section fixed the definition, which
   result told you what makes it easy, what you did to defeat each attack.
6. `README.md` — **you write this, by hand.** See below.

### README.md

You are the only one who will ever have read this paper alongside this code. A
script can reformat the JSON; it cannot say which theorem you were steering around
or which version of the generator was secretly trivial. Write the page you would
have wanted before you started.

Write for someone who has **never read the paper** and wants to know, in this order:
what the problem is, whether they can trust it, and how to run it. Keep it tight —
one screen of prose plus tables. Cover:

- **The profile up front**: `TRACK`, native domain, object regime, computational core,
  certificate form, intended intuition and `domain_essentiality` — copied from
  `PROBLEM_PROFILE`. If `reduction_kind` is anything but `none` or `paper_licensed`,
  say plainly that this is **not** native coverage of the paper's domain, and name what
  was discarded.
- **What the family is**, in plain language. What object is handed to the solver,
  what they must find, and why checking an answer is cheap. Name the paper, link it.
- **Why it is hard**, in the sense your `TRACK` declares. Track A: the specific theorem
  and parameter regime you are inside, and — just as important — the easy regimes you
  had to avoid and the results that identify them. Track B: **name the algorithm that
  solves it**, its complexity and its measured cost, then say why the compact route is
  not something a model can execute in context. A Track B README that reads like a
  Track A README is the failure mode here. Cite sections by number either way. This is
  the part only you know.
- **A worked example.** A rendered instance small enough to read in full — use the
  `demo` preset, which exists for this — its answer, `verify` returning True on it,
  and `verify` returning False with its reason on a corrupted variant. Say plainly
  whether a person can actually solve it by hand, and if not, why the family's
  smallest supported setting still is not hand-scale.
- **Difficulty presets**, as a table, and which one ships. If a preset was rejected,
  say which gate rejected it — a preset the oracle failed but an attack solved is
  worth recording.
- **Gate results**, as a table with the measured numbers.
- **The oracle loop**, as a table: preset, seed, solved, why.
- **The G9 arms**, as a table: bare / hinted / placebo solved-out-of-attempts, the
  hinted − placebo difference, and what you conclude. If the structural hint bought the
  oracle nothing, say so — that is evidence about your `intuition_type`, and this
  README is the only place it will ever be written down. Give the measured answer size
  and intended-route operation count here too.
- **How to use it**: an import-and-verify snippet, and the `scripts/emit.sh` command.
- **Caveats — required, and do not skip this one.** What would make this family
  easy; what your `P(guess)` number does and does not mean given the prior your
  `random_candidate` samples from; which attacks you did *not* try; anything you
  are unsure of. A reader who trusts a weak family because the README was silent
  is worse off than one you warned. If you genuinely have no caveat, say what you
  checked that makes you confident.

`submit.sh` refuses a result whose `README.md`, `selftest_report.json` or
`llm_loop_transcript.jsonl` is missing.

### `cap_bound` is not a rejection

If the harness returns `cap_bound`, **do not write `REJECTED.md`.** The family is
fine and the paper is fine; the answer simply cannot be written out at the size that
would make it hard. Say so in your report and stop. The paper goes back to the pool
for a future run under a larger cap, not into the reject pile.

You should reach `cap_bound` only after trying the fixed-length axes in
`escalate()`. If you reached it by raising `n` alone, you have not finished the job.

## Writing `REJECTED.md`

A rejection is a real result and costs nothing — but a *wrong* rejection throws away a
paper someone already paid to read, and an audit found 7 of 12 rejections were wrong.
So `REJECTED.md` must answer the question that was skipped:

- Which of G, H, V fails, and **which track** — a family can fail H on Track A and
  still be a perfectly good Track B family.
- If you are rejecting because an efficient method exists, state the **mechanical
  cost** and the **compact route length**, and show the gap is too small to test
  anything. Without those two numbers the rejection is not reviewable, and
  `submit.sh --reject` will refuse it.
- Which theorem or section you are relying on, by number.

Do not reject on the abstract. Do not reject because the paper "gives a construction" —
that describes almost every paper in this pool.

## Report honestly

If the family fails, say which gate and why. A rejected family costs nothing; a
family that silently generates easy or unsolvable instances poisons the dataset.
Never report a gate as passing without the number that shows it.
