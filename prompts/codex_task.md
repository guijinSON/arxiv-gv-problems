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
DIFFICULTY: dict            # named presets, e.g. {"easy": {...}, "hard": {...}}
                            # each maps to kwargs for make_instance

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

def random_candidate(inst, rng) -> object
    """A random candidate that ALREADY SATISFIES every constraint a solver would
    trivially enforce from reading the statement (shape, size, and any structural
    rule that is obvious once stated). Used to measure P(random guess). Must not
    bias toward the planted answer. See G4 — do NOT sample from the naive space."""

def search_space(inst) -> int | None
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
| **G4 guess resistance** | `P(random guess) < 1e-6` from ≥200k samples, measured **structure-aware** (see below). Report hits/total. |
| **G5 sparse** | Where `enumerate_all` is feasible, solutions are a tiny fraction of `search_space`. |
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
- When a level is solved the harness escalates: to the next named preset, and once
  `DIFFICULTY` is exhausted, by calling your `escalate()`. After **3 escalations** — or
  as soon as `escalate()` returns None — it stops and reports `verdict: "too_easy"`.
- It writes `llm_loop_transcript.jsonl` itself, and records the master seed, the pool
  and its verdict in `.meta.json`. Do not write either file by hand; `submit.sh`
  validates their schema and will reject a hand-rolled one.

Read the verdict it prints:

- `{"verdict": "hardened", ...}` — `shipping_params` is the level that held. If it came
  from `escalate()` rather than a named preset, **add it to `DIFFICULTY` under a name**
  and point `SHIPPING_DIFFICULTY` at it, then re-run STEP 3's gates at that level.
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

- **What the family is**, in plain language. What object is handed to the solver,
  what they must find, and why checking an answer is cheap. Name the paper, link it.
- **Why it is hard.** The specific theorem and parameter regime you are inside, and
  — just as important — the easy regimes you had to avoid and the results that
  identify them. Cite sections by number. This is the part only you know.
- **A worked example.** A rendered instance small enough to read in full (use your
  smallest preset), its answer, `verify` returning True on it, and `verify`
  returning False with its reason on a corrupted variant.
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
