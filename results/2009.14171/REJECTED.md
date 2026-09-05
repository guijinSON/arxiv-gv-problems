# Rejected: the generated promise fails H on both tracks

The paper was read in full from its arXiv source. The candidate family used
Section 3.2, Theorem 2 (the theorem labelled `th:W-n` in the source): regular
Multicolored Independent Set is reduced to Hospital Residents with lower
quotas (HR-LQ). An independent transversal opens one quota-three vertex
hospital per color; the theorem's forward proof then gives the full stable
matching. Section 2, Observation 1 makes verification especially direct,
because every hospital in the reduction is accepted by exactly its lower
quota number of residents. The construction therefore clears G and V.

It does **not** clear H.

## Track A fails

The prototype inverse-generates each color-pair relation over `GF(p)` and
plants labels satisfying

```text
a*x_c + b*x_d + g = e (mod p).
```

The value `e` and all coefficients are displayed in the problem statement.
The excluded pairs form a perfectly consistent component, so three displayed
relations determine `x_0`, after which the color-0 relations determine every
other label. This is a deterministic polynomial-time decoder for every
instance in the generated distribution. Thus Theorem 2's W[1]-hardness for
generic regular multicolored graphs does not imply distributional hardness for
this promise, and Track A would be false.

## Track B also fails: the mechanical and compact routes coincide

The initial prototype reported connected components of the fully expanded
excluded-pair graph as its reference algorithm. At the hard preset
`n=60, p=101`, that implementation measured a mean of **721,140 graph
operations** and **0.071 seconds** over eight seeds. That is not the honest
input-native baseline: the rendered instance is already a succinct table of
affine equations, so expanding it into `n*p` vertices first is gratuitous.

On the representation actually handed to the solver, ordinary modular linear
elimination on the rows `(0,1)`, `(0,2)`, and `(1,2)`, followed by substitution
in the `(0,c)` rows, is both the standard mechanical algorithm and the claimed
shortcut. The module counts **241 exact field operations** for that route at
the hard preset (plus a linear scan of the 1,770 displayed rows). The compact
route is also **241 exact field operations**. The cost ratio is therefore 1,
not the claimed 721,140-to-241 compression gap. Increasing `p` would only turn
the task into harder hand arithmetic; it would not create a shorter structural
route, and the current 241-operation route is already near G9(c)'s 300-operation
cap.

The script-owned oracle run independently confirms the diagnosis. Before the
OpenRouter key reached its total limit, the evaluated no-tool models recovered
the exact planted affine solution on 3/3 easy instances, 2/3 medium instances,
and both completed hard instances (2/2). The third hard attempt could not be
scored because all redraws returned HTTP 403, so no formal `harden.py` verdict
was manufactured from the API failure. The completed calls are nevertheless
enough to show that the declared shipping distribution is not hard in Track
B's sense; the deterministic 241-operation decoder is the primary reason.

## Easy regimes checked in the paper

- Section 4, Theorem 4 solves HR-LQ/HR-LUQ in `O(n^3 m)` when every lower quota
  is at most two. The prototype correctly retained Theorem 2's quota-three and
  quota-four hospitals, so this is not the cause of rejection.
- Section 3.3, Observation 3 solves HR-LQ in `O(nm)` once the open set is fixed,
  and Corollary 1 gives `O(nm 2^m_quota)`. These results identify choosing open
  hospitals as the generic hard part, but they do not rescue this generated
  promise because its open hospitals are exposed by the affine decoder.
- Section 3.1, Theorem 1 supplies an alternative reduction from bounded-
  occurrence 3-SAT. It proves worst-case NP-hardness only; planting a random
  satisfying assignment would not, without separate distributional evidence,
  establish Track A. No unsupported average-case claim is substituted here.

The built module is retained as `rejected_gen_2009_14171.py`, together with
the local gate report and the script-authored transcript, so a future redesign
using a genuinely different generated distribution can be audited rather than
reconstructed from scratch.
