# Brandt-semigroup subpower membership generator

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | logic |
| Object regime | finite discrete |
| Computational core | linear algebra |
| Certificate form | integer tuple (a normalized semigroup-generator word) |
| Intended intuition | reduction recognition: find a spanning tight cycle among ternary parity supports |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 2, proof of Theorem 1.1, equations (1)–(2) |

This module turns Markus Steindl’s [*On semigroups with PSPACE-complete subpower membership problem*](https://arxiv.org/abs/1604.01757) into positive instances of subpower membership for the five-element Brandt semigroup \(B_2\). The solver receives an exact definition of generator tuples and a target tuple in a direct power of \(B_2\), encoded compactly by the clause coordinates from the paper’s SAT reduction. It must return a normalized word of generator IDs. Verification performs exact coordinatewise Brandt multiplication and comparison; it does not read the planted answer.

## Why this is Track B

Corollary 1.3 proves that unrestricted SMP(\(B_2\)) is NP-complete via Theorem 1.1, but that worst-case result does **not** prove this planted distribution hard. These instances are deliberately and honestly polynomial-time solvable. Each four-clause block is a ternary XOR equation. Dense Gaussian elimination over \(GF(2)\) takes \(O(mn^2)\); on eight shipping instances with \(n=100,m=350\), the audit counted 1,322,188 bit-XORs total (165,273 average) and 0.107389 seconds.

The compact route is to recognize a hidden spanning tight cycle. Consecutive cycle equations imply \(x_i\mathbin{\mathrm{XOR}}x_{i+3}=r_i\mathbin{\mathrm{XOR}}r_{i+1}\). Since \(3\nmid n\), stepping by three visits every position, after which one original equation fixes the remaining bit. The audited implementation found the cycle in 119 search nodes on average and used exactly \(3n-1=299\) XORs. The 250 extra supports are sampled from the same marginal distribution as a randomly relabelled cycle support and are assigned parity from the already planted answer; they enlarge the haystack without changing the 100-ID witness.

Section 3, Algorithm 1 gives an \(O(|A|^2n)\) algorithm when the Rees sandwich matrix has one block. \(B_2\)’s matrix does not, which is why Corollary 1.3 lands in the NP-complete case. Section 4 makes \(B_2^1\) PSPACE-complete, but its Q3SAT witness enumerates universal assignments and is exponentially long, so this generator intentionally uses \(B_2\) without an identity and the short Section 2 certificate.

## Worked demo

The demo preset at seed 0 is hand-solvable: identify each block’s XOR value, recover the five-cycle, and propagate five bits. Its complete rendered problem is:

~~~text
Find a normalized generator word for a target tuple in a direct power of the Brandt semigroup B2.

Definitions and exact conventions:
- B2 has five elements 0, [1,1], [1,2], [2,1], [2,2]. Multiplication is 0*u=u*0=0. For nonzero elements,
      [i,lambda] * [j,mu] = [i,mu] if lambda=j, and 0 otherwise.
  Tuple multiplication is coordinatewise and word products are evaluated left to right.
- There are 5 Boolean variables x0,...,x4, 10 generator IDs 0,...,9, and 25 tuple coordinates numbered 0,...,24.
- For variable j and value z in {0,1}, call the displayed generator ID a_j^z. Its tuple is defined without abbreviation as follows.
  * At control coordinate i in 0,...,4, a_j^z(i) is [2,2] if i<j, [1,2] if i=j, and [1,1] if i>j.
  * At a clause coordinate, a_j^z is 0 if assigning xj=z makes at least one occurrence of xj or not xj in that displayed clause true; it is [1,1] otherwise. Variables absent from the clause therefore contribute [1,1].
- The target tuple is [1,2] at every control coordinate 0,...,4, and 0 at every clause coordinate 5,...,24.
- A normalized answer has exactly 5 generator IDs. At word position j it must choose exactly one of the two IDs displayed for variable j. Thus repetitions are forbidden and order is fixed by j; the choice at position j is the encoded value of xj.
- Each clause block below is one ternary parity truth table with four ordinary OR-clauses. Every displayed clause is a separate target coordinate. A clause is satisfied if at least one of its literals is true.

Generator IDs:
  variable 0: value 0 -> generator 5; value 1 -> generator 3
  variable 1: value 0 -> generator 0; value 1 -> generator 9
  variable 2: value 0 -> generator 8; value 1 -> generator 4
  variable 3: value 0 -> generator 2; value 1 -> generator 6
  variable 4: value 0 -> generator 1; value 1 -> generator 7

Clause-coordinate blocks:
  block 0:
    coordinate 5: (not x2 OR not x0 OR x1)
    coordinate 6: (x1 OR x0 OR x2)
    coordinate 7: (not x2 OR not x1 OR x0)
    coordinate 8: (not x1 OR not x0 OR x2)
  block 1:
    coordinate 9: (x2 OR not x1 OR not x3)
    coordinate 10: (not x2 OR not x3 OR x1)
    coordinate 11: (x3 OR x1 OR x2)
    coordinate 12: (not x1 OR not x2 OR x3)
  block 2:
    coordinate 13: (not x4 OR not x3 OR x0)
    coordinate 14: (not x0 OR x4 OR not x3)
    coordinate 15: (x3 OR not x4 OR not x0)
    coordinate 16: (x0 OR x3 OR x4)
  block 3:
    coordinate 17: (not x0 OR not x1 OR x4)
    coordinate 18: (x1 OR x0 OR x4)
    coordinate 19: (x0 OR not x4 OR not x1)
    coordinate 20: (not x4 OR not x0 OR x1)
  block 4:
    coordinate 21: (x2 OR not x3 OR not x4)
    coordinate 22: (not x2 OR x4 OR not x3)
    coordinate 23: (not x4 OR x3 OR not x2)
    coordinate 24: (x3 OR x4 OR x2)

Give your final answer inside <answer></answer> tags, as one JSON array of exactly 5 integer generator IDs in word order.
Example format (not necessarily a solution): <answer>[5, 0, 8, 2, 1]</answer>
Output nothing else inside the tags.
~~~

The answer is “<answer>[3, 9, 4, 6, 7]</answer>”. verify(inst, [3, 9, 4, 6, 7]) returns (True, "ok"); dropping the last ID returns (False, "wrong length: expected 5, got 4").

## Difficulty

| Preset | \(n\) | Decoys | Blocks | Candidate space | Result |
|---|---:|---:|---:|---:|---|
| demo | 5 | 0 | 5 | \(2^5\) | hand example; skipped by hardener |
| easy | 46 | 0 | 46 | \(2^{46}\) | oracle solved 2/3 |
| medium | 73 | 40 | 113 | \(2^{73}\) | oracle solved 1/3 |
| **hard (ships)** | **100** | **250** | **350** | **\(2^{100}\)** | bare and structural-hint pools both failed 0/3 |

An earlier 100-variable level with 150 decoys held bare but failed G9(b): one of three hinted oracles solved it. The single permitted upward move increased only decoy density to 250; both bare and hinted tests were rerun there.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted words verified; compact recovery matched all |
| G2 | pass | 5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged prose and untagged fenced JSON both round-tripped |
| G4 | pass | 0/200,000 structured guesses; exact density \(2^{-100}=7.888609052210118\times10^{-31}\) |
| G5 | pass | one certified shipping solution; Gaussian baseline 1,322,188 XORs/8; strongest failing attack 2,600 steps |
| G6 | pass | four attacks, 0/8 successes each; reference Gaussian solver 8/8 |
| G7 | pass | doubled \(n=200\) instance built and verified |
| G8 | pass | 100 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | pass | 445 chars, 112 estimated tokens, 100 atoms, 299 intended XORs; hinted 0/3 |

## Bare oracle loop

| Preset | Seed | Model | Solved | Checker result |
|---|---:|---|---|---|
| easy | 1858406570 | Grok 4.6 | yes | ok |
| easy | 111907080 | Gemini 3.1 Pro | yes | ok |
| easy | 268215001 | GPT-5.6 Terra | no | wrong clause coordinate |
| medium | 908937984 | Grok 4.6 | yes | ok |
| medium | 745164624 | Claude Sonnet 5 | no | empty length-limited completion |
| medium | 1604910696 | Gemini 3.1 Pro | no | wrong clause coordinate |
| hard | 700121217 | Claude Sonnet 5 | no | empty length-limited completion |
| hard | 1908452338 | GPT-5.6 Terra | no | wrong clause coordinate |
| hard | 348987058 | Gemini 3.1 Pro | no | wrong clause coordinate |

## G9 arms

| Arm at final hard | Solved / valid attempts | Notes |
|---|---:|---|
| bare | 0/3 | final script-owned bare run |
| structural hint | 0/3 | one Grok timeout was discarded and redrawn |
| placebo hint | 1/3 | one Grok timeout was discarded; its redraw solved |

Hinted minus placebo is \(-1/3\). On this sample the structural sentence did not help relative to a same-register placebo. It names the right invariant but leaves cycle extraction and all 299 XORs to the solver. The arm’s negative difference is diagnostic only; G9(b) passes because the hinted pool was still hardened.

## Use

From this directory:

~~~python
import random
import gen_1604_01757 as g

inst = g.make_instance(seed=123, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
candidate = g.parse_answer("<answer>" + str(inst["answer"]) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) == 2 ** 100
sample = g.random_candidate(inst, random.Random(7))
~~~

From the repository root, emit 20 shipping instances with:

~~~bash
bash scripts/emit.sh 1604.01757 20 hard
~~~

The module uses only the Python standard library; gvlib is unnecessary for this finite exact construction.

## Caveats

- This is not evidence of average-case NP-hardness. Gaussian elimination solves every generated instance quickly, and any sandbox/CAS makes the family easy; that is why it is Track B.
- The shipping statement is large (350 parity blocks, 1,400 clauses). The answer and post-insight arithmetic fit G9’s caps, but finding the tight cycle still tests sustained structural extraction from a long prompt. The audit finder averaged 119 backtracking nodes; this should not be mistaken for computational hardness.
- The exact \(2^{-100}\) density is relative to the normalized language that already chooses one displayed generator per word position. It does not describe a looser space of arbitrary generator strings. The 0/200,000 experiment is consistent with, but does not itself establish, that exact theorem-backed density.
- The adversary panel tried literal-frequency outliers, greedy single-bit clause gain, 256 uniform restarts per seed, generator-label ansatzes, dense Gaussian elimination, and the cycle extractor. It did not run an external SAT/SMT package; exact \(GF(2)\) elimination is the domain-standard algorithm for these recognized XOR blocks.
- canonical_key is a strong, cheap Weisfeiler–Lehman incidence invariant, not a complete hypergraph-isomorphism canonical form. It passed variable/generator relabelling, block/clause/literal reordering, Boolean complementation, composition, and 20-seed distinctness, but rare non-isomorphic collisions remain possible.
- Two accepted oracle failures (bare and hinted) were empty Claude completions at the fixed 32,000-token completion budget. The other shipping failures were parsed lists rejected by exact verification. The transcripts preserve those distinctions and the discarded 900-second provider timeouts.
