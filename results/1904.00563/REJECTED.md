# Rejected: arXiv:1904.00563

Paper: Kenta Noguchi, [“Proper 3-orientations of bipartite planar graphs with minimum degree at least 3”](https://arxiv.org/abs/1904.00563).

## Decision

The constructed family passes generation and exact verification, but it fails the mandatory Track B no-tool-hardness gate G9(b). Track A is unavailable, and the one permitted Track B escalation was also solved when given the structural hint. No further escalation or hand-tuning is allowed by the task protocol.

## Paper facts used at triage

Section 1 defines an orientation, indegree, proper orientation, and proper orientation number. Theorem 2 states that a bipartite graph `G[X,Y]` with maximum average degree at most `2k` and degree at least `k+1` on `X` has proper orientation number at most `k+1`. Its proof first invokes Hakimi's bounded-indegree orientation construction, then reverses suitable `X -> Y` arcs until every `X` vertex has indegree `k+1`. Lemma 6 gives the planar bipartite density bound, and Theorem 3 applies Theorem 2 with `k=2` to bipartite planar graphs of minimum degree at least 3.

That proof is constructive and polynomial-time, so it rules out a Track A claim. It does not by itself rule out Track B; the family was therefore built and measured before rejection.

## Attempted family

The generator inverse-constructed a prescribed proper 3-orientation on a randomly relabelled cylindrical quadrangulation. Boundary `X` vertices have all three edges directed inward. Each interior `X` vertex chooses one outgoing edge to a target-one `Y` vertex, so the remaining three edges point inward. A certificate is a bijection from the interior `X` vertices to adjacent target-one `Y` vertices. The exact checker expands this compact encoding into every arc, recomputes all indegrees, and scans every edge for properness; it never reads the planted answer.

Generation and verification were not the failure: all planted witnesses verified over every preset and seed tested, all five corruption classes were rejected for distinct reasons, and structure-aware random bijections had 0 successes in 200,000 trials at both attempted shipping levels.

## Mechanical cost and compact route

For this prescribed subfamily, the domain-standard algorithm is Hopcroft–Karp bipartite perfect matching, with complexity `O(E sqrt(V))`.

| attempted level | parameters | measured mechanical cost | compact route |
|---|---:|---:|---:|
| easy | `n=64, height=5, jitter=31` | 2,984 counted edge/queue/pair operations on average over 8 seeds; 0.00029 s | at most 189 selections/parity updates |
| medium | `n=80, height=5, jitter=31` | 3,136 counted operations on average over 8 seeds; 0.00032 s | at most 213 selections/parity updates |

The compact route keeps eligible edges whose endpoints have equal eligible degree. They form three even cycles, and alternating edges on each cycle give a perfect matching and hence the orientation. This roughly 15-to-1 operation gap was large enough to justify trying Track B, but it was not large enough to survive disclosure of the insight. Thus the rejection is not the invalid argument “a polynomial-time algorithm exists”; it is the observed failure of the required hinted-oracle gate.

## Failed gate evidence

The bare easy run was `hardened`: GPT-5.6 Terra returned a duplicate label, Gemini 3.1 Pro returned the wrong length, and Claude Sonnet 5 exhausted its response budget without emitting a witness. Provider timeouts were recorded as errors and did not count.

The G9 structural-hint arm at easy was solved by Gemini 3.1 Pro and Grok 4.6 (2 solved out of 3 attempts). Under the protocol's single allowed move, the family was raised to the named medium preset and both bare and hinted retests were started. Gemini failed the first bare-medium attempt but solved the first hinted-medium attempt. That single valid hinted witness is already enough to fail G9(b), so the remaining calls were stopped and no placebo arm was run.

## Gates

- **G:** passes by inverse construction; the matching phase is chosen before relabelling and no solver is called by `make_instance`.
- **H, Track A:** fails because Theorem 2's proof gives a polynomial-time construction.
- **H, Track B / G9(b):** fails because the structural hint solved both easy and the one permitted medium escalation.
- **V:** passes; verification is an exact linear scan of the candidate orientation and graph.

The paper may support a different benchmark family, but this prescribed-orientation/cycle-decomposition family must not ship under the stated protocol.
