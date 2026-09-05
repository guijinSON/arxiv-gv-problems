# Rejected: arXiv 2509.05822

Paper: [Chromatic numbers with open and nonzero local modular constraints](https://arxiv.org/abs/2509.05822)

## Decision

G and V pass for the retained construction, but H fails. This is specifically a
**Track B rejection**. It must not be presented as Track A: exact Gaussian
elimination recovers the certificate in polynomial time.

The retained module has been renamed `rejected_gen_2509_05822.py`. It inverse-generates
a 16-coordinate binary character, composes four factor identities to build a succinct
Cayley graph, and verifies the induced proper integer coloring by exact parity and
modular arithmetic. The witness is known by construction and verification does not
enumerate the graph's exponentially many vertices.

## STEP 0 result

Section 2 fixes the native object: a proper integer vertex labeling whose closed
neighborhood sums are nonzero modulo a fixed modulus. Theorem 3.3 turns a nonproper
modular labeling into a proper one by adding a suitably scaled ordinary proper
coloring. Theorem 3.4 is the decisive easy-regime result: for a `j`-regular graph,
if the modulus does not divide `j+1`, then the new chromatic number equals the
ordinary chromatic number. The retained construction uses modulus 3 and shipping
degree 637, so it lies exactly in that regime.

The certificate-producing mechanical algorithm is packed Gaussian elimination over
GF(2), with complexity `O(r*d^2)` scalar bit operations. At the named hard preset
(`d=625`, `r=637`) it solved 8/8 local trials, took 0.011669 seconds on average, and
used at most 6,266,787 counted scalar bit operations. The intended compact route is
to recognize the four-factor Kronecker incidence structure and solve four small
factor systems; it took at most 141 exact binary operations at that preset. This is
a genuine mechanical/compressed gap, so the existence of elimination did not itself
disqualify Track B.

What disqualifies it is that the compact route is too exposed. The coordinate names
display the tensor factors, and multiple no-tool oracles repeatedly reconstructed the
unique 16-name witness from the bare statement.

## Hardening evidence

The official `llm_loop_transcript.jsonl` was written by `scripts/harden.py`. API-error
rows are excluded below, as required.

| level | parameters | exact solves / scored attempts |
|---|---:|---:|
| easy | `d=81, extras=6` | 3/3 |
| medium | `d=256, extras=9` | 1/3 |
| hard | `d=625, extras=12` | 1/3 |
| escalated | `d=625, extras=24` | 2/3 |
| escalated | `d=625, extras=36` | 2/3 |
| escalated | `d=625, extras=48` | 2/3 |

Every completed level was defeated by at least one exactly verified answer. Increasing
only the number of redundant equations did not help. The final scheduled level
(`extras=60`) was not scored: OpenRouter returned HTTP 403 total-key-limit errors on
all retries, and the harness correctly aborted rather than converting infrastructure
failure into a hardness claim. No `hardened` verdict is claimed. The earlier, fully
scored failures are already enough to fail H; a structural-hint G9 run would be
strictly easier and was therefore not purchased or fabricated.

## Why another family was not substituted

The explicit graph families in Sections 4, 6, and 8 are solved by displayed formulas,
short periodic patterns, gcd tests, or direct recursive labelings. Their standard
mechanical work is linear in the written graph (often less), and the compact route is
the same formula or pattern, so there is no meaningful Track B compression gap.

Theorem 3.4 can transfer ordinary coloring difficulty to regular graphs, but the paper
does not give a hard planted distribution. Sampling a coloring first and then adding
compatible random edges would establish G, not distributional H: worst-case graph-
coloring hardness does not imply that such planted instances resist coloring
algorithms. The prior-triage suggestion therefore cannot support an honest Track A
claim without importing an unrelated hard-instance construction.

Accordingly, arXiv 2509.05822 is rejected for this benchmark on H, Track B. The
retained module, `.meta.json`, and oracle transcript preserve enough evidence to
revisit the decision if the benchmark later admits a less revealing encoding or a
different hardness standard.
