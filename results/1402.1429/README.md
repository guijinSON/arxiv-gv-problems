# Exact cubic sign systems from arXiv:1402.1429

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | CSP/SAT |
| Certificate form | integer tuple (a sign vector) |
| Intended intuition | decomposition |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed: Section 4, equation (4.3), Lemmas 4.3–4.4, Theorem 4.1 |

This generator uses the exact factored cubic polynomial encoding in Stéphane
Gaubert and Zheng Qu, [*Checking the strict positivity of Kraus maps is
NP-hard*](https://arxiv.org/abs/1402.1429).  The solver receives rational
polynomials of the form `(1 ± xa)(1 ± xb)(1 ± xc)=0`, together with the exact
constraints `xj^2=1`, and must return one common sign-valued zero.  The checker
substitutes the proposed signs into every displayed polynomial using integers;
it neither reads the planted answer nor relies on the paper's theorem.

The construction is inverse generation.  It first samples a uniform sign on
each incidence of a connected cubic structure, derives the parity required at
each constraint, and expresses each parity by the four cubic clauses that forbid
the opposite-product assignments.  Clause order, factor order, and variable
labels are shuffled.  Thus every instance has a known witness without solving
it, and every variable has exactly balanced positive and negative literal
counts.

## Why Track B, not Track A

The paper's Theorem 4.1 proves worst-case NP-hardness by reducing 3SAT through
this polynomial system to unital bilinear feasibility; Lemma 4.1 then identifies
bilinear feasibility with failure of strict positivity, yielding Theorem 4.2.
That theorem says nothing about the average difficulty of an inverse-planted
distribution.  Claiming Track A here would therefore be unsupported.

For this generated subclass an efficient algorithm is known and implemented:
group the four polynomials having each common three-variable support, translate
signs to bits, and perform exact Gaussian elimination over GF(2).  Its generic
bound is `O(v*e*min(v,e))` coefficient XORs.  At the shipping preset it solved
8/8 instances, averaging approximately 0.0029 seconds, 63,392 coefficient XORs, 676 row
XORs, and 127 pivots.  Once the stronger structural insight is seen, every
variable occurs in exactly two parity groups: set non-tree variables to `+1`
and eliminate tree variables from leaves to root.  That route takes 256 exact
sign operations, but discovering the grouping and carrying it through 512
shuffled cubics is not mechanically executable in the no-tool context.  The
paper's easy-side result also matters: Corollary 3.1 proves that irreducibility
and primitivity are polynomial-time checkable, so neither is used as a hardness
claim.

## Worked demo (`n=4`, seed 5)

This is the complete rendered instance (the smallest supported setting is
genuinely hand-solvable):

```text
Find a common zero of the following exact polynomial system.

There are 6 variables x1,...,x6. Every variable must be a sign: xj is either -1 or +1 (equivalently, xj^2=1). Every displayed product is an ordinary polynomial over the rational numbers. A row is satisfied exactly when its integer value after substitution is zero. Row order and factor order carry no meaning. Variable indices are 1-based.

The 16 equations are:
  1: (1 - x5)(1 - x6)(1 - x3) = 0
  2: (1 - x3)(1 + x4)(1 + x2) = 0
  3: (1 - x6)(1 + x5)(1 + x3) = 0
  4: (1 - x5)(1 - x1)(1 - x2) = 0
  5: (1 + x6)(1 - x4)(1 + x1) = 0
  6: (1 + x5)(1 + x6)(1 - x3) = 0
  7: (1 + x2)(1 - x5)(1 + x1) = 0
  8: (1 - x6)(1 + x1)(1 + x4) = 0
  9: (1 + x1)(1 - x2)(1 + x5) = 0
  10: (1 - x6)(1 - x1)(1 - x4) = 0
  11: (1 + x2)(1 - x4)(1 + x3) = 0
  12: (1 + x6)(1 + x4)(1 - x1) = 0
  13: (1 + x3)(1 + x4)(1 - x2) = 0
  14: (1 - x3)(1 - x4)(1 - x2) = 0
  15: (1 + x2)(1 + x5)(1 - x1) = 0
  16: (1 + x3)(1 + x6)(1 - x5) = 0

Return exactly one sign for each variable, in the order [x1,x2,...,x6]. Use a JSON list containing only the integers -1 and 1; order matters and no entry may be omitted or repeated.

Give your final answer inside <answer></answer> tags, as the JSON list just specified.
Example of the required syntax: <answer>[1,-1,1]</answer>
Output nothing else inside the tags.
```

The planted answer is `[-1,-1,-1,1,1,-1]`.
`verify(inst, answer)` returns `(True, "ok")`; deleting its final sign returns
`(False, "answer has 5 signs; expected 6")`.  A person can solve the demo on
paper by grouping equal supports into four parity equations and eliminating.

## Difficulty presets

| Preset | parity groups `n` | sign variables | cubic equations | status |
|---|---:|---:|---:|---|
| demo | 4 | 6 | 16 | hand example; harden skips it |
| easy | 32 | 48 | 128 | rejected by oracle: 2/3 solved |
| medium | 64 | 96 | 256 | rejected by oracle: 1/3 solved |
| **hard** | **128** | **192** | **512** | **ships; 0/3 solved** |

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 planted verifies | pass | 12/12 across all presets |
| G2 corruption | pass | 5/5 rejected with 5 distinct reasons |
| G3 round trip | pass | tagged JSON recovered through prose/fences |
| G4 guessing | pass | 0/200,000 uniform sign vectors; exact density is `2^-127` |
| G5 density/cost | pass | `2^65` valid of `2^192`; 256-restart attack averaged about 0.0026 s |
| G6 adversaries | pass | five attacks, each 0/8; reference algorithm 8/8 |
| G7 scaling | pass | doubled build has 384 variables and verifies |
| G8 canonical key | pass | 140/140 relabelings invariant and real; 20/20 unrelated keys distinct |
| G9 no-tool | pass | 577 worst-case chars, 145 estimated tokens, 192 elements, 256 operations |

The five failing G6 attacks were literal-balance/outlier scoring, greedy repair
of the first violated cubic, a single parity-repair sweep, an alternating-sign
ansatz, and 256 uniform random restarts.  Plants and free variables use the same
uniform sign distribution; there is no planted magnitude or frequency outlier.

## Bare oracle loop

| Preset | Seed | Model | Result | Reason |
|---|---:|---|---|---|
| easy | 1530123837 | Gemini 3.1 Pro | failed | submitted vector violated equation 25 |
| easy | 990969744 | Grok 4.6 | solved | verified |
| easy | 197415052 | Claude Sonnet 5 | solved | verified |
| medium | 777574515 | Claude Sonnet 5 | failed | exhausted 32k completion budget with no answer |
| medium | 1041929613 | Gemini 3.1 Pro | solved | verified |
| medium | 754921098 | GPT-5.6 Terra | failed | submitted vector violated equation 6 |
| hard | 345941182 | Grok 4.6 | error | 900-second timeout; excluded and redrawn |
| hard | 1023396350 | GPT-5.6 Terra | failed | returned 258 signs, expected 192 |
| hard | 162693659 | Gemini 3.1 Pro | failed | submitted vector violated equation 20 |
| hard | 1276598529 | Claude Sonnet 5 | failed | exhausted 32k completion budget with no answer |

The official verdict is `hardened` at `hard` after two escalations.  The Grok
timeout is not counted as a failure.

## G9 controlled arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

The hinted and placebo arms used the same master seed, models, and instance
seeds.  Hinted minus placebo is `0.0`: in these three trials, explicitly naming
the decomposition and tree elimination bought no measured solve-rate gain.  The
worst-case answer has 577 serialized characters (145 estimated tokens), 192
atomic signs, and the intended route uses 256 exact sign operations.

## Use

```python
import gen_1402_1429 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit fresh canonical-key-distinct instances with:

```bash
bash scripts/emit.sh 1402.1429 20 hard
```

## Caveats

This is deliberately not a Track A family.  Software that recognizes the four
clauses per support solves it quickly by GF(2) elimination, and recognition of
the incidence structure gives an even faster tree construction.  The solver is
shown the paper's polynomial intermediate, not Kraus operators themselves; the
coverage claim is the paper-licensed Section 4 reduction, not native Kraus-map
strict positivity.

The `P(guess)` figure is for the statement-visible prior of uniform full sign
vectors.  It accurately incorporates the sign alphabet and answer length, but
does not model a solver that has discovered the parity structure.  The panel did
not run an industrial CDCL/XOR solver, a Gröbner-basis package, or learning-based
structure recovery; this omission does not hide a Track A claim because the
successful exact Gaussian and tree solvers are reported explicitly.  One bare
and one hinted Claude failure were empty length-limited responses, so those rows
are weaker evidence than a parsed wrong witness; the other two shipping vendors
returned concrete invalid vectors in each relevant arm.

Finally, `canonical_key` uses exact individualized color refinement of the
recovered uncharged cubic incidence graph.  It is invariant under variable
renumbering, equation/factor reordering, and independent sign-domain switches,
and passed all reported tests, but it is not a complete general graph-isomorphism
canonizer.  A rare non-isomorphic collision is therefore possible.
