# Affine-XOR extraction from tree ensembles

Trust status: the generator and all deterministic gates pass, but the required oracle loop is **incomplete**. The script-configured two-vendor pool solved all five valid calls (easy 3/3, medium 2/2); OpenRouter then returned HTTP 403 “key limit exceeded” on the remaining medium retries, before `hard` was tested. The three shipping-preset G9 arms likewise contain only API errors. These errors are retained but never counted as model failures, so there is no hardness verdict yet.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | logic |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate | integer tuple (a fixed-order Boolean input, serialized as a bit string) |
| Intuition | change of variables: repeated four-tree blocks are affine XOR equations on public binary-vector tags |
| Domain essentiality | native |
| Reduction | paper-licensed: Section 6, Theorem 1 |

## What the family asks

The source is Huang, Zhao, and Huang, [“Embedding and Extraction of Knowledge in Tree Ensemble Classifiers”](https://arxiv.org/abs/2010.08281). Section 2 defines decision-tree paths and ensemble voting. Section 6, Eq. (10), asks for an input (x') within an (L_0) budget of a training input that traverses a suspected target joint path. Theorem 1 proves NP-completeness by making one decision tree for every 3-SAT clause and adding one fewer constant-False tree; the ensemble votes True exactly when every clause tree accepts.

An instance here contains those same objects: Boolean features, three-test clause trees, constant-False trees, an all-zero baseline, and the full-feature (L_0) budget used by the theorem’s reduction. The solver returns any fixed-order input bit string that makes the ensemble vote True. `verify` checks its shape, exact Hamming distance, every literal path, and the exact integer majority. It never reads `inst["answer"]`.

Generation is inverse. The generator first samples a quadratic Boolean form $q$ and a linear form $\ell$ on the nonzero vectors of $\mathbb F_2^d$. It retains the input $q(v)\oplus\ell(v)$, creates identities on triples $(u,v,u\oplus v)$, compiles each identity into four 3-CNF clause trees, and shuffles feature and tree order. The certificate is known before the forest exists. `render` groups trees with the same three tested features and canonicalizes only their display order; every parenthesized tree remains a separate vote.

## Why Track B

This is not a Track-A claim. The paper’s exact general extraction method uses SMT, and Theorem 1 establishes NP-completeness; Section 6.1 also warns that the joint-path disjunction may be exponential. On this promised affine distribution, however, four-tree XOR recognition followed by GF(2) Gaussian elimination is polynomial, $O(en^2)$ in the counted bit-operation model. It solved 8/8 shipping instances at an average **1,140,137 scalar bit operations** and **0.0040 s** per instance in the retained final run. A separate domain-standard DPLL solver with unit propagation also solved 8/8: **65,873 clause scans**, eight search nodes, and **0.0198 s** per instance on average.

The compact route is different: assign the seven basis-tagged features zero and use the compulsory tagged identities in increasing Hamming weight. Each of the other 120 features costs two binary XORs, for exactly **240 XORs**. The challenge is recognizing that change of variables in a 635-block, 2,540-tree forest without a sandbox. The paper’s PTIME embedding Algorithms 1–2 are therefore not used as a false Track-A hardness claim. Its loss/activation outlier methods in Section 6.2 are only prefilters and are explicitly allowed to produce false alarms.

## Worked demo

This is `make_instance(n=7, equation_factor=1, seed=7)` rendered in full:

```text
Knowledge extraction from a Boolean tree ensemble

There are 7 Boolean input features x_0,...,x_6.  A candidate input is
a bit string z of length 7; its character at zero-based position i is x_i.
The features also have the following public, fixed 3-bit vector tags.  Angle
brackets delimit a tag and are not part of the feature value:
  x_0=<010>  x_1=<111>  x_2=<011>  x_3=<101>  x_4=<001>  x_5=<110>  x_6=<100>

The ensemble contains the 28 clause trees listed below and
27 additional constant-False trees.  In a clause
tree, +j means the literal x_(j-1)=1 and -j means x_(j-1)=0; signed feature
numbers are therefore one-based even though bit-string positions are
zero-based.  A listed tree tests its three literals from left to right, returns
True immediately when a literal is true, and returns False if all three are
false.  Reordering the three tests would not change that tree's Boolean
function.  The complete ensemble returns the label with a strict majority of
votes.  Its total number of trees is odd, so there is no tie.

For compact display, each B-line groups the four separate clause trees that
test the same three features.  Parentheses delimit individual trees and the
vertical bar separates them; every parenthesized tree contributes one vote.
The angle-bracket header repeats those features' public tags in increasing
binary order.  Blocks are ordered lexicographically by their tag triples.
Grouping and ordering are presentation only and do not add a vote or constraint.

Clause-tree blocks:
  B_0 <001,010,011>: (+5 +1 +3) | (+5 -1 -3) | (-5 +1 -3) | (-5 -1 +3)
  B_1 <001,100,101>: (+5 +7 +4) | (+5 -7 -4) | (-5 +7 -4) | (-5 -7 +4)
  B_2 <001,110,111>: (+5 +6 -2) | (+5 -6 +2) | (-5 +6 +2) | (-5 -6 -2)
  B_3 <010,100,110>: (+1 +7 -6) | (+1 -7 +6) | (-1 +7 +6) | (-1 -7 -6)
  B_4 <010,101,111>: (+1 +4 +2) | (+1 -4 -2) | (-1 +4 -2) | (-1 -4 +2)
  B_5 <011,100,111>: (+3 +7 +2) | (+3 -7 -2) | (-3 +7 -2) | (-3 -7 +2)
  B_6 <011,101,110>: (+3 +4 -6) | (+3 -4 +6) | (-3 +4 +6) | (-3 -4 -6)

The baseline input is 0000000.  The L0 distance between two bit
strings is the number of positions at which they differ.  Find any candidate
z whose L0 distance from the baseline is at most 7 and for
which the ensemble's strict-majority label is True.  Any such input is valid;
you do not have to recover a distinguished planted input.

Give your final answer inside <answer></answer> tags as one contiguous
7-character bit string in x_0,...,x_6 order.
Example format (showing syntax, not a claimed solution): <answer>0000000</answer>
Output nothing else inside the tags.
```

The retained answer is `1101010`. `verify(inst, "1101010")` returns `(True, "ok")`; deleting its final bit returns `(False, "answer is too short: expected 7 bits")`. A person can solve this demo on paper by grouping the four clauses on each feature triple into one parity equation.

## Difficulty

| Preset | Features | Equation factor | Clause trees | Constant-False trees | Answer bits | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 7 | 1 | 28 | 27 | 7 | hand-scale; skipped by hardener |
| easy | 31 | 3 | 372 | 371 | 31 | solved by the oracle, 3/3 |
| medium | 63 | 4 | 1,008 | 1,007 | 63 | solved on 2/2 valid calls; third call blocked by quota |
| hard | 127 | 5 | 2,540 | 2,539 | 127 | **provisional shipping preset; not oracle-tested** |

Escalation first raises redundant-equation crowding at fixed answer length. Once factor 8 is exhausted, it doubles the ambient feature set only when both the 256-atom and 300-operation caps still hold; from the shipping size, the next doubling correctly returns `cap_bound` because its compact route would require 494 XORs. That is a shipping limit only: `make_instance` has no mathematical size cap, and G7 verifies both 255- and 511-feature builds.

## Gate measurements

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verify; all are JSON-native |
| G2 | pass | drop, unequal swap, duplicate, empty, and non-binary corruptions all rejected with five distinct reasons |
| G3 | pass | model-style fenced response round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 uniform structure-aware guesses; 0.137 s |
| G5 | pass | measured rank 120, hence exactly 128 of 2^127 witnesses are valid (density 2^-120); demo enumeration finds 8/128 |
| G6 | pass | five attacks, 0/8 successes each; DPLL and GF(2) references both solve 8/8 |
| G7 | pass | 255- and 511-feature builds have 5,100 and 10,220 clause trees; both plants verify |
| G8 | pass | 100 separate/composed symmetry checks and 100 carried witnesses; 20/20 unrelated keys distinct |
| G9(c) | pass | 129 serialized characters, at most 129 tokens, 127 atoms, 240 intended XORs |

The failing G6 panel was: feature/tag degree outlier (15,240 operations), one-sweep greedy repair (650,240), 256 random restarts per seed (2,048 total candidates), direct right-side-majority (15,240), and the genuinely in-context all-zero baseline ansatz (1,016 bit writes). Each recorded 0/8 successes. Both successful references are deliberately outside `attacks`, as Track B requires.

## Oracle and G9 diagnostics

The main hardener completed `easy` and two calls at `medium`; every valid response contained a verified answer. It then exhausted the key while retrying the final medium slot. The error rows are infrastructure failures, not unsolved answers:

| Preset | Seed | Model | Result | Why |
|---|---:|---|---|---|
| easy | 1677650050 | GPT-5.6 Terra | solved | verified `ok` |
| easy | 855295515 | Gemini 3.8 Flash | solved | verified `ok` |
| easy | 1499102569 | Gemini 3.8 Flash | solved | verified `ok` |
| medium | 1146535396 | GPT-5.6 Terra | solved | verified `ok` |
| medium | 1187913691 | Gemini 3.8 Flash | solved | verified `ok` |
| medium | 39576436 | Gemini 3.8 Flash | error | HTTP 403 key limit |
| medium | 1227888419 | GPT-5.6 Terra | error | HTTP 403 key limit |
| medium | 1809595001 | GPT-5.6 Terra | error | HTTP 403 key limit |
| medium | 659316743 | GPT-5.6 Terra | error | HTTP 403 key limit |

| G9 arm | Solved/valid attempts | API errors | Verdict |
|---|---:|---:|---|
| bare | 0/0 | 4 | unmeasured |
| structural hint | 0/0 | 4 | unmeasured |
| placebo hint | 0/0 | 4 | unmeasured |

Consequently `hinted − placebo` is not statistically defined; the report stores `0.0` only because both attempt denominators are zero. No conclusion about the usefulness of the stated change-of-variables hint is justified. Re-run all three arms after restoring OpenRouter quota.

## Use

```python
import random
import gen_2010_08281 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=42, **params)
statement = g.render(inst)
candidate = g.parse_answer(f"<answer>{inst['answer']}</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) == 2 ** 127
_ = g.random_candidate(inst, random.Random(9))
```

From the repository root:

```bash
bash scripts/emit.sh 2010.08281 20
```

## Caveats

- The required final oracle verdict is absent because the configured OpenRouter key reached its total limit mid-run. This result must not be submitted as fully hardened until the bare ladder reaches a held preset (or its prescribed terminal verdict) and all G9 arms contain valid shipping-preset attempts.
- The affine promise makes this family polynomial with tools. Public vector tags are deliberate extra structure supporting the 240-XOR route; this benchmark tests whether a no-tool solver notices it, not general NP-hard extraction.
- The theorem reduction’s (L_0) bound equals the number of features, so it is vacuous. This exactly follows the proof but is less representative of practical “nearby input” extraction.
- G4 samples uniformly from all correctly sized bit strings, incorporating the only stated free constraints and the full (L_0) bound. Its 0/200,000 observation does not model a solver conditioned on affine functions; the exact valid density (2^{-120}) is stronger only for that declared uniform language.
- No industrial SMT implementation was run. A generic DPLL/unit-propagation baseline and the exact XOR-aware Gaussian solver were both measured, but implementation-specific SMT preprocessing costs remain unmeasured.
- Raising `equation_factor` adds redundant constraints and a larger parsing haystack without shrinking the solution set. It can burden attention more than mathematical search; this is why the missing oracle measurement matters.
- Exact signed-hypergraph isomorphism is not known to be cheap. `canonical_key` uses iterative incidence colour refinement, is tested under feature/tree/test reorderings and a global GL(d,2) tag-basis change, and may conservatively collapse a rare pair of non-isomorphic instances that colour refinement cannot distinguish.
- `gvlib` is unnecessary here: all objects are Boolean, and Python integer bitsets give exact GF(2) arithmetic using only the standard library.
