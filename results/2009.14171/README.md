# arXiv 2009.14171 — rejected HR-LQ generator prototype

Status: **rejected because H fails on both tracks**. The full decision, with
the theorem references and the mechanical-versus-compact cost comparison, is
in [REJECTED.md](REJECTED.md).

## What was built

The prototype applies Section 3.2, Theorem 2 of Boehmer and Heeger,
[*A Fine-Grained View on Stable Many-To-One Matching Problems with Lower and
Upper Quotas*](https://arxiv.org/abs/2009.14171). It inverse-generates a regular
multicolored graph over `GF(p)` together with an independent transversal, then
carries that transversal through the theorem's explicit construction of a
stable Hospital Residents matching with lower quotas.

The solver is handed the HR-LQ residents, hospitals, quotas, strict
preferences, and a succinct table defining the graph. A certificate selects
one vertex hospital per color. Verification checks the answer's exact shape
and confirms by modular arithmetic that no selected pair corresponds to a
quota-four edge hospital that can be opened by a blocking coalition. G and V
pass; generation samples the transversal before constructing the relations and
does not solve an instance.

## Why it was rejected

The rendered relation table explicitly gives coefficients satisfying
`a*x_c + b*x_d + g = e (mod p)`. Three rows determine `x_0`, and the rows
joining color 0 to every other color determine the rest. Consequently:

- Track A is false because this decoder solves every generated instance in
  polynomial time.
- Track B is false because the input-native mechanical algorithm and the
  claimed compact route are the same 241-operation modular calculation. The
  earlier 721,140-operation baseline first expanded the succinct graph and was
  therefore not an honest reference cost.
- The official no-tool run recovered the exact planted solution on 3/3 easy,
  2/3 medium, and both completed hard instances. The OpenRouter key then hit
  its total limit before the third hard call, so API errors were not counted as
  failures and no formal harness verdict was asserted.

Increasing the modulus would make the same calculation more tedious without
introducing a new structural insight. The hard preset already requires 241 of
G9(c)'s permitted 300 exact operations, so this is not a defensible hardening
axis.

## Preserved evidence

| File | Contents |
|---|---|
| `rejected_gen_2009_14171.py` | complete deterministic prototype |
| `selftest_report.json` | local measurements, with G6 failing on the affine attack |
| `llm_loop_transcript.jsonl` | script-authored scored calls and later HTTP 403 redraws |
| `g9_*_transcript.jsonl` | earlier script-authored G9 attempts, all blocked by HTTP 403 |
| `REJECTED.md` | reviewable H rejection and paper citations |

The retained prototype can still be audited locally:

```bash
python3 rejected_gen_2009_14171.py
```

At the hard preset the local report records 0/200,000 uniform
statement-aware guesses, three weak heuristics at 0/8, the decisive affine
ansatz at 8/8, a 471-character certificate with 120 atomic elements, and a
241-operation intended route.
Those measurements do not override the explicit decoder or the scored oracle
successes; a large answer space is not evidence of hardness.

## Paper regimes checked

Section 4, Theorem 4 gives an `O(n^3 m)` algorithm when every lower quota is at
most two. Section 3.3, Observation 3 is `O(nm)` when the open set is supplied,
and Corollary 1 is `O(nm 2^m_quota)`. The prototype avoided those easy regimes
by retaining Theorem 2's quota-three and quota-four hospitals and growing the
number of colors. Its failure is instead specific to the affine promise added
by the generator.

Section 3.1, Theorem 1 reduces bounded-occurrence 3-SAT and could support a
future redesign, but it supplies worst-case hardness only. A new inverse-
planted SAT distribution would need its own attack and oracle evidence; this
result does not claim such a distribution is hard.
