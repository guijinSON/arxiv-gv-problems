# TASK: turn this paper into a self-contained, verified problem generator

You are given one arXiv paper. Produce a single Python module that manufactures an
unlimited supply of instances of ONE problem family from that paper, together with
everything needed to pose the problem to a solver and grade the answer
automatically.

A family is only acceptable if all three hold:

- **G — generatable.** You can build an instance *and know its answer*, because you
  sampled the answer first and constructed the problem around it.
- **H — hard.** No known polynomial-time or closed-form method, and the answer space
  is far too large to guess.
- **V — verifiable.** A candidate answer is checked cheaply and exactly: substitute,
  expand, recompute, compare.

The answer must be a **witness** — a structured object handed to a checker. Never an
absence ("no solution exists"), never an optimum whose optimality is the claim,
never a real number or an asymptotic rate.

---

## STEP 0 — read the actual paper, not just the abstract

**Do this first. Do not skip it.** Fetch and read the full text
(`https://arxiv.org/abs/<id>`, or the LaTeX source at
`https://arxiv.org/e-print/<id>`).

The abstract will not tell you the three things that decide whether your generator
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
say so in `NATIVE["reduction"]`, and do not present it as coverage of the paper's
native domain.

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

One file, standard library only, deterministic given `(n, seed)`. No file IO, no
network, no printing at import. Use `random.Random(seed)`, never global `random`.

```python
NATIVE: dict                # what this family really is -- see below.  Required.
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
    """Inverse generation: sample the answer FIRST, then build the problem around
    it. Returns a dict containing key "answer" (the planted witness) plus all data
    the solver needs. `n` is the size parameter; larger n must mean harder."""

def render(inst) -> str
    """The complete problem statement a solver reads. See the OUTPUT CONTRACT."""

def parse_answer(text) -> object | None
    """Extract an answer from raw solver output. Return None if absent/malformed.
    Must tolerate surrounding prose, markdown fences, and whitespace."""

def verify(inst, answer) -> tuple[bool, str]
    """(True,"ok") or (False, reason). Accept ANY valid witness, not only
    inst["answer"] — other correct answers may exist. NEVER read inst["answer"]."""

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
    """Size of the naive candidate space, or None if not countable."""

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

def escalate(params) -> dict | None
    """Parameters strictly harder than `params`, or None if this family cannot be
    made any harder. Called by the hardening harness once the named DIFFICULTY
    ladder is exhausted and the oracle pool is still solving instances.

    Raising `n` is not automatically the right move — for many families the usable
    window is narrow, and a larger n makes instances unsatisfiable or, worse,
    easier. Escalate along whichever axis actually costs a solver: crowding,
    density, the number of decoys, how close the plant sits to the feasibility
    boundary. Returning None is a legitimate answer and ends the loop."""
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

`parse_answer` must round-trip: `parse_answer(render_of_answer) == answer`, and must
return `None` — not raise — on garbage.

---

## STEP 3 — mandatory gates

Implement `selftest()` running all of these and returning a dict. **Every gate must
pass at the difficulty you ship.**

| gate | requirement |
|---|---|
| **G1 planted verifies** | `verify(inst, inst["answer"])` is True — for **every** preset × several seeds. Re-run this after *any* change. |
| **G2 rejects corruption** | Perturbed answers (drop one element, swap one, duplicate, empty, out-of-range) are all rejected, each with a distinct reason. |
| **G3 round-trip** | `parse_answer` recovers an answer from a realistic model-style response with prose around it. |
| **G4 guess resistance** | `P(random guess) < 1e-6` from ≥200k samples drawn from `CERTIFICATE_LANGUAGE`, measured **structure-aware** (see below). Report hits/total. |
| **G5 density + baseline cost** | A real number, never "not feasible": an exact solution count where enumeration works at any preset, otherwise a sampled density estimate — **plus** the measured cost of your strongest attack. See below. |
| **G6 adversary panel** | ≥3 cheap attacks **plus the standard algorithm for the problem class**, each FAILING across ≥8 seeds. The domain attack is mandatory — see below. |
| **G7 scales** | Difficulty grows with `n`; a size-doubled instance still builds and still passes G1. |
| **G8 canonical_key** | The key is invariant under every relabelling that preserves the family, and distinct across unrelated instances. See below — `submit.sh` cannot check this. |

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
present with **at least 4 entries** — three generic probes plus the domain attack.

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
   measured number (P(guess) as hits/total, solution counts, per-attack results).
3. `llm_loop_transcript.jsonl` — **written by `scripts/harden.py`, not by you.** One
   JSON object per oracle call, carrying `schema_version, model, effort, preset,
   params, seed, escalation_round, solved, parsed, verify_ok, verify_reason, reply,
   error, elapsed_sec, http_status, finish_reason`. This is the evidence for the hardness claim.
   `.meta.json` is likewise owned by the scripts (master seeds, oracle pool, verdict,
   duplicate rate) — leave both alone.
4. A `NOTES` string in the module: which paper section fixed the definition, which
   result told you what makes it easy, what you did to defeat each attack.
5. `README.md` — **you write this, by hand.** See below.

### README.md

You are the only one who will ever have read this paper alongside this code. A
script can reformat the JSON; it cannot say which theorem you were steering around
or which version of the generator was secretly trivial. Write the page you would
have wanted before you started.

Write for someone who has **never read the paper** and wants to know, in this order:
what the problem is, whether they can trust it, and how to run it. Keep it tight —
one screen of prose plus tables. Cover:

- **The three axes up front**: native domain, computational core, intended
  intuition — copied from `NATIVE`. If `reduction` is set, say plainly that this is
  a discretised analogue of the paper's problem and name what was discarded.
- **What the family is**, in plain language. What object is handed to the solver,
  what they must find, and why checking an answer is cheap. Name the paper, link it.
- **Why it is hard.** The specific theorem and parameter regime you are inside, and
  — just as important — the easy regimes you had to avoid and the results that
  identify them. Cite sections by number. This is the part only you know.
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
- **How to use it**: an import-and-verify snippet, and the `scripts/emit.sh` command.
- **Caveats — required, and do not skip this one.** What would make this family
  easy; what your `P(guess)` number does and does not mean given the prior your
  `random_candidate` samples from; which attacks you did *not* try; anything you
  are unsure of. A reader who trusts a weak family because the README was silent
  is worse off than one you warned. If you genuinely have no caveat, say what you
  checked that makes you confident.

`submit.sh` refuses a result whose `README.md`, `selftest_report.json` or
`llm_loop_transcript.jsonl` is missing.

## Report honestly

If the family fails, say which gate and why. A rejected family costs nothing; a
family that silently generates easy or unsolvable instances poisons the dataset.
Never report a gate as passing without the number that shows it.
