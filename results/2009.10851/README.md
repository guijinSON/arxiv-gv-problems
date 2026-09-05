# arXiv 2009.10851 problem generator

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate | integer tuple: coordinates of one finite-field element |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

This module turns Masuda, Rubio, and Santiago's [*Permutation binomials of the form \(x^r(x^{q-1}+a)\) over \(\mathbb F_{q^e}\)*](https://arxiv.org/abs/2009.10851) into exact preimage problems.  The solver receives an odd-degree finite field in a changed normal basis, the paper's binomial at \(h=1,a=1,s=q-1,r=q^e\), and a target element.  On the field the binomial is \(x^q+x\).  The answer is its unique preimage, represented by exact base-field coordinates; `verify` applies the basis change, the Frobenius shift, and the inverse basis change using integer arithmetic modulo `q`.

## Trust and hardness

The mathematical and local adversarial gates pass.  The cross-vendor oracle claim is **not yet established**.  A fresh bare run scored twelve calls before the supplied OpenRouter key reached its total limit: the pool solved `easy` 3/3, `medium` 3/3, `hard` 2/3, and the first fixed-length escalation (`n=29,q=211`) 2/3.  The next escalation (`q=431`) stopped after four HTTP 403 errors, so `harden.py` correctly produced no hardness verdict.  The hinted and placebo runs likewise remain unscored.  API errors are not model failures.

Theorem 3.4 (Theorem 1.4 in the introduction), using Lemmas 3.1–3.3, guarantees the selected binomial is a permutation.  Odd `e` makes \((-1)^{1+q+\cdots+q^{e-1}}=-1\ne1\), and `r=q^e` is obtained by taking `h=k=1` and `s=q-1`.  The generator samples the preimage first and computes its image, so it never solves its own instance.

This is Track B because an efficient method exists.  The reference algorithm materializes the displayed \(e\times e\) matrix and performs exact Gaussian elimination in \(O(e^3)\) field operations.  At the shipping preset it solved 8/8 instances, averaging 24,466 field operations and about 0.001 seconds.  The structure-specific algorithm is also disclosed: it observes that the displayed operator is conjugate to `I + cyclic_shift`, applies the triangular change of variables, solves one odd cyclic recurrence, and changes back in \(O(e)\), measured here as 169 exact field operations.  Theorem 1.3's direct classification for `e=2,...,6` and the paper's optimized search below \(q^e=10^8\) are why this is not presented as Track A.

## Worked demo

```text
Invert a permutation binomial over a finite field.

All scalar arithmetic below is modulo the prime q=3.
Let K=F_(q^e) with e=3.  Fix a normal basis eta_0,...,eta_2
whose indices are modulo e and satisfy eta_i^q=eta_(i+1).
A field element is reported in e displayed coordinate slots.  To turn a
displayed vector v into its normal-basis coordinate vector w, first form
chain coordinates c using c[slot_to_chain[j]]=v[j], and then use
  w[0]=c[0],
  w[i]=c[i]+b[i]*w[i-1] mod q  for i=1,...,e-1.
This triangular rule is invertible and therefore defines the displayed basis.

The slot_to_chain list (entry j belongs to displayed slot j) is:
  [2, 1, 0]
The multipliers b[1],...,b[e-1] are:
  [2, 2]

Consider f(x)=x^(q^e)*(x^(q-1)+1), with q^e=27.
For every x in K, x^(q^e)=x, so this same field function is f(x)=x^q+x.
The target y, in displayed coordinate-slot order, is:
  [0, 1, 0]

Find the unique x in K such that f(x)=y.
Your answer must be one JSON array of exactly 3 integers in 0,...,2.
Coordinate order is the displayed slot order above; order matters, zeros and
repeated coordinates are allowed, and the whole vector must be nonzero.

Give your final answer inside <answer></answer> tags, as one JSON array of integers.
Example format only: <answer>[0, 0, 1]</answer>
Output nothing else inside the tags.
```

The answer and two checker calls are:

```text
<answer>[2, 1, 1]</answer>
verify(inst, [2, 1, 1]) -> (True, "ok")
verify(inst, [0, 1, 1]) ->
  (False, "image mismatch at displayed coordinate 0: got 1, expected 0")
```

