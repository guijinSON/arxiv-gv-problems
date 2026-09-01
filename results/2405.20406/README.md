# Pentagon-solution isomorphism generator

This directory turns [Colazzo–Okniński–Van Antwerpen, *Bijective solutions to the Pentagon Equation* (arXiv:2405.20406v2)](https://arxiv.org/abs/2405.20406) into a witness problem. The solver receives two alternating tensors over `F_3`. Each tensor defines a class-2 exponent-3 group and hence the finite pentagon map `s_G(x,y)=(xy,y)`. The witness is a pair of invertible matrices `(P,Q)` giving an isomorphism. Checking consists only of modular Gaussian elimination and the identities `P^T TARGET[k] P = sum_l Q[k,l] SOURCE[l]`.

## Why this is the paper's problem, and why it is hard

Definition 2.2 defines an isomorphism of pentagon solutions by `(f×f)s=t(f×f)`. Theorem 4.1 constructs a solution from a matched pair; taking its `A` factor trivial gives exactly `s_G(x,y)=(xy,y)`. Proposition 5.6 and Corollary 6.6 then make pentagon-solution isomorphism equivalent to matched-pair isomorphism, and in this special case to group isomorphism.

The tensor is required to be surjective and radical-free, so its group has commutator subgroup and center equal to the displayed output space. Isomorphism is therefore the skew-symmetric matrix-tuple isometry problem. No polynomial-time algorithm is known for this regime: class-2 exponent-`p` groups are identified as a major group-isomorphism barrier by [Sun, 2023](https://arxiv.org/abs/2303.15412), while tensor and class-2 `p`-group isomorphism belong to the robust tensor-isomorphism complexity class described by [Grochow–Qiao, 2019](https://arxiv.org/abs/1907.00309). Both tensor modes grow under `escalate`; the structured standard search space is about `2.04×10^24` matrix pairs.

The generator avoids the paper's easy regimes. Theorem 4.1 itself makes forward construction a formula lookup, so the task asks for an unknown isomorphism instead. Proposition 6.2 explicitly removes extension permutations up to isomorphism, so `X` is not used as fake hardness. Section 7 shows that involutive finite solutions reduce to elementary abelian 2-groups with trivial actions; this generator instead uses nonabelian exponent-3 groups. The originally tested `(n,m)=(6,3)` standard setting was also discarded because G8 found only 11 distinct structural keys among 20 seeds; increasing the output mode to `m=4` produced 20/20.

## Worked demo (`seed=0`)

The smallest preset renders this statement in full:

```text
Find an isomorphism between two finite set-theoretic solutions of the pentagon equation.

All arithmetic below is in the finite field F_3: add and multiply integers modulo 3. Vectors are columns. Indices are 0-based.

An alternating bilinear map B: F_3^3 x F_3^3 -> F_3^2 is encoded by 2 matrices B[k], with
    B(u,v)[k] = u^T B[k] v  (mod 3).
The displayed matrices are alternating: their diagonal is zero and B[k][j][i] = -B[k][i][j] modulo 3.

Such a B defines a finite group on pairs (u,z) in F_3^3 x F_3^2; its multiplication is
    (u,z) * (v,w) = (u+v, z+w+inv2*B(u,v)),
where inv2=2 is the inverse of 2 modulo 3. This group defines the bijective pentagon map s_B(x,y)=(x*y,y). You do not need to list this exponentially large map.

The two tensors SOURCE and TARGET below define two such pentagon maps. Find two matrices:
  - P, exactly 3 by 3, invertible over F_3;
  - Q, exactly 2 by 2, invertible over F_3.
They must satisfy, for every k=0,...,1,
    P^T TARGET[k] P = sum over ell=0,...,1 of Q[k][ell] SOURCE[ell]  (mod 3).
Equivalently, F(u,z)=(P u,Q z) is an isomorphism of the two groups and of their pentagon maps. Other valid isomorphisms may exist; any one is accepted.

Matrix entries must be JSON integers in the inclusive range 0 through 2. Row order and column order matter. Repetitions are allowed as entries, but P and Q must each be invertible.

SOURCE has 2 component matrices, numbered 0 through 1:
SOURCE[0]
0 0 1
0 0 0
2 0 0
SOURCE[1]
0 0 2
0 0 1
1 2 0

TARGET has 2 component matrices, numbered 0 through 1:
TARGET[0]
0 0 2
0 0 0
1 0 0
TARGET[1]
0 1 0
2 0 1
0 2 0

Give your final answer inside <answer></answer> tags, as one JSON object with exactly the keys "P" and "Q", each containing a row-major array of rows.
Example of the exact syntax (the identity matrices illustrate syntax only and normally are not a solution):
<answer>{"P":[[1,0,0],[0,1,0],[0,0,1]],"Q":[[1,0],[0,1]]}</answer>
Output nothing else inside the tags.
```

One answer is `<answer>{"P":[[1,1,0],[1,2,1],[1,1,1]],"Q":[[1,2],[0,2]]}</answer>`. `verify(inst, answer)` returns `(True, "ok")`. Replacing the second row of `P` by its first row returns `(False, "P is not invertible over F_3")`.

## Difficulty presets

| preset | `n` | `m` | role/result |
|---|---:|---:|---|
| `demo` | 3 | 2 | Readable example; all three oracles solved it; exact valid fraction is 864/539,136. |
| `standard` | 6 | 4 | **Shipping preset**; all three standard-rung oracle attempts failed. |
| `hard` | 8 | 4 | Larger fallback; not reached because `standard` held. |

## Gate results at the shipping preset

| gate | measured result |
|---|---|
| G1 | 9/9 plants verify (3 presets × 3 seeds). |
| G2 | 5/5 corruptions rejected with 5 distinct reasons. |
| G3 | Tagged, fenced JSON with surrounding prose round-trips. |
| G4 | 0/200,000 uniform guesses from `GL(6,3)×GL(4,3)`; structured space `2,041,078,601,585,144,836,915,200`. |
| G5 | Tiny exact case: 864/539,136 structured candidates valid (`0.00160256`). |
| G6 | Sparsity-outlier, greedy coordinate-swap, and 64-random-restart attacks each solved 0/8. |
| G7 | Doubling `(6,4)` to `(12,8)` verifies; naive search-space bit length grows 83→330. |
| G8 | 80/80 composed relabellings preserve the key and carried answer; 20/20 unrelated keys differ. |

## Oracle hardening loop

| preset | model | seed | result | reason |
|---|---|---:|---|---|
| demo | Claude Sonnet 5 | 1523199754 | solved | Valid parsed witness. |
| demo | Grok 4.6 | 837890600 | solved | Valid parsed witness. |
| demo | Gemini 3.1 Pro Preview | 307517818 | solved | Valid parsed witness. |
| standard | Claude Sonnet 5 | 1698430387 | failed | Used all 32,000 completion tokens in reasoning and returned no content (`finish_reason=length`). |
| standard | Grok 4.6 | 1534152685 | failed | Parsed matrices; tensor equation failed. |
| standard | Gemini 3.1 Pro Preview | 2044393082 | failed | Parsed matrices; tensor equation failed. |

The repository-owned verdict is `hardened`, with one escalation and `standard` as `shipping_params`. The Claude row is weaker evidence than an algebraically wrong witness and is reported as such; the two other vendors produced checkable wrong answers.

## Use

From this directory:

```python
import gen_2405_20406 as gen

inst = gen.make_instance(seed=123, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)
```

From the repository root, emit a checked corpus with `bash scripts/emit.sh 2405.20406 20 standard`.

## Caveats

G4 samples uniformly from the full obvious constraint set `GL(n,p)×GL(m,p)`; it rules out blind structured guessing under that prior, not algebraic attacks or a favorable nonuniform prior. The adversary panel is deliberately cheap. It does **not** implement Sun-style individualization/refinement, tensor-isomorphism algorithms, Gröbner-basis/SAT encodings, or code-equivalence methods, and this finite preset is not a cryptographic security claim. A solver that recovers a distinguished tensor decomposition could make instances easier.

`canonical_key` is not a complete tensor canonical form—that would substantially duplicate the hard isomorphism task. It hashes a recursive, basis-invariant signature of ranks and common radicals over the projective lattice of the alternating matrix space. G8 checks all representation symmetries available here: independent input/output basis changes on both tensors, coordinate and component permutations, source/target exchange, and their compositions. The invariant can collide for nonisomorphic tensors; emission resamples collisions, and the observed standard-preset result was 20/20 distinct. Finally, the paper proves the structural reduction but no complexity theorem; the hardness claim relies on the external primary complexity results linked above.
