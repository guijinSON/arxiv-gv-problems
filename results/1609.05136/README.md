# arXiv 1609.05136 — exact promised-slot Consensus-Halving

Status: **parked (`cap_bound`), not rejected and not shipped**. The required bare
oracle ladder never found an all-fail level before the next fixed-length grid
increase would exceed the 2,000-character answer cap.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain / essentiality | optimization / native |
| Object regime / core | rational-exact / linear algebra |
| Certificate | rational normalized cut coordinates |
| Intuition | decomposition: common all-slot mass plus one permuted exceptional coordinate |
| Reduction | none |

## Problem and provenance

The source is Filos-Ratsikas, Frederiksen, Goldberg, and Zhang,
[“Hardness Results for Consensus-Halving”](https://arxiv.org/abs/1609.05136).
Section 2 defines valuations on an interval, cuts, `+/-` portions, and exact or
approximate balance; it explicitly permits step-function densities. This family
hands the solver those native objects. Each rational answer coordinate determines
one cut in a promised open slot, labels alternate from `+`, and `verify` integrates
every stated density exactly.

Theorems 1 and 2 in Section 3 prove PPAD-hardness for constant-error, reduction-
generated instances with `n` or `n+k` cuts. That is **not** a hardness claim about
this inverse-generated distribution. The slot promise linearizes this family, so
it is Track B. Dense exact Gauss-Jordan elimination is an `O(n^3)` reference
algorithm; at the named hard preset its median measured cost was 54,819 rational
field operations and 0.016 seconds. The compact route notices that every balance
row is a common all-slot sum plus one exceptional coordinate: derive 96 signed
targets, sum them, divide by 97, and subtract the common term, for 288 exact
operations.

## Worked demo

For `make_instance(n=2, q=3, seed=0)`, the rendered agent data are:

~~~text
A1: guard=0; special=1; L=7; R=26/3; C=1
A2: guard=1; special=0; L=7; R=17/3; C=1
~~~

The valid normalized coordinates are
`<answer>1/3, 2/3</answer>`, and `verify(inst, inst["answer"])` returns
`(True, "ok")`. Replacing the first coordinate by zero returns
`(False, "agent 1 is not balanced (exact discrepancy -1/3)")`. This two-agent
demo is hand-solvable: it is just two rational balance equations.

## Presets and gates

| Preset | Parameters | Oracle solved |
|---|---:|---:|
| demo | `n=2, q=3` | skipped; hand example |
| easy | `n=24, q=31` | 3/3 |
| medium | `n=48, q=127` | 3/3 |
| hard | `n=96, q=257` | 2/3 |
| escalated | `n=96, q=4,113` | 3/3 |
| escalated | `n=96, q=65,809` | 3/3 |
| escalated | `n=96, q=1,052,945` | 3/3 completed calls; one API error was redrawn |
| largest in-cap | `n=96, q=16,847,121` | 1/3 |

| Gate | Measured result |
|---|---|
| G1 | 12/12 planted witnesses verified and JSON-round-tripped |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | model-style fenced/prose response round-tripped |
| G4 | 0 hits / 200,000 structure-aware grid samples |
| G5 | demo: 1 solution / 25; shipping sample density 0/200,000; strongest failing attack 512 restarts, median 0.050 s |
| G6 | five attacks, 0/8 successes each; reference elimination 8/8 |
| G7 | doubled `n=192` instance builds and verifies |
| G8 | 80/80 key-invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | not run: the bare ladder never hardened, so hinted/placebo arms were not applicable |

At the largest in-cap level, the answer measured 1,876 characters (469 estimated
tokens), 192 atomic elements, and the intended route remained 288 operations.
The next fixed-length escalation, `q=269,553,937`, measured about 2,138 characters
(535 tokens), so the script-owned verdict is `cap_bound`. No `REJECTED.md` or G9
transcript is present by design.

## Use

~~~python
from gen_1609_05136 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
~~~

If the family is later reopened under a larger output cap, emit from the repository
root with `bash scripts/emit.sh 1609.05136 20`. It should not be submitted under
the current cap because `.meta.json` records `cap_bound`.

## Caveats

The family is efficiently solvable and makes no Track A or average-case PPAD
claim. Its difficulty is only the no-tool gap between generic elimination and a
short decomposition. Uniform G4 samples range-valid `1/q`-grid vectors and says
nothing about model priors or structural reasoning. Planted vectors are conditioned
to have distinct coordinates and nondegenerate row targets for reliable corruption
tests, while the declared answer language allows repeats; exploiting that generator
fact still leaves an enormous falling-factorial space, but G4 does not measure that
conditional prior. The panel did not test every symbolic linear-algebra heuristic;
the successful oracle calls already show that the decomposition itself is often
recognized. One final-rung failure was an empty length-limited reply, so it is not
strong mathematical evidence. Most importantly, the paper’s PPAD-hard theorem
applies to a different distribution and precision regime.
