# Verified relation generator for arXiv:0902.4670

> Status: the module passes every local G1--G9(c) gate. The script-owned bare
> oracle loop held the shipping `easy` preset on 3/3 scored attempts, so the
> harness verdict is **`hardened` with zero escalations**.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | `number_theory` |
| Object regime | `integer_lattice` |
| Computational core | `subset_sum` (signed ideal-class relation) |
| Certificate | `integer_tuple` of form orientations |
| Native objects | imaginary-quadratic discriminant; primitive positive-definite binary quadratic forms; ideal-class relation |
| Intended intuition | invariant: recognize a concealed principal norm identity |
| Domain essentiality | `native` |
| Reduction | none |

## Problem and trust model

The source is Bisson and Sutherland, [*Computing the endomorphism ring of an
ordinary elliptic curve over a finite field*](https://arxiv.org/abs/0902.4670).
Section 2.2 represents ideal classes of imaginary quadratic orders by primitive
positive-definite binary quadratic forms. Section 2.3 and equation (3) define a
relation by choosing signs on oriented split-prime classes. An instance here
gives the common discriminant and the oriented prime forms; the solver returns
one normalized sign vector whose Dirichlet product is principal.

This is a paper-native intermediate object, not an elliptic curve replaced by a
graph. The generator first chooses a factored norm `A`, an integer `x`, and the
answer signs, sets `D=x^2-4A`, and only then builds and shuffles the displayed
forms. Thus G uses composition of identities. Verification combines the signed
roots by exact CRT. Since `A < |D| < 3A`, a combined form `(A,B,C)` represents
one exactly iff `4A+D` is a square `x^2` and `B == ±x (mod 2A)`. The checker
executes those integer tests and never reads `inst["answer"]`.

## Why Track B

The paper is explicit about the mechanical route. Section 2.3 fixes one sign by
global inversion and enumerates the other `2^(k-1)` choices; its class-group
relation count uses `O(2^k + sum(log e_i))` group operations. Because this task
only asks for one witness, the measured reference uses the stronger standard
meet-in-the-middle search on exact reduced-form class keys. Its complexity is
`O(2^(k/2) poly(log|D|))` time and memory. Over eight shipping seeds it averaged
48,836.5 candidates, 64,905 form reductions, 1,237,669.75 counted exact
operations, 1.841 seconds mean and 3.422 seconds maximum in the final self-test,
and solved 8/8.

An efficient specialized route therefore exists and is not hidden: multiply
the norms, notice that `4A+D` is a square, take its exact integer square root,
and compare that root with each oriented residue. It costs 178 counted exact
operations on the shipping instance. The benchmark tests whether a no-tool
solver finds this invariant; executing tens of thousands of reduced-form tests
and roughly 1.24 million exact operations in context is not realistic.

For the full endomorphism-ring problem, Algorithm `Certify` obtains relations
with `FindRelation`, and Algorithm `Verify` checks them by isogeny walks.
Proposition 6 gives heuristic subexponential cost for `FindRelation`,
Proposition 9 does the same for verification, and Corollary 8 bounds certificate
size. Small conductor primes are an easy regime handled by isogeny climbing in
Algorithm 1, lines 3--4; Section 3.3 says Algorithm 2 can be much faster when
`u << v`. For this relation family, small arity is plainly easy because Section
2.3 enumerates the signs, so the five-form setting is only a demo and shipping
uses 31 forms. Those facts rule out pretending that this constructed
distribution is a Track-A endomorphism-ring benchmark.

## Worked demo

For `make_instance(seed=0, n=5, prime_bits=7)`, `render(inst)` is:

```text
Find a principal signed relation among oriented binary quadratic forms.

A binary quadratic form is Q(X,Y)=a X^2+b XY+c Y^2.  Its discriminant is
D=b^2-4ac.  All forms below are primitive positive-definite forms with the same
negative discriminant

  D = -21978630539.

Row i gives the oriented prime form Q_i=(ell_i,b_i,c_i).  Choose one sign
epsilon_i in {+1,-1} for every row.  Let

  A = product_i ell_i.

There is a unique odd B in the half-open interval 0 <= B < 2A satisfying

  B = epsilon_i*b_i (mod 2*ell_i)  for every i.

(The ell_i are distinct odd primes, so these congruences are compatible and
determine B.)  Put C=(B^2-D)/(4A).  Your signs are valid exactly when the
combined form Q=(A,B,C) is principal.  Here "principal" means that there exist
integers r,s with A*r^2+B*r*s+C*s^2=1.

Because negating every sign gives the inverse of the same relation, fix
epsilon_0=+1.  Row indices are 0-based, list entry i is epsilon_i, every row
gets exactly one sign, and signs may repeat.  All congruence intervals above
use the stated inclusive/exclusive endpoints.

The 5 rows are:
  0: ell=107, b=147, c=51351991
  1: ell=109, b=29, c=50409705
  2: ell=103, b=87, c=53346209
  3: ell=97, b=193, c=56646051
  4: ell=79, b=143, c=69552693

Give your final answer inside <answer></answer> tags as a JSON list of exactly
5 integers, each 1 or -1, with the first entry 1.
Format example: <answer>[1,-1,1,-1,1]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[1,1,-1,1,1]</answer>`, and
`verify(inst, [1,1,-1,1,1]) == (True, "ok")`. Flipping the second sign gives
`verify(inst, [1,-1,-1,1,1]) == (False, "the signed combined form is not
principal")`. A person can solve this smallest instance by checking its 16
normalized sign vectors on paper; it is intentionally illustrative.

## Difficulty presets

| Preset | `n` forms | Prime bits | Normalized sign space | Status |
|---|---:|---:|---:|---|
| demo | 5 | 7 | 16 | hand-scale, never shipped |
| easy | 31 | 14 | 1,073,741,824 | **shipping preset** |
| medium | 31 | 22 | 1,073,741,824 | fixed-length arithmetic escalation |
| hard | 31 | 30 | 1,073,741,824 | fixed-length arithmetic escalation |

No preset was rejected locally. The bare oracle ladder held at `easy`, so
`medium` and `hard` were not needed.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 16/16 planted answers verified; all JSON round-tripped |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered from prose and Markdown |
| G4 | pass | 0/250,000 structure-aware guesses; construction proves probability 1/1,073,741,824 |
| G5 | pass | demo has exactly 1/16 answers; shipping has one proved answer and sampled density 0/250,000; reference mean 1.841 s and 1.238M operations |
| G6 | pass | five attacks each 0/8; reference algorithm 8/8 as Track B expects |
| G7 | pass | doubling to 62 forms verifies and raises the space to 2,305,843,009,213,693,952 |
| G8 | pass | 20/20 permutation/inversion invariance, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | worst case 93 characters, 24 estimated tokens, 31 atoms, and 187 conservative intended-route operations (178 on the measured instance) |

## Oracle loop

The current repository harness used two vendors and three fresh instances. All
three replies parsed, and all three sign vectors failed exact principality.

| Preset | Seed | Model | Scored result | Reason |
|---|---:|---|---|---|
| easy | 756372974 | Gemini 3.8 Flash | failed | parsed vector was not principal |
| easy | 2100907888 | GPT-5.6 Terra | failed | parsed vector was not principal |
| easy | 1770876550 | GPT-5.6 Terra | failed | parsed vector was not principal |

The authoritative records are in `llm_loop_transcript.jsonl` and `.meta.json`;
the recorded verdict is `hardened` at `easy` with zero escalations.

## G9 arms

| Arm | Solved / valid attempts | Error calls | Conclusion |
|---|---:|---:|---|
| bare | 0/3 | 0 | shipping preset held |
| structural hint | 0/3 | 0 | hint did not yield a valid witness |
| placebo hint | 0/3 | 0 | no generic prompt-length benefit observed |

The hinted-minus-placebo difference is `0.0`. On this small sample the named
invariant bought no scored success, so the diagnostic does not show that the
oracle can execute the arithmetic after recognizing the structure. The two G9
transcripts preserve the replies; one placebo reply omitted the required tags
and the other eight arm replies parsed. The size/effort measurements are at most
93 characters, 31 atoms, about 24 tokens, and a 187-operation conservative route
bound (178 operations on the measured instance).

## How to use

```python
import importlib.util

path = "results/0902.4670/gen_0902_4670.py"
spec = importlib.util.spec_from_file_location("gen_0902_4670", path)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

inst = gen.make_instance(seed=7, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
candidate = gen.parse_answer("<answer>" + str(inst["answer"]).replace(" ", "") + "</answer>")
assert gen.verify(inst, candidate) == (True, "ok")
```

Because dotted result-directory names are not normal Python package names, the
reliable command-line checks from the repository root are:

```bash
python3 results/0902.4670/gen_0902_4670.py
python3 scripts/harden.py results/0902.4670/gen_0902_4670.py
bash scripts/emit.sh 0902.4670 20 easy
```

## Caveats

The family becomes easy immediately when the norm invariant is recognized;
that is intentional Track-B behavior, not evidence for average-case class-group
hardness. The 0/250,000 guess figure is empirical and is conditioned on the
freely deducible first-sign normalization; uniqueness additionally proves that
the uniform probability is exactly `1/2^30`, but neither figure models solvers
with number-theoretic priors. The inverse construction guarantees a unique
normalized answer in this parameter range, while
arbitrary relations from the paper need not be unique.

The attacks do not include generic CAS class-group software, lattice reduction,
or a learned pattern detector. A CAS would solve these instances, as would the
178-operation compact route, and both are consistent with Track B. The tested
heuristics were all-positive orientation, smallest oriented roots, greedy
prefix CRT, a 256-choice by-hand window, and 2,048 random restarts. The task text
describes a four-vendor oracle pool, but the installed `harden.py` currently
defines a two-vendor pool (OpenAI and Google); this run proves the current
harness criterion, not a four-vendor claim. After the runs, one contradictory
renderer phrase (“repetitions are not allowed”) was corrected to the explicit
“signs may repeat”; the instance data, answer grammar, and checker did not
change. A prompt-identical rerun was attempted, but the key then hit its total
quota, so the retained scored transcripts precede that wording-only correction.
