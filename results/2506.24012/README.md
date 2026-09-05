# arXiv 2506.24012 problem generator

This is a native finite-field, Track B generator based on Ruikai Chen's
[A general approach to permutation polynomials from quadratic forms](https://arxiv.org/abs/2506.24012).
It is locally verified, but the required four-vendor hardness measurement is
still unavailable: OpenRouter rejected every vendor request with HTTP 403
`Key limit exceeded (total limit)`. Those errors are preserved in the three
script-owned transcripts and are not counted as model failures.

| Profile field | Value |
|---|---|
| Track | B — an efficient exact algorithm exists and is reported |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity |
| Certificate | exact symbolic finite-field element `[u,v]` |
| Intuition | invariant: relative trace exposes the preimage trace |
| Domain essentiality | native; no reduction |

## The problem

For odd `n`, the solver is handed the field
`E = GF(2^n)[W]/(W^2+W+1)`, an exact polynomial-basis presentation, and a
target `y`. It must find the unique preimage of

`F(x) = a*x^2 + x*Tr(x)`

with `a` a nonidentity element of `GF(4)`. Corollary 15, specialized to
`l=1,k=0`, and Example 16 guarantee that this map permutes `GF(4^n)`. The
rendered zero terms are identities `c*(x^(4^n+r)+x^(r+1))`, licensed by the
paper's Section 1 convention `x^(4^n)=x`; they add presentation crowding but
do not replace the native polynomial. A witness is checked cheaply and exactly
by one trace computation and one field evaluation.

## Why Track B

This family would be false as a Track A claim. A specialist can try all four
possible relative traces and solve the resulting binary linear systems by
Gaussian elimination in `O(n^3)` bit operations. On eight `n=31` instances,
the reference implementation solved 8/8 with a mean of 89,884 instrumented
assembly/elimination bit operations and about 0.0044 seconds in the recorded
final self-test.

The compact route is the paper's trace structure: from `y=F(x)`,
`Tr(y)=(a+1)Tr(x)^2`. After the preimage trace is known, a normalization gives
an Artin--Schreier equation `z^2+z=c`; the odd extension degree permits two
half-traces in `GF(2^n)`. The measured route used at most 110 field operations.
Recognizing that invariant is the intended work; doing four 62-variable exact
eliminations in context without tools is not. Proposition 3 explains why trace
and quadratic forms control the permutation criterion, while Corollary 15 is
also the decisive easy-regime result that forbids a Track A label.

## Worked demo

For `make_instance(n=3, decoy_terms=0, seed=7)`, the full rendered data use
`P=11`, trace mask `M=1`, `a=[0,1]`, and target `y=[7,7]`. The requested
answer is:

```text
<answer>[3, 2]</answer>
```

`verify(inst, [3, 2])` returns `(True, "ok")`; swapping the components gives
`(False, "the candidate does not map to the target")`. A person can solve this
demo by the trace shortcut or by checking its 42 legal candidates on paper.

## Difficulty presets

| Preset | `n` | Zero terms | Candidate-space scale | Status |
|---|---:|---:|---:|---|
| demo | 3 | 0 | 42 | hand-scale illustration |
| easy | 31 | 6 | 4,611,686,011,984,936,962 | candidate shipping preset |
| medium | 47 | 10 | about `2^94` | available escalation |
| hard | 61 | 14 | about `2^122` | available escalation |

No preset was rejected by a local gate. The oracle could not evaluate even the
first preset because the configured OpenRouter key had reached its total limit,
so `easy` is not yet supported by valid STEP 4 evidence.

## Gate results

| Gate | Result |
|---|---|
| G1 | 16/16 planted witnesses verified and JSON-round-tripped |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | realistic tagged prose parsed; garbage returned `None` |
| G4 | 0/200,000 structure-aware guesses; required rate `<1e-6` |
| G5 | shipping sampled density 0/200,000; demo exact count 1/42; 4,096-restart baseline failed in about 0.140 s |
| G6 | four attacks failed on 8/8 seeds; Gaussian reference solved 8/8 as expected |
| G7 | doubled build at `n=63`, 13 zero terms, verified |
| G8 | 80/80 Frobenius invariance and carried-witness checks, 20/20 reorder checks, 20/20 unrelated keys distinct |
| G9(c) | 22 characters, 22 conservative tokens, 2 atoms, 110 intended operations |

## Oracle loop and G9 arms

| Arm | Valid solved/attempts | Script calls | Outcome |
|---|---:|---:|---|
| bare | 0/0 | 4 | all HTTP 403 key-limit errors |
| structural hint | 0/0 | 4 | all HTTP 403 key-limit errors |
| placebo hint | 0/0 | 4 | all HTTP 403 key-limit errors |

Because API errors do not consume attempts, there is no honest
`hinted - placebo` estimate yet. The structural hint names only the invariant:
“The relative trace of the target depends only on the relative trace of its
preimage.” No hardness or hint-effect conclusion is drawn from the error-only
transcripts.

## Use

```python
from gen_2506_24012 import make_instance, render, parse_answer, verify

inst = make_instance(n=31, decoy_terms=6, seed=123)
print(render(inst))
candidate = parse_answer("<answer>[1, 2]</answer>")
print(verify(inst, candidate))
```

From the repository root, emit instances after a valid oracle rerun with:

```bash
bash scripts/emit.sh 2506.24012 20
```

## Caveats

The `0/200,000` guess result is for the exact promised prior—uniform nonzero,
distinct component pairs—and measures only blind guessing, not algebraic
attacks. The family becomes easy with finite-field software, with the trace
identity, or with Gaussian elimination; that is the explicit Track B premise.
The panel did not test Gröbner-basis software, generic computer algebra, timing
side channels, or language-model performance because the required provider was
unavailable. Canonicalization covers all field Frobenius automorphisms in the
fixed presentation and reordering of zero identities; it does not attempt to
recognize arbitrary isomorphic field presentations with different irreducible
polynomials. Most importantly, this result must not be submitted as hardened
until `harden.py` completes three non-error attempts at the held preset and the
hinted/placebo arms are rerun with a funded OpenRouter key.
