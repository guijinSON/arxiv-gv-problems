# Rejected after G9(b): arXiv:2602.19989

Track considered: **B (no-tool compression)**. The retained implementation is
`rejected_gen_2602_19989.py`; it is evidence for the decision, not a shippable
generator.

## Decision

The native construction passes G and V, but fails **H for Track B as enforced by
the mandatory G9(b) polarity-flipped gate**. The bare `hard` preset defeated all
three oracle vendors. With the one-sentence structural hint, the first independent
oracle returned a verified witness. One success is already enough to fail the
rung, so the remaining paid calls were stopped and no further tuning was done.

Track A is not a fallback. The paper proves existence, not computational or
average-case hardness for this planted distribution, and the distribution has an
efficient exact orbit-recognition algorithm. Calling it Track A would conceal the
algorithm that recovers its certificates.

## What the paper says

Section 1 fixes the exact native witness. For an ordering
`a_1,...,a_m` of a subset of an abelian group, partial sums
`p_i=a_1+...+a_i` must be pairwise distinct; a sequencing additionally requires
`p_i != 0` for every `i<m`, while the final sum may be zero.

Theorem 1.3 proves classical sequenceability in the regime
`|A| <= exp(c(log p)^(1/3))`, where `p` is the least prime divisor of the cyclic
group order. Theorem 1.4 gives the stated `t`-weak existence regime. Lemma 2.7
produces existence with positive probability through the paper's one-shot random
splitting/ordering construction and the Lovasz Local Lemma. The paper states no
polynomial-time, FPT, approximation, or hardness result for finding a sequencing.
These facts rule out an honest Track-A claim but leave Track B worth testing.

## Attempted family and exact certificate

For a prime `p`, a primitive root `r`, and `n<p-1`, let

```text
G = 1 + r + ... + r^(n-1)  (mod p),
u = r/G                    (mod p),
A = {u, ur, ..., ur^(n-1)}.
```

The generator samples `p` and `r`, constructs the orbit order first, and only then
shuffles `A`. It never solves the emitted instance. Every consecutive interval of
length `ell` in the planted order has sum

```text
u r^i (r^ell - 1)/(r - 1)  (mod p),
```

which is nonzero for `1 <= ell <= n` because `r` has order `p-1`. This proves the
partial sums are distinct and all proper partial sums are nonzero. Verification
independently checks the permutation and recomputes the exact modular partial sums.
Thus G and V pass in the paper's native cyclic-group objects.

The scale `u=r/G` also makes `sum(A)=r`. That checksum is the intended compact
invariant.

## Algorithm audit and measured costs

The Track-B reference algorithm is exhaustive pair-ratio overlap recognition: it
forms all quotients of displayed residues, counts how many elements each quotient
maps back into `A`, and expands the score-`n-1` orbit directions. Its complexity is

```text
O(n^2 log p + n min(p,n^2)) exact work.
```

At the final `hard` preset (`n=120`, `slack=28`) it solved **8/8** instances. The
measured total was **254,341 modular-operation/membership units**, averaging
**31,792** and peaking at **32,858** per instance; all eight runs together took
**0.012752 seconds** on this host in the retained self-test report.

The compact route sums the 120 residues to obtain `r`, evaluates the geometric
series by binary powering, inverts it with extended Euclid, and expands the orbit.
The retained module executes this route and measured **263 exact operations**.
The gap is real—roughly 120 times fewer counted operations—so the family is not
being rejected merely because an efficient algorithm exists, nor because the
mechanical and compact routes are comparable.

Before G9, 0 of 200,000 structure-aware random permutations verified. Four attacks
each scored 0/8: centered-magnitude ordering, locally safe middle-first greedy,
256 uniform permutation restarts, and a checksum-aware in-context heuristic that
guesses the numerical minimum as the orbit endpoint. The answer used 120 atomic
elements and 393 serialized characters; the compact route's 263 operations is
below the 300-operation cap. This is not `cap_bound`.

## Failing gate

The final bare `hard` run was **0/3 solved** across GPT-5.6-terra,
Claude Sonnet 5, and Gemini 3.1 Pro. The structural hint was:

> The common multiplier of the hidden multiplicative orbit equals the sum of all
> displayed elements modulo p.

This names one invariant. It contains no chained step, algorithm, derived ordering,
or output instruction. Nevertheless Gemini 3.1 Pro computed the multiplier,
identified the orbit, and returned a witness that `verify` accepted, so the hinted
arm was **1/1 solved** when stopped. The candidate had already been moved up once,
from the bare-held `medium` rung to `hard`, as G9(b) permits; another escalation
would be tuning past the prescribed verdict.

Evidence retained here:

- `llm_loop_transcript.jsonl`: script-written final bare `hard` run, 0/3 solved.
- `.meta.json`: the corresponding script-written `hardened` verdict.
- `g9_hinted_transcript.jsonl`: script-written hinted `hard` result, 1/1 solved.
- `g9_hinted_meta.json`: harness metadata for the interrupted terminal arm.
- `rejected_gen_2602_19989.py`: the complete generator and reproducible local gates.

The placebo arm was not run after the gated hinted arm had already supplied the
terminal rejection; placebo is diagnostic only and cannot reverse G9(b).
