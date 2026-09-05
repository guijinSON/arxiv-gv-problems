# Graph decompositions in projective geometries — verified generator

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | CSP over Frobenius edge-orbit representatives |
| Certificate form | integer tuple encoding an edge starter |
| Intended intuition | symmetry: one cyclic translation is shared across all Frobenius-orbit rows |
| Domain essentiality | native |
| Reduction | none |

## What the family asks

This generator is based on Buratti, Nakić, and Wassermann, [*Graph decompositions in projective geometries*](https://arxiv.org/abs/1907.03194), especially Definitions 4.2 and 5.1, Theorem 5.4, Proposition 5.12, and the Frobenius-orbit construction in Section 10.1. A solver receives points of `PG(v-1,2)` in Singer cyclic coordinates, a trace-zero hyperplane template, and candidate starting points for one edge in each signed Frobenius difference orbit. The answer chooses one start per orbit. The checker reconstructs every Frobenius-developed edge with exact modular arithmetic, recomputes the finite-field trace hyperplane, verifies that every hyperplane point is incident, and checks that every nonzero directed difference occurs exactly once. Theorem 5.4 then identifies the cyclic translates as the desired projective graph decomposition.

The answer is generated before the decoys: a cyclic translation is sampled and applied to a deterministic, exactly audited starter. All decoy starts are independent translations of the same row templates. Thus the certificate is carried through a structure-preserving map; the generator never solves the instance it emits.

## Why Track B, not Track A

The paper does not establish distributional computational hardness. Indeed, Proposition 9.3 explicitly solves the Paley/circulant graceful-labeling case by a group isomorphism, while Section 10.1 supplies only finite Singer-cycle examples and Conjecture 10.2 is not a theorem. Claiming Track A would therefore be unjustified.

For this generated distribution, the successful reference algorithm forms the offset `candidate_start - template_start (mod M)` for the whole table and takes the most frequent value. It is `O(r n)`. At the shipping parameters `r=93,n=128`, it performs 11,904 modular subtractions and 93 additions, or 11,997 exact operations. Across eight shipping instances it solved 8/8 in 0.144043 seconds total (0.018005 seconds per instance). This is easy with code but far beyond a no-tool response.

The compact route notices that the marked observations preserve the same row-relative offset. It needs 160 subtractions to find the repeated offset and 93 additions to write the starter: 253 exact operations. Near-global blocker offsets occur in 92 of 93 rows, so a partial scan cannot distinguish them from the target. Section 5.3’s multiplier viewpoint and Section 10.1’s Frobenius path orbit are the structural ideas being tested.

## Worked demo

The `demo` preset is hand-solvable. With seed 5, the complete rendered instance is:

```text
Recover a Frobenius-developed graph starter in a projective hyperplane.

Exact objects and conventions:
- Work over GF(2^5) = GF(2)[x]/(x^5 + x^2 + 1). Let alpha be the residue class of x. Its nonzero powers are indexed by the cyclic group Z_M, where M=2^5-1=31; all displayed residues use the representatives 0 through 30.
- The absolute field trace is Tr(z)=z+z^2+...+z^(2^4). In Singer coordinates the trace-zero projective hyperplane is D={e in Z_M : Tr(alpha^e)=0}. It has 15 points. For c in Z_M write H_c={e+c mod M : e in D}.
- An undirected initial edge with start a and step d is {a,a+d mod M}.
- For a center c, the centered Frobenius map is F_c(z)=2(z-c)+c mod M. Develop an initial edge by applying F_c^i to both endpoints for every i=0,...,4.
- For every developed undirected edge {u,w}, its directed differences are w-u and u-w modulo M.

Instance data:
- The template hyperplane center is c0=0.
- Each row below gives one signed Frobenius difference orbit, a known template start, its step, and an unordered set of candidate starts. Choose exactly one candidate start from every row.
- Let R* be the row whose orbit number is smallest. If x* is your chosen start in R* and a* is that row's template start, define tau=x*-a* mod M and c=c0+tau mod M.
- Your chosen starts define one initial edge per row. Develop all of them around c. A valid answer must have: (i) no loops or repeated developed edges; (ii) endpoint set exactly H_c, so the graph is a proper graph-subspace; and (iii) every nonzero directed difference 1,...,M-1 exactly once. By cyclically translating this graph block through Z_M, these identities give the graph decomposition.
- Candidate order inside a row is irrelevant. Answer order is the displayed row order. Starts may repeat between different rows.
- The marked observations below are auxiliary data only and do not change validity. Exactly 2 of them are entries of the target starter used to construct this instance.

Rows:
R0 orbit=1 template=15 step=1 : 3 10 23
R1 orbit=3 template=4 step=3 : 18 23 28
R2 orbit=5 template=2 step=5 : 10 21 26

Marked observations:
(orbit=1,start=3) (orbit=3,start=18) (orbit=5,start=21)

Give your final answer inside <answer></answer> tags, as one JSON array of exactly 3 integers, one chosen start per row in displayed row order.
Example format (wrong length and not a solution): <answer>[4, 17, 9]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[3, 23, 21]</answer>`. `verify(inst, [3, 23, 21])` returns `(True, "ok")`; dropping the last row gives `(False, "wrong length: expected 3, got 2")`. A person can solve this demo by comparing the three row-relative offsets modulo 31.

## Difficulty presets

| Preset | v | Rows | Candidates/row | Blockers | Marked | Answer entries | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 5 | 3 | 3 | 2 | 3 | 3 | hand example |
| easy | 7 | 9 | 10 | 8 | 10 | 9 | first oracle rung |
| medium | 11 | 93 | 48 | 40 | 80 | 93 | local gates pass |
| hard | 11 | 93 | 128 | 92 | 160 | 93 | **shipping preset** |

No preset was rejected by a local gate. Escalation first adds marked decoys up to the 300-operation route cap, then increases candidate crowding while the 93-entry witness stays fixed.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified; compact route also verified |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions all rejected with 5 distinct reasons |
| G3 | pass | tagged and fenced model-style answers round-trip |
| G4 | pass | 0/200,000 structure-aware random candidates valid; space `128^93` |
| G5 | pass | shipping sampled density 0.0; demo has exactly 2 valid answers among 27 |
| G6 | pass | five attacks, each 0/8; reference algorithm 8/8 at 11,997 operations/instance |
| G7 | pass | 256 candidates/row builds and verifies with the answer still 93 entries |
| G8 | pass | 20/20 composed relabellings invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | pass | 418 chars, 105 estimated tokens, 93 atoms, 253 intended exact operations |

## Oracle hardening and G9 arms

The configured OpenRouter key was over its total limit. `harden.py` made four retries for each run and every provider call returned HTTP 403, so it correctly refused to turn an API outage into evidence of model failure. The script-owned transcripts are retained, but **no oracle hardness claim has been made**.

| Arm | Solved/attempts | Script outcome |
|---|---:|---|
| bare | 0/0 | four API-error retries; pool unreachable |
| structural hint | 0/0 | four API-error retries; pool unreachable |
| placebo hint | 0/0 | four API-error retries; pool unreachable |

`hinted - placebo` is therefore not measurable, and the hinted verdict is `not_run`. The structural hint names only the common row-relative offset invariant; it does not state an algorithm or a derived value.

## Use

From the repository root:

```python
import importlib.util

path = "results/1907.03194/gen_1907_03194.py"
spec = importlib.util.spec_from_file_location("generator", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=42, **params)
statement = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

Emit dataset records with:

```bash
bash scripts/emit.sh 1907.03194 20
```

## Caveats

- This is deliberately Track B. With a sandbox, the full offset histogram solves the planted distribution in milliseconds; the benchmark claim is only about compressing that mechanical scan into a no-tool response.
- The 0/200,000 guess rate is for uniform choices of one displayed candidate per row. It is not the success probability of a solver that conditions on a chosen anchor hyperplane or exploits the marked-offset symmetry.
- Other valid starters can exist and `verify` accepts them; the demo has two. The checker never compares with `inst["answer"]`.
- The local panel did not run an external SAT/CP package. The full offset histogram is the stronger construction-aware reference algorithm for this distribution; a generic finite-field CSP solver may also succeed.
- The canonical key is exact for input reorderings, Singer translations, Frobenius relabellings, and their compositions. It does not attempt arbitrary projective equivalence under a change of primitive polynomial.
- Oracle and G9 behavioral evidence remains blocked by external quota, as recorded above. Correctness, density, attacks, scaling, and canonicalization were all measured locally; no claim should be made about four-vendor model hardness until the harness completes successfully.