A person can solve this 3-coordinate demo on paper by converting to normal coordinates, walking the three-cycle, and converting back.

## Difficulty presets

| preset | extension degree `e=n` | base prime `q` | candidate space | status |
|---|---:|---:|---:|---|
| demo | 3 | 3 | \(3^3-1=26\) | hand example; exhaustive count 1 |
| easy | 13 | 5 | \(5^{13}-1\) | solved by the bare oracle pool 3/3 |
| medium | 23 | 17 | \(17^{23}-1\) | solved by the bare oracle pool 3/3 |
| hard | 29 | 101 | \(101^{29}-1\) | declared preset; solved by the bare pool 2/3, so not shippable yet |

`escalate` raises `q` while leaving the 29-coordinate answer fixed.  No preset was rejected by a local gate.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted answers and 12/12 Theorem 3.4 condition sets verified |
| G2 | 5/5 corruption classes rejected with 5 distinct reasons |
| G3 | tagged prose/fence round-trip passed; answer is JSON-native |
| G4 | 0/200,000 structure-aware random candidates valid; language size `101^29-1` |
| G5 | shipping sampled density 0/200,000; demo exact count 1; baseline 24,466 operations, 0.001286 s |
| G6 | six attacks each 0/8; reference Gaussian algorithm 8/8 |
| G7 | degree 59 instance built and its planted witness verified |
| G8 | 40/40 slot/basis/rotation/rescaling invariance checks, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | 145 worst-case characters, 59 estimated tokens, 29 atoms, 169 intended operations |

## Oracle loop and G9 diagnostics

| run | preset | seeds written by harness | scored solved/attempts | outcome |
|---|---|---|---:|---|
| bare | easy | 1272532903, 391235661, 1922560049 | 3/3 | level defeated |
| bare | medium | 1763921824, 678255512, 959527011 | 3/3 | level defeated |
| bare | hard | 616443454, 881150244, 1265477214 | 2/3 | level defeated because any solve escalates |
| bare | escalated `q=211` | 130770164, 1549623943, 1390105295 | 2/3 | level defeated |
| bare | escalated `q=431` | 1415760888, 1758688973, 1315294947, 1485204120 | 0/0 | four HTTP 403 errors; run aborted without a verdict |
| structural hint | hard | 248458531, 2029190165, 371627092, 1925675997 | 0/0 | four HTTP 403 errors; aborted |
| placebo hint | hard | 711864073, 985875523, 1189398825, 1157220126 | 0/0 | four HTTP 403 errors; aborted |

At the declared hard preset the bare diagnostic is 2/3 solved; the hinted-minus-placebo difference is unavailable, not zero, because neither added-hint arm produced a scored attempt.  The hint therefore provides no diagnostic evidence yet.  G9(c)'s writable-answer and intended-operation caps do pass.

## Use

From this directory:

```python
import gen_2009_10851 as g
inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
problem = g.render(inst)
ok, reason = g.verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, emit JSONL instances with:

```bash
bash scripts/emit.sh 2009.10851 20 hard
```

## Caveats

The family becomes easy with a CAS, with the disclosed matrix solver, or once the triangular conjugacy is recognized and the modular recurrence is executed accurately.  In particular, the fastest disclosed route is already linear-time; the Track-B claim is about recognizing and carrying out that compression without tools, not computational intractability.  The 0/200,000 figure estimates uniform guessing over all nonzero coordinate vectors; it does not model a solver using algebraic structure.  The attacks cover a coordinate outlier, direct-target and divide-by-two guesses, partial recognition of either the cycle or the basis change, and 256 uniform restarts per seed.  They do not include a computer-algebra finite-field inverse routine, a dedicated structured-matrix solver, or a successful oracle pool run; Gaussian elimination is the domain-standard automated reference measured here.  `canonical_key` removes the generated triangular basis, slot order, cyclic normal-basis rotations, and common base-field rescaling, but not the full group of changes between arbitrary normal bases; that larger equivalence would require canonicalizing invertible circulant actions and remains an explicit limitation.
