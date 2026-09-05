# Rejected: arXiv 1105.2672

Paper: [The chromatic spectrum of 3-uniform bi-hypergraphs](https://arxiv.org/abs/1105.2672), Ping Zhao, Kefeng Diao, and Kaishun Wang.

## Decision

The family fails **H on both tracks**. G and V are available: a coordinate
partition is known by construction, and a proposed partition is checked exactly
by confirming that it covers every vertex, uses the requested number of colors,
and gives every 3-element bi-edge exactly two colors. The obstacle is not the
witness rule.

It fails Track A because the paper gives the answers explicitly for its entire
constructed distribution. Section 1 defines a proper coloring of a bi-edge;
Theorem 2.2 states that the coordinate partitions are all strict colorings of
the Cartesian construction, Theorem 2.3 uses repeated coordinates to prescribe
their multiplicities, and Theorem 3.2 carries the same feasible set and spectrum
to the sparse derived construction. There is therefore a known linear-time
method on exactly the generated objects, not merely on an easy special case
outside the claimed regime.

It also fails Track B because the mechanical algorithm and the compact route
are the same operation. For the tested sparse object `H*_{23,23}` there are 69
vertices. The paper's mechanical method reads one displayed coordinate and
places each vertex in that coordinate class: **69 coordinate reads/assignments,
O(|X|)**. Measured over 100,000 runs, constructing that partition took
**1.01e-5 seconds per instance** in Python. The purported compact route is
"group equal first coordinates" and still needs **69 placements** to write the
answer. Thus the mechanical cost is 69 operations and the compact route length
is 69 output placements; there is no compression gap to test.

## Why relabeling does not rescue it

The retained experimental generator applies an invertible affine relabeling and
deletes a uniformly sampled set of edges while carrying the known partition.
That makes a large set-partition answer space and an exact verifier, but it does
not supply honest hardness. With affine coordinates present, each bi-edge's
three point-pair directions contain the two hidden coordinate kernels; comparing
two ordinary bi-edges recovers them directly and partition evaluation is still
linear. Scanning all 1,500 edges (the experiment measured 4,500 pair directions
and about 27,000 field operations) is an artificially weak baseline because the
two-edge method is available. If the coordinates are removed and vertices are
made opaque, the paper provides neither a Track A distributional-hardness result
nor a short Track B route; that would manufacture a generic CSP rather than test
the paper's construction.

The preliminary structure-aware sampling result (0 hits in 200,000 conditioned
partition samples) therefore does not change the decision: cardinality is not
difficulty when the theorem prints a valid partition in linear time.

## Retained evidence

`rejected_gen_1105_2672.py` is the experimental builder and is intentionally
kept as required. Its local G1--G8 experiments passed after the candidate prior
was corrected to condition on the first edge. The attempted oracle transcript is
also retained, but it contains only HTTP 403 `Key limit exceeded` errors from
OpenRouter and was not used as evidence for this rejection. No G9 or oracle
failure is being claimed.
