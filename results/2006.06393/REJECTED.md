# Rejection: arXiv:2006.06393

This paper does not yield a shippable family in this run. The attempted family
passes generation and exact verification, but it fails **H (hardness)** after
both tracks are considered.

## Step 0 result

Section 1 defines the native object as a machine--job hypergraph with machines
partitioned into two nonempty groups. An ordinary edge uses one machine and one
job; a group--job hyperedge uses every machine in that group and the job. The
same section notes that an empty group collapses to ordinary bipartite
multigraph edge coloring, so the attempted generator kept both groups nonempty
and included both edge types.

Track A is unavailable. Theorem 1 states that an optimal solution of the
paper's auxiliary LP can be made integral, and Section 13 explicitly obtains
the integral variables through network-flow models with integral lower and
upper bounds. Together with solving the displayed LP, this is a polynomial-time
algorithm for the full two-hypervertex optimization class. A hidden-coloring
plant therefore cannot be presented honestly as a distribution with no known
efficient general method.

## Attempted Track B family

The retained module inverse-generates a native schedule. It samples one
nonzero, pairwise-distinct modular offset per machine, constructs a proper
color class at a time, and erases the colors. A submitted offset vector expands
to the full coloring by

```
ordinary (h,j): color = j - s_h (mod n)
group (G,j):    color = j.
```

The checker expands that rule and checks machine/color and job/color uniqueness
exactly without reading the planted answer. Every machine has load `n`, so the
constructed `n`-coloring is optimal. Thus G and V pass by inverse construction
and exact inspection.

The efficient mechanical method for the bounded witness language is exhaustive
cyclic set correlation: for every machine, test all `n-1` possible translates
against all `n` residues. Its complexity is `O(m n^2 + E)`. At the hard preset
`n=53`, two groups of four machines, 26 hyperedges per group, and 268 total
operations, the retained reference implementation used **22,316 counted exact
operations** (22,048 set comparisons) and **0.00236 seconds** on this machine.
The broader paper method is the polynomial LP plus integral-network-flow route
of Theorem 1 and Section 13.

The compact route is the cyclic-translate invariant: a machine's missing
ordinary-job set is its group's hyperedge-job set shifted by `s_h`. Taking set
sums modulo `n` recovers each shift. At the hard preset this route costs **292
exact operations**, including reading/summing all 268 displayed incidences and
three modular operations for each of eight machines. The answer itself is only
eight integers (23 serialized characters for the measured seed). The compact
route is therefore fully executable in context, not merely shorter in theory.

## Hardening evidence and failed gate

`scripts/harden.py` tested the bare statement at all three non-demo presets.
Every call returned a witness accepted by the exact checker:

| preset | parameters | solved / attempts |
|---|---|---:|
| easy | `n=17`, group size 3, hyper-count 8 | 3 / 3 |
| medium | `n=37`, group size 4, hyper-count 18 | 3 / 3 |
| hard | `n=53`, group size 4, hyper-count 26 | 3 / 3 |

The pool included OpenAI GPT-5.6 Terra and Google Gemini 3.8 Flash at medium
reasoning effort. The script-owned verdict is `too_easy`; the complete per-call
records remain in `llm_loop_transcript.jsonl` and `.meta.json`.

Consequently the attempted family fails **H on Track B** as well: the intended
invariant is both discoverable and executable by no-tool solvers throughout the
allowed ladder. Escalating beyond the hard preset would push the intended route
past the 300-operation G9(c) cap while the witness stays short; the run's rule
for a `too_easy` verdict forbids hand-retuning after this result. This rejection
does not claim that certificates or verification are defective, and it does not
confuse the existence of a polynomial algorithm with a witness-rule failure.

The attempted generator is retained as `rejected_gen_2006_06393.py` so the
decision can be replayed.
