# Rejected: arXiv 1903.06981 — *Token Swapping on Trees*

Paper: <https://arxiv.org/abs/1903.06981> (version 5). I read the full paper and
its LaTeX source, not only the abstract.

## Decision

No family from this paper simultaneously clears G, H, V, and the no-tool output
caps. The prior-triage proposal—scramble a solved placement and return the
recorded swaps in reverse—does clear G and V, but it does **not** establish H.
This is a rejection on hardness, after considering both tracks; it is not a
rejection because a certificate is unavailable.

| candidate | G | V | Track A | Track B / cap |
|---|---:|---:|---:|---:|
| Any sorting sequence from an inverse scramble | yes | yes, exact replay | fails: Section 2.3 gives a direct polynomial sorting method, and the paper gives no hardness result for the random-scramble distribution | no hidden compact route is supplied by the instance |
| Section 4 happy-leaf constructions | yes | yes, exact replay | fails: the proof explicitly gives the certificate-producing schedule | mechanical and compact costs are comparable at the largest writable instance |
| Theorem 3 weighted-coloured spider reduction | yes for planted YES inputs | yes in principle, by replay | this is the paper's genuine NP-complete regime | its native swap-sequence witness exceeds the output and intended-route caps by many orders of magnitude |

## Step 0 discriminating test

### Unbounded sequence replay

Section 2.3 states that tokens on any connected graph can be sorted in
`O(N^2)` swaps: root a spanning tree, process vertices leaf-first, and home the
token for each leaf. Therefore a prompt asking for *any* sorting sequence is in
P on every generated instance. Recording the inverse scramble is a valid way
for the generator to know a witness, but it does not make that witness hard for
the solver to obtain. Adding a length bound changes the problem, but the paper's
NP-completeness theorem does not apply to the proposed non-backtracking random
scramble distribution; using worst-case hardness as an average-distribution
claim would violate Track A's rule.

### Section 4: explicit happy-leaf schedules

Theorem 1 defines `T_k` and explicitly constructs a solution of
`3*k^2/2 + 9*k` swaps. Theorem 2 defines `T_(k,b)` (odd `b`) and its paragraph
“A Clever Solution” explicitly tells the reader to exchange the buffer leaves
with `A_1`, then `A_2`, and so on, using

`S(k,b) = (b+1) * (binom(k+1, 2) + 2*k)`

swaps. Thus the paper's displayed exchange routine produces the certificate in
`Theta(S)` time. This disqualifies this distribution on Track A.

For Track B, use the most favourable raw encoding: one edge index per swap, so
one swap is one atomic answer element. The largest natural Theorem 2 preset
below the 256-atom cap is `k=7, b=5`, with 43 tree vertices and

`S(7,5) = 6 * (28 + 14) = 252` swaps.

The mechanical route emits/replays 252 swaps, while the compact route still has
to write those same 252 edge indices. Both are 252 essential output/replay
steps, already below the 300-operation cap. The ratio is 1:1, so this does not
create Track B's required “million mechanical operations versus a dozen after
the insight” gap. Increasing to `k=8, b=5` requires 312 swaps, exceeding both
the 256-atom answer cap and the 300-operation intended-route cap.

A custom macro such as “exchange this whole arm with the buffer” would shorten
the answer, but then the generated task is solved by decomposing the displayed
arm permutation into cycles and copying the exact `b+1`-exchange recipe already
printed in the proof. The algorithm producing that macro certificate is linear
in the (at most 256-element) macro answer, so its mechanical and compact routes
remain comparable. Treating the macro expander's internal swaps as the
mechanical cost would hide the actual algorithm that produces the declared
certificate, contrary to Track B's honesty requirement.

### Theorem 3: genuine hardness misses the caps

Section 5, Theorem 3 proves weighted coloured token swapping NP-complete on
spiders by reduction from maximum-degree-three Vertex Cover. This is the one
paper-central route that could support Track A. Its construction sets
`L_r = n^7`; the YES witness moves `L_r` red tokens, each through
`8*m + (L_r - 1)` swaps. Even at the proof's smallest stated inequality regime,
`n=5`, this phase alone contains at least

`5^7 * (5^7 - 1) = 6,103,437,500`

swaps. That is far above 256 atomic elements and 300 intended exact operations.
The paper's NP-membership argument uses an ordinary quadratic-length list of
swap operations checked by execution; it does not provide a bounded symbolic
certificate that an exact checker can validate without expanding the path.

Returning only the underlying Vertex Cover would not repair this: it would
replace the requested native reconfiguration witness with the source problem's
certificate, and a checker that merely invokes the reduction theorem would
violate the witness rule. Replaying the reduction's actual swaps restores V but
restores the multi-billion-operation cap failure as well.

## Easy regimes checked

The paper explicitly identifies exact polynomial algorithms for paths and
stars in Sections 2.5–2.6, weighted coloured paths and stars in Section 6, and
brooms in Section 7. It also gives three polynomial-time 2-approximations for
general trees in Section 2.4. None of these regimes can support Track A. Their
certificates are ordinary swap lists, so under the 256-element output cap their
mechanical output cost cannot be separated substantially from the route a
solver must write; they do not rescue Track B either.

## Failed gate and track summary

- **G:** available by inverse generation or by the paper's constructive proofs.
- **V:** available by exact edge-legality, cost, and final-colour replay.
- **H / Track A:** fails for the writable constructions because the paper gives
  the certificate-producing algorithm explicitly; unsupported for random
  scrambles because the theorem is worst-case, not distributional.
- **H / Track B:** fails for writable raw witnesses because the measured route
  lengths are 252 versus 252 operations at the largest fitting Section 4
  preset. The actual NP-hard construction would require at least
  6,103,437,500 swaps even at `n=5`, so it fails G9(c) rather than yielding a
  shippable Track B instance.

Because this decision was reached at Step 0, no generator or fabricated gate
reports/transcripts were produced.
