# XOR-zero Walsh quartets from arXiv:2504.01233

> **Status:** the generator and all local gates pass, but the required oracle
> hardening is **not complete**. OpenRouter returned HTTP 403 (“Key limit
> exceeded (total limit)”) for every attempt on the final construction. The
> script-owned transcripts are retained as error evidence, not as a hardness
> claim.

## Profile

| field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | subset sum (four-XOR) |
| certificate | four 0-based indices (`integer_tuple`) |
| native objects | implicitly represented Walsh–Hadamard vertices of a Boolean cube |
| intuition | invariant: linearity plus a whole-list XOR checksum and cyclic rotation |
| domain essentiality | native |
| reduction | none |

## The family

The source is Batmanov and Voronov, [*The Borsuk Problem for Subsets of the
Vertices of the 10-Dimensional Boolean Cube*](https://arxiv.org/abs/2504.01233).
Section 2 defines the exact-distance graph on Boolean-cube vertices. Section 3
classifies the two distance-six `K4` types used in the proof and observes that
the first displayed type has XOR of its four vertices equal to zero.

An instance gives short labels `a` for full Walsh cube vertices
`W_a(x) = parity(a AND x)`, one coordinate for every binary word `x`. Distinct
labels define vertices at exactly half the ambient cube dimension from one
another, and `W_a XOR W_b = W_(a XOR b)`. The solver must find four labels whose
cube vertices XOR to zero. The checker executes the two identities exactly on
integers; it neither expands the exponentially long vertices nor reads the
planted answer.

Generation is inverse. Random decoys are sampled first, and four new labels are
algebraically composed so that their XOR is zero, the XOR of the entire list is
the first planted label, and its one-bit cyclic rotation is the second. A complete
pair-XOR collision check rejects accidental second answers. That check confirms
uniqueness; it does not produce the planted witness.

## Why Track B

This is not a complexity-theoretic claim. The paper itself uses SAT (`kissat`)
for coloring checks, with a one-second cutoff per check, and reports about 14
days for the outer `n=10, k=6` configuration enumeration in Section 3. It gives
no theorem that a generated distribution like this one is hard, so Track A
would be unsupported.

Here the standard exact algorithm hashes pair XORs in `O(N^2)` time and memory.
At the shipping candidate it solved 8/8 tests, as expected, averaging 4,803.25 pair
operations (38,426 total) and 0.00691 seconds total on this machine. That is
easy with code but not a realistic unaided manual calculation. Once the planted
aggregate structure is noticed, the whole-list XOR and its rotation reveal two labels
and one linear scan recovers the other pair; the measured shipping route uses 224 exact
word operations. This mechanical-versus-compact gap is the Track B claim.

## Worked demo

For `make_instance(n=12, label_bits=8, seed=0)`, the labels are:

```text
0: B8   1: 0F   2: F6   3: 03   4: D7   5: EA
6: C1   7: CE   8: 8C   9: E0  10: 17  11: EB
```

The answer is `[2, 4, 6, 9]` because `F6 XOR D7 XOR C1 XOR E0 = 00`.
`verify(inst, [2, 4, 6, 9])` returns `(True, "ok")`.
`verify(inst, [0, 2, 4, 6])` returns
`(False, "quartet XOR is nonzero")`. The demo is genuinely hand-scale: there
are only 495 four-subsets, and this example's aggregate shortcut takes 16 word
operations in the tested seeds.

## Difficulty presets

| preset | labels `N` | label bits `m` | implicit cube dimension `2^m` | admissible four-subsets | status |
|---|---:|---:|---:|---:|---|
| demo | 12 | 8 | 256 | 495 | hand example |
| easy | 140 | 28 | 268,435,456 | 15,329,615 | shipping candidate |
| medium | 144 | 36 | 68,719,476,736 | 17,178,876 | locally verified |
| hard | 148 | 44 | 17,592,186,044,416 | 19,190,605 | locally verified |

`SHIPPING_DIFFICULTY` is provisionally `easy`; it must be reconfirmed by a
successful `harden.py` run after the OpenRouter quota is restored.

## Local gate results

| gate | result |
|---|---|
| G1 | 16/16 planted certificates verify; 16/16 JSON round-trips |
| G2 | 5/5 corruptions rejected with distinct reasons |
| G3 | realistic fenced/prose response round-trips |
| G4 | 0/200,000 hits; exact density `1 / 15,329,615 = 6.52332e-8` |
| G5 | exact valid count 1; pair-XOR baseline 8,179 pair operations on the measured shipping instance |
| G6 | four attacks each 0/8; reference pair-XOR algorithm 8/8 |
| G7 | doubled `N=296` instance builds and verifies |
| G8 | 100/100 affine/reordering invariance checks, 100/100 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | 18 answer characters, 4 atoms, about 5 tokens, 224 intended operations |

The four failing G6 attacks are label-weight outliers, a two-lowest-label greedy
ansatz, 256 uniform restarts, and the first 256 lexicographic pair-XOR checks.

## Oracle loop and G9 arms

The final construction has no scored oracle attempts. All calls failed at the
transport/account layer and therefore correctly did **not** consume attempts:

| arm | preset | scored solved/attempts | script records | outcome |
|---|---|---:|---:|---|
| bare | easy | 0/0 | 4 | HTTP 403 quota errors |
| structural hint | easy | 0/0 | 4 | HTTP 403 quota errors |
| placebo hint | easy | 0/0 | 4 | HTTP 403 quota errors |

Consequently `hinted - placebo` is not estimable; the numeric placeholder is
0.0 and must not be interpreted as an observed effect. The hint has not yet
been tested on this final family.

## Use

```python
import importlib.util

spec = importlib.util.spec_from_file_location("g", "results/2504.01233/gen_2504_01233.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

inst = g.make_instance(seed=7, **g.DIFFICULTY["easy"])
statement = g.render(inst)
answer = g.parse_answer("<answer>[0, 1, 2, 3]</answer>")
ok, reason = g.verify(inst, answer)
```

Because Python package identifiers cannot contain dots or start with digits,
loading this result by `importlib.util.spec_from_file_location` is the portable
choice. From the repository root, emit samples with:

```bash
bash scripts/emit.sh 2504.01233
```

After quota restoration, rerun the required evidence from this directory:

```bash
python3 ../../scripts/harden.py gen_2504_01233.py
```

Then rerun the structural and placebo copies in separate scratch directories,
copy their transcripts back, update `G9_MEASURED_ARMS`, regenerate
`selftest_report.json`, and only then treat the family as shippable.

## Caveats

The Walsh family is a scalable exact construction using the paper's native cube
vertices and XOR witness, but it is not the paper's fixed `n=10, k=6`
configuration distribution and the paper does not analyze it. Its implicit
representation is exponentially more compact than listing each cube vertex;
the checker validates the representation identity symbolically.

The G4 prior is uniform over all four-subsets. This is structure-aware because
all four-subsets of distinct Walsh labels already satisfy the distance condition;
it says nothing about a solver exploiting the planted aggregate identities.
Those identities are precisely what the G6 panel and pending oracle loop probe.

The canonical key is a strong cheap affine invariant—affine rank plus the
triple-XOR collision profile—not a complete canonical form for binary point
configurations. It may theoretically collapse non-equivalent instances. The
tests cover reordering, coordinate-bit permutation, common XOR translation, and
their composition, but not every `GL(m,2)` basis change. No SAT/SMT package was
needed; the domain-standard pair-XOR algorithm is implemented directly. The
largest remaining uncertainty is no-tool model behavior, because the account
quota prevented the required final oracle and G9 measurements.
