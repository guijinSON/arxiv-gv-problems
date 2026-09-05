# Cyclic-XOR binary CSP generator — arXiv:0911.0801

| profile field | value |
|---|---|
| Track | B — no-tool compression |
| Native domain / object regime | logic / finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer tuple of primary CSP values |
| Native objects | domain-3 binary CSP, explicit binary relation tables, primary and selector variables |
| Intended intuition | invariant: repeated clause neighborhoods encode XOR, and pair-sharing scopes contain a cyclic recurrence |
| Domain essentiality / reduction | native / paper-licensed by Section 7, Lemma 7.4 |

## What the family is

Dániel Marx’s [*Tractable hypergraph properties for constraint satisfaction and conjunctive queries*](https://arxiv.org/abs/0911.0801) defines a CSP as variables over a common domain with every constraint relation listed extensionally (Definition 2.1). Section 7, Lemma 7.4 converts a 3-CNF formula into an equivalent domain-3 binary CSP: each clause receives a selector variable whose value identifies a true literal.

This generator samples a Boolean vector first. It builds a uniquely solvable cyclic 3-XOR system around that vector, adds compatible pair-disjoint XOR equations as crowding, compiles each XOR into four 3-CNF clauses, and applies Lemma 7.4. The solver receives only the resulting binary CSP. Its answer gives values 1/2 for the primary variables; the checker locally assigns each selector its smallest feasible value and checks every binary relation by exact table membership. Generation never solves an emitted instance.

## Why Track B, not Track A

The paper’s Theorem 1.1 places bounded-arity, bounded-treewidth CSP in the polynomial-time regime. Theorem 4.1 gives an FPT algorithm for bounded submodular width, while Theorem 7.1 and Corollary 7.2 give ETH-based hardness only for recursively enumerable classes of unbounded submodular width. None of those results proves that an arbitrary planted distribution is hard.

This distribution has a known polynomial algorithm and therefore cannot be Track A. Group the four clauses on each three-primary scope into an XOR row, then run Gaussian elimination over GF(2). Its complexity is O((n+d)n²), where d is the number of extra equations. The recorded hard instance used 118,815 exact inspections/field operations and 0.232359 seconds; the eight-seed panel solved 8/8.

The compact route is different. Scopes sharing a variable pair form one cycle; extra scopes are isolated in that overlap graph. Along the cycle, the homogeneous recurrence has period three. A particular recurrence pass, two wraparound equations, and the period-three correction use at most 280 XORs at hard. Recognizing this representation is the intended no-tool insight.

## Worked demo

The demo preset at seed 7 is hand-solvable: group the 20 selectors into five four-clause XOR blocks, order the five pair-sharing scopes cyclically, and check the four possible starting pairs.

~~~text
Find a compact witness for the following finite binary constraint satisfaction problem (CSP).

A binary CSP has variables taking values in a finite domain.  A constraint
'u v R' is satisfied exactly when the ordered pair (value(u), value(v))
appears in the explicitly listed binary relation R.  Every constraint must
be satisfied.  Here the common domain is exactly {1, 2, 3}.

There are 5 primary variables and 20 selector variables.
For a primary variable, value 1 means Boolean true and value 2 means Boolean false;
your answer may not give a primary the value 3.

Relation tables (row order has no meaning):
  R1a: (2,2) (3,2) (1,3) (1,2) (3,3) (2,3) (1,1)
  R1b: (1,3) (2,1) (3,2) (1,2) (2,2) (3,3) (2,3)
  R2a: (3,1) (3,3) (1,1) (2,1) (1,3) (1,2) (2,3)
  R2b: (2,2) (3,1) (1,1) (1,3) (3,3) (2,1) (2,3)
  R3a: (1,2) (2,1) (3,2) (3,1) (2,2) (1,1) (1,3)
  R3b: (1,1) (2,1) (3,1) (3,2) (2,2) (1,2) (2,3)

Primary variables in the exact answer order:
  X60631 X168176 X349563 X424002 X692554

Binary constraints; each line is 'first-variable second-variable relation':
  X60631 Y00001_170298cd R3a
  X692554 Y00015_228d5ec0 R3a
  X349563 Y00009_0504be4b R2a
  X60631 Y00011_2828e0e6 R3a
  X60631 Y00010_09ef77c3 R3b
  X424002 Y00020_2c6aab1e R1a
  X692554 Y00006_095ea567 R1a
  X60631 Y00005_24db2504 R2a
  X168176 Y00002_1f3e8dfd R1a
  X424002 Y00012_2b892121 R1a
  X692554 Y00016_3caf4114 R3b
  X692554 Y00013_08cd3968 R3b
  X692554 Y00003_0a7a399f R2b
  X692554 Y00008_35850c74 R1b
  X168176 Y00003_0a7a399f R1a
  X349563 Y00008_35850c74 R3b
  X424002 Y00019_31619d27 R1b
  X692554 Y00005_24db2504 R1a
  X424002 Y00011_2828e0e6 R1b
  X168176 Y00014_0bfaf41b R2b
  X692554 Y00001_170298cd R2b
  X349563 Y00007_0f1cc788 R3a
  X349563 Y00010_09ef77c3 R2a
  X168176 Y00018_246da057 R3b
  X349563 Y00017_390ac1b8 R2b
  X692554 Y00002_1f3e8dfd R2a
  X692554 Y00004_266e902a R2a
  X349563 Y00012_2b892121 R2b
  X60631 Y00007_0f1cc788 R2b
  X424002 Y00013_08cd3968 R1a
  X349563 Y00019_31619d27 R2a
  X168176 Y00017_390ac1b8 R3a
  X424002 Y00015_228d5ec0 R1b
  X424002 Y00014_0bfaf41b R1a
  X692554 Y00007_0f1cc788 R1b
  X60631 Y00006_095ea567 R2b
  X424002 Y00017_390ac1b8 R1b
  X168176 Y00013_08cd3968 R2a
  X349563 Y00011_2828e0e6 R2b
  X168176 Y00001_170298cd R1b
  X692554 Y00014_0bfaf41b R3a
  X168176 Y00016_3caf4114 R2b
  X424002 Y00018_246da057 R1a
  X60631 Y00004_266e902a R3b
  X60631 Y00002_1f3e8dfd R3a
  X168176 Y00004_266e902a R1b
  X349563 Y00005_24db2504 R3a
  X424002 Y00009_0504be4b R1a
  X168176 Y00015_228d5ec0 R2a
  X60631 Y00008_35850c74 R2a
  X60631 Y00009_0504be4b R3a
  X424002 Y00016_3caf4114 R1b
  X349563 Y00020_2c6aab1e R2a
  X168176 Y00020_2c6aab1e R3a
  X424002 Y00010_09ef77c3 R1b
  X349563 Y00018_246da057 R2b
  X60631 Y00003_0a7a399f R3b
  X168176 Y00019_31619d27 R3b
  X349563 Y00006_095ea567 R3b
  X60631 Y00012_2b892121 R3b

Certificate convention: output values only for the primary variables, in the
displayed order.  The checker extends them deterministically.  For each selector
Y independently, it tries selector values 1, then 2, then 3, and assigns Y the
smallest value for which all three constraints incident with Y are satisfied.
If no such value exists, the proposed primary assignment is invalid.  The checker
then verifies every listed binary constraint by exact table membership.

Your answer must therefore be a JSON list of exactly 5 integers,
each equal to 1 or 2.  Order matters and repeats are allowed.
Give your final answer inside <answer></answer> tags, as that JSON list.
Syntax-only example (not the required length): <answer>[1,2,1,1,2]</answer>
Output nothing else inside the tags.
~~~

The answer is <answer>[2,2,2,1,1]</answer>, and verify returns (True, "ok"). Dropping the last entry returns (False, "wrong answer length: expected 5, got 4").

## Presets

| preset | primary n | extra equations | selectors | binary constraints | reference operations at seed 20260905 | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 5 | 0 | 20 | 60 | 136 | hand example |
| easy | 17 | 8 | 100 | 300 | 1,903 | solved by 2/3 oracle attempts |
| medium | 41 | 40 | 324 | 972 | 14,547 | 2/2 completed attempts failed; third unavailable |
| hard | 83 | 160 | 972 | 2,916 | 118,815 | configured shipping preset; local gates pass, oracle unmeasured |

After the named ladder, escalate() doubles extra equations at fixed 83-value answer length before considering any longer witness.

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted witnesses verify; 16/16 JSON round-trips |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 3/3 prose/fenced responses round-trip; garbage rejected |
| G4 | 0/200,000 guesses; exact declared space 2^83 = 9,671,406,556,917,033,397,649,408 |
| G5 | shipping density estimate 0/200,000; construction proves one solution; exact easy count 1; baseline 118,815 operations / 0.232359 s |
| G6 | four attacks each 0/8; Gaussian reference 8/8, operation range 102,520–117,674 |
| G7 | n=166,d=320 builds and verifies; fixed-length escalation to n=83,d=320 verifies |
| G8 | 100/100 individual/composed transformed keys invariant, 100/100 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | 249 characters, 63 estimated tokens, 83 atoms, 280 intended exact operations |

## Oracle loop and G9 diagnostics

The required script-owned bare run began successfully but exhausted the OpenRouter key before a level held. API errors are not failures, so there is no honest hardened verdict and this directory is not submission-complete.

| preset | model | seed | result |
|---|---|---:|---|
| easy | OpenAI GPT-5.6 Terra | 804501758 | solved |
| easy | Google Gemini 3.8 Flash | 786800680 | solved |
| easy | OpenAI GPT-5.6 Terra | 574681827 | invalid witness |
| medium | OpenAI GPT-5.6 Terra | 1119067490 | invalid witness |
| medium | Google Gemini 3.8 Flash | 572182487 | invalid witness |
| medium | OpenAI GPT-5.6 Terra | four redraw seeds | HTTP 403 quota errors; not attempts |

Both shipping-preset G9 scratch runs also received four HTTP 403 redraw errors before any valid attempt.

| arm | solved / valid attempts | conclusion |
|---|---:|---|
| bare | 0/0 at shipping | unavailable after quota exhausted during the ladder |
| structural hint | 0/0 | unavailable; four error redraws preserved |
| placebo hint | 0/0 | unavailable; four error redraws preserved |

Hinted minus placebo is stored as 0.0 only because both denominators are absent; it is not evidence that the hint helped or failed to help. G9(c) passes independently.

## Use

~~~python
import json
import gen_0911_0801 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
statement = g.render(inst)
answer = g.parse_answer(
    "<answer>" + json.dumps(inst["answer"], separators=(",", ":")) + "</answer>"
)
assert g.verify(inst, answer) == (True, "ok")
~~~

From the repository root:

~~~bash
bash scripts/emit.sh 0911.0801 20
~~~

When quota is restored, rerun python3 ../../scripts/harden.py gen_0911_0801.py here, then run the structural and placebo modes in separate scratch directories.

## Caveats

This family is easy with code; that is the Track B premise. It tests discovery of generator-specific XOR/cycle structure, not the paper’s ETH hardness theorem or average-case CSP hardness. Pair-disjoint extra equations make the useful cycle detectable once the correct overlap representation is considered.

The 0/200,000 result uses the exact declared prior—uniform vectors in {1,2}^83. It does not model a solver that learns the generator or recognizes XOR. The panel did not run an industrial SAT/SMT package or a learned structure detector; Gaussian elimination is the simpler successful specialist algorithm for this distribution.

The hard rendering is about 89,734 characters. Although its answer and exact arithmetic route meet G9(c), failures may partly reflect relation scanning and bookkeeping. The canonical key is complete for generated instances but not a general binary-CSP isomorphism algorithm. Most importantly, the external oracle evidence is incomplete: local correctness and attack gates pass, but hardness is not yet verified by STEP 4.
