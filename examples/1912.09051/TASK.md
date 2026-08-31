> **Historical copy — pre-`harden.py` rules.** This is the prompt as it stood when
> this example was built: a single fixed oracle, a builder-written hardening loop, and
> a seven-function interface. The current prompt is `prompts/codex_task.md`, where the
> loop belongs to `scripts/harden.py` and the module must also supply `canonical_key`
> and `escalate`. Read this for the worked result, not for the instructions.

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
    """A uniformly random SYNTACTICALLY valid candidate (right shape, right size).
    Used to measure P(random guess). Must not bias toward the planted answer."""

def search_space(inst) -> int | None
    """Size of the naive candidate space, or None if not countable."""

def enumerate_all(inst) -> int | None
    """Exact count of valid answers by brute force; None if the space is too big.
    Cap the work — return None rather than hanging."""
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
| **G4 guess resistance** | `P(random guess) < 1e-6`, measured by sampling ≥200k `random_candidate`s. Report hits/total. |
| **G5 sparse** | Where `enumerate_all` is feasible, solutions are a tiny fraction of `search_space`. |
| **G6 adversary panel** | Write ≥3 cheap attacks and confirm each FAILS across ≥8 seeds. See below. |
| **G7 scales** | Difficulty grows with `n`; a size-doubled instance still builds and still passes G1. |

### G6: the adversary panel — this is where generators actually die

A planted instance can pass every correctness gate and still be trivial, because
the planting leaves a statistical signature. **Write attacks that exploit how you
built it**, and prove they fail. At minimum:

- **Outlier attack** — is the planted element distinguishable by any per-element
  statistic? Position, magnitude, width, degree, frequency, ordering.
- **Greedy attack** — does an obvious greedy/left-to-right rule solve it?
- **Random restart** — does sampling with a mild heuristic find a solution?

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

**Draw plants and decoys from the SAME distribution.** Get difficulty from
crowding/density/size, never from making the planted object look different.

---

## STEP 4 — the LLM hardening loop (required)

An OpenRouter API key is in the file `.orkey` in your working directory. Use it to
check the instance actually defeats a strong model.

    POST https://openrouter.ai/api/v1/chat/completions
    Authorization: Bearer <contents of .orkey>
    body: {"model":"openai/gpt-5.6-terra", "reasoning":{"effort":"medium"},
           "messages":[{"role":"user","content":render(inst)}], "max_tokens":16000}
    the reply text is choices[0].message.content

```
for preset in ascending difficulty:
    inst  = make_instance(**preset, seed=<fresh>)
    reply = ask gpt-5.6-terra, reasoning effort "medium", with render(inst)
    ans   = parse_answer(reply)
    if ans is not None and verify(inst, ans)[0]:
        -> TOO EASY. escalate (raise n / f / density / crowding) and repeat.
    else:
        -> record this preset as the shipping difficulty.
```

Requirements:

- Model `openai/gpt-5.6-terra`, **reasoning effort medium**. If the `reasoning`
  field is rejected, retry without it and say so in your report.
- Try **at least 3 distinct seeds** per preset. One failure to solve is not evidence;
  3/3 failures is weak evidence and that is all we are claiming.
- Log the raw reply for each attempt. If `parse_answer` returns None on a reply that
  visibly *contains* an answer, that is a **G3 bug in your renderer** — fix the
  contract, do not celebrate a false negative.
- If the model solves even the hardest preset you can construct, report the family
  as **too easy** rather than shipping it.

---

## STEP 5 — deliverables

1. `gen_<arxiv_id>.py` — the module.
2. `selftest()` output: every gate with its measured number (P(guess) as hits/total,
   solution counts, per-attack results).
3. The LLM loop transcript: preset, seed, whether solved, and the final shipping
   difficulty.
4. One worked example: the rendered question, the answer, and `verify` returning
   True on it plus False on a corrupted variant.
5. A short `NOTES` block: which paper section fixed the definition, which result
   told you what makes it easy, and what you did to defeat each attack.

## Report honestly

If the family fails, say which gate and why. A rejected family costs nothing; a
family that silently generates easy or unsolvable instances poisons the dataset.
Never report a gate as passing without the number that shows it.
## PAPER

arXiv id: 1912.09051
url: https://arxiv.org/abs/1912.09051
title: On the hardness of finding normal surfaces
categories: cs.CG cs.CC

Prior triage (a hypothesis, not ground truth - verify it against the paper):
  family: topological structures
  method: structural scan
  candidate generator: construct triangulation encoding a known normal surface witness
  candidate verifier: check normal coordinates, matching constraints, and required topological type
