# One sample question per generator

Rendered from every shipped generator at its **shipping** preset, seed `42`. Each planted answer was checked with the module's own `verify()` before inclusion.

- generators rendered: **39**
- all planted answers verify: **True**

Full, untruncated questions and answers are in [`samples.jsonl`](samples.jsonl); long instance data is elided below only for readability.

---

## 2001.09362 — $S$-packing chromatic vertex-critical graphs

*graph structures* · [paper](https://arxiv.org/abs/2001.09362) · preset `medium` `{"n": 22, "clue_density": 0.4, "filter_nodes": 100000, "attack_filter": true}` · search space ≈ `18444908…(680 digits)`

```text
S-packing coloring of a compactly defined graph

There are q = 22 available color labels: the integers 1 through 22.
Use the S-packing sequence S = (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1).  An S-packing
coloring assigns one color label to every vertex, and two distinct vertices
with the same label must have graph distance strictly greater than 1.  Thus,
for this S, adjacent vertices must have different labels (ordinary proper
vertex coloring).

The undirected graph has these vertices:
  * anchors A[0], ..., A[21];
  * cells C[r,c] for 0 <= r < 22 and 0 <= c < 22.
All indices are 0-based.  Its edges are exactly the following; there are no
others:
  1. Every two distinct anchors are adjacent.
  2. Two distinct cells are adjacent exactly when they share a row or share a
     column: C[r,c]--C[r,d] for c != d, and C[r,c]--C[t,c] for r != t.
  3. For every clue (r,c)=s below, C[r,c] is adjacent to every anchor A[t]
     with t != s, and is not adjacent to A[s].

Clues (each s is an anchor INDEX, not an output color label):
  (0,0) = 3
  (0,2) = 8
  (0,3) = 11
  (0,5) = 6
  (0,9) = 20
  (0,11) = 12
  (0,12) = 2
  (0,14) = 4
  (0,15) = 14
  (0,16) = 21
  (0,18) = 10
  (0,19) = 19
  (1,0) = 12
  (1,1) = 16
  (1,6) = 7
  (1,7) = 5
  (1,11) = 13
  (1,12) = 14
  (2,0) = 1
  (2,3) = 21
  (2,6) = 8
  (2,8) = 12
  (2,11) = 15
  (2,13) = 17

    ... [173 lines of instance data omitted] ...

the same output label as A[s].  Output labels may be globally permuted; any
valid coloring is accepted.

Your answer must contain exactly 506 comma-separated base-10 integers, in
this order: A[0] through A[21], then all cells in row-major order
C[0,0], C[0,1], ..., C[21,21].  Order matters.  Every integer must
be in the inclusive range 1..22; repeats are allowed unless an edge forbids
them.

Give your final answer inside <answer></answer> tags, as one comma-separated
list.  Syntax example: <answer>1, 2, 3</answer> (your actual list must contain
exactly 506 integers).  Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[6, 1, 7, 15, 4, 20, 21, 19, 18, 17, 8, 5, 2, 9, 16, 14, 22, 13, 12, 11, 10, 3, 15, 17, 18, 5, 19, 21, 12, 6, 22, 10, 1, 2, 7, 9, 4, 16, 3, 20, 8, 11, 13, 14, 2, 22, 14, 13, 1, 6, 19, 20, 4, 7, 10, 9, 16, 8, 12, 18, 21, 5, 17, 3, 15, 11, 1, 6, 20, 3, 7, 12, 18, 21, 2, 19, 9, 14, 10, 13, 11, 5, 16, 22, 15, 4, 17, 8, 22, 5, 7, 2, 8, 4, 17, 14, 15, 13, 21, 10, 11, 16, 1, 9, 12, 19, 20, 18, 6, 3, 18, 12, 5, 9, 3, 14, 20, 17, 1, 22, 11, 15, 13, 4, 6, 19, 7, 2, 21, 16, 8, 10, 21, 18, 3, 11, 2, 15, 4, 9, 10, 8, 7, 17, 12, 19, 20, 13, 1, 14, 6, 5, 16, 22, 8, 21, 6, 17, 20, 16, 11, 22, 18, 5, 15, 1, 14, 10, 2, 3, 4, 13, 12, 7, 19, 9, 12, 4, 9, 18, 5, 17, 14, 19, 13, 16, 3, 6, 1, 11, 22, 21, 8, 15, 2, 10, 7, 20, 20, 14, 10, 21, 13, 9, 3, 5, 17, 15, 2, 11, 6, 12, 7, 8, 22, 4, 1, 19, 18, 16, 17, 19, 16, 15, 4, 7, 13, 1, 6, 21, 12, 20, 2, 14, 8, 10, 18, 11, 9, 22, 3, 5, 14, 15, 21, 6, 18, 13, 2, 11, 19, 12, 16, 8, 4, 20, 10, 7, 9, 3, 22, 17, 5, 1, 11, 3, 4, 12, 10, 20, 5, 7, 8, 18, 19, 22, 9, 17, 15, 1, 13, 6, 16, 14, 21, 2, 6, 9, 17, 10, 21, 22, 15, 4, 3, 2, 8, 16, 5, 1, 19, 14, 20, 12, 7, 13, 11, 18, 5, 1, 13, 19, 6, 11, 7, 8, 16, 14, 17, 18, 15, 22, 3, 12, 2, 9, 10, 21, 20, 4, 10, 20, 2, 1, 22, 18, 8, 16, 12, 3, 13, 21, 17, 5, 14, 15, 6, 7, 11, 9, 4, 19, 3, 7, 12, 20, 16, 8, 9, 10, 11, 17, 22, 13, 19, 2, 21, 4, 5, 1, 18, 15, 14, 6, 19, 10, 11, 8, 12, 2, 1, 15, 7, 9, 5, 4, 3, 18, 16, 6, 1  … (1817 chars total)
```

---

## 2002.10145 — Hardness of equations over finite solvable groups under the exponential   time hypothesis

*constraint satisfaction* · [paper](https://arxiv.org/abs/2002.10145) · preset `easy` `{"n": 140, "avg_degree": 9.0, "attack_restarts": 32, "backtrack_floor": 10000}` · search space ≈ `75885503…(82 digits)`

```text
FIXED 4-COLOURING WITNESS PROBLEM

The graph has 140 vertices, numbered 0 through 139 inclusive.
Each line in the edge list is one undirected edge 'u v'.
There are no loops. Edge order and endpoint order have no meaning.
Assign exactly one integer colour in the inclusive range 1..4 to every vertex.
For every listed edge u v, the two endpoint colours must be different.
Colours may be reused on nonadjacent vertices; there is no balance requirement.
Your output order matters: entry i is the colour of vertex i (0-indexed).
The graph contains a 4-clique used only to remove global colour-name symmetry.
The following anchor colours are mandatory:
  vertex 0 -> colour 1
  vertex 1 -> colour 2
  vertex 2 -> colour 3
  vertex 3 -> colour 4

n = 140
m = 630
edges:
0 1
0 2
0 3
0 68
0 88
0 89
1 2
1 3
1 29
1 40
1 65
1 69
1 90
2 3
2 14
2 20
2 23
2 38
2 48
2 67
2 72
3 7
3 10
3 26
3 48
3 62

    ... [599 lines of instance data omitted] ...

122 133
122 138
123 135
126 131
136 137
end edges

Give your final answer inside <answer></answer> tags as exactly 140 comma-separated integers, in vertex-number order.
Do not include brackets, vertex labels, explanations, or any other text inside the tags.
For format only, a hypothetical 4-vertex answer would be:
<answer>1, 2, 3, 4</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[1, 2, 3, 4, 4, 3, 2, 3, 4, 4, 2, 3, 4, 4, 2, 1, 1, 3, 3, 4, 1, 4, 2, 4, 3, 1, 2, 1, 2, 4, 1, 4, 4, 3, 1, 1, 2, 3, 2, 2, 3, 3, 1, 4, 4, 4, 2, 3, 2, 2, 4, 4, 4, 3, 2, 1, 1, 3, 1, 3, 4, 1, 3, 1, 2, 3, 4, 4, 3, 1, 2, 2, 1, 1, 3, 1, 4, 3, 3, 3, 4, 1, 2, 2, 1, 1, 3, 1, 4, 3, 4, 1, 2, 2, 3, 4, 2, 4, 3, 2, 1, 3, 1, 1, 3, 2, 4, 3, 3, 4, 2, 2, 4, 2, 2, 1, 2, 3, 3, 1, 4, 3, 1, 2, 1, 1, 2, 3, 2, 4, 2, 4, 4, 2, 2, 1, 1, 4, 3, 1]
```

---

## 2007.09736 — Total coloring and efficient domination applications to non-Cayley non-Schreier vertex-transitive graphs

*graph structures* · [paper](https://arxiv.org/abs/2007.09736) · preset `medium` `{"n": 40, "q": 6}` · search space ≈ `57055838…(187 digits)`

```text
Partition a graph into efficient dominating sets

The input is a finite undirected simple graph.  Its vertices are the integers
0 through 239, inclusive.  Each unordered edge is listed once as u-v;
there are no loops, and the order of endpoints and edges has no meaning.

A set S of vertices is an efficient dominating set (an E-set) when every
vertex outside S has exactly one neighbor in S.  Find a partition of all
vertices into exactly 6 E-sets, named by colors 0 through 5.  In other
words, assign one color c[v] to each vertex v so that the closed neighborhood
consisting of v and all its neighbors contains every color 0 through 5
exactly once.  Consequently adjacent vertices have different colors.  Every
color must occur exactly 40 times.

Every vertex has degree 5.  The graph has 240 vertices and
600 edges:
58-169 147-157 78-149 44-50 5-71 166-239 199-201 231-235 65-203 137-138
60-97 162-215 142-225 25-108 24-155 118-191 181-204 40-223 75-195 89-208
136-209 61-179 67-73 46-211 95-190 113-177 34-175 50-213 8-23 19-221
159-196 70-207 54-211 33-208 83-94 120-163 107-149 63-170 58-78 168-216
17-198 6-116 125-230 14-93 87-198 64-203 1-178 29-203 105-135 155-158
107-168 33-131 57-66 55-145 125-193 68-185 135-144 225-229 105-185 121-159
217-222 171-219 88-177 94-128 4-45 51-149 90-169 164-217 59-151 80-236
29-50 64-66 28-48 123-130 136-148 44-221 23-204 22-61 27-65 32-114
188-229 3-84 151-169 73-76 131-167 131-206 138-187 161-198 46-152 24-228
100-167 53-216 45-132 115-228 104-191 39-91 124-140 170-174 4-163 65-197
59-62 37-122 49-145 158-195 81-128 127-150 24-133 4-10 22-200 3-78
42-88 150-151 146-180 142-205 10-192 71-193 111-190 148-197 33-98 204-211
151-232 98-199 52-174 25-40 7-187 5-6 19-51 129-235 30-44 101-172
96-139 220-238 147-182 50-119 34-38 110-124 168-223 51-161 173-201 9-152
124-125 43-106 210-218 13-55 54-64 99-103 47-115 36-192 99-104 83-220
71-85 148-229 124-235 155-231 43-117 143-160 108-207 161-171 69-81 101-198
170-189 79-103 80-176 146-231 204-205 63-91 61-72 0-34 45-122 1-23
114-152 102-181 22-40 75-192 53-154 89-194 104-230 22-110 100-142 79-190
43-98 3-101 82-202 162-172 16-112 17-68 148-225 132-233 0-189 61-97
86-119 129-162 37-126 91-180 59-90 113-127 21-134 40-231 69-136 78-182
76-139 21-185 52-202 15-221 9-162 147-201 23-171 209-239 31-84 156-165
109-123 88-109 46-139 31-227 20-212 165-193 28-186 177-220 63-77 114-237
52-189 164-186 26-85 56-109 39-216 175-214 20-191 31-207 187-236 127-195
26-79 114-183 139-214 33-49 7-72 143-192 96-197 198-238 81-136 18-105
26-107 107-193 36-197 106-200 106-208 28-213 41-120 5-70 110-210 19-73
111-173 7-64 84-180 69-92 188-218 167-216 38-118 17-84 129-153 171-223
31-96 69-132 100-120 158-206 6-214 126-236 186-232 2-17 28-183 4-234
37-121 146-176 68-219 11-56 105-189 20-237 36-149 11-102 34-49 121-192
2-209 28-199 18-27 82-184 25-154 122-202 18-41 100-227 133-137 123-204

    ... [29 lines of instance data omitted] ...

74-118 75-214 58-172 93-116 42-195 128-130 61-129 81-188 39-43 0-11
55-115 99-134 80-234 178-212 63-155 47-53 126-205 86-156 142-237 144-153

Order matters only by vertex index: the first output integer is c[0], the
second is c[1], and so on through c[239].  Color names may be globally
permuted.  Repeated colors are required, but there must be exactly 240
comma-separated integers, each in the inclusive range 0..5.

Give your final answer inside <answer></answer> tags, as a comma-separated list
of the 240 colors in vertex order.
Example of the syntax: <answer>0, 2, 1, 0</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[1, 2, 0, 2, 2, 4, 5, 3, 5, 1, 3, 4, 0, 1, 2, 3, 0, 3, 4, 5, 3, 4, 1, 3, 3, 5, 2, 5, 5, 2, 4, 1, 1, 5, 0, 5, 2, 0, 5, 2, 3, 0, 5, 0, 1, 5, 2, 2, 0, 4, 3, 1, 0, 3, 1, 0, 0, 1, 3, 3, 3, 4, 2, 5, 0, 3, 5, 2, 2, 3, 3, 1, 2, 4, 1, 0, 0, 1, 5, 1, 0, 0, 5, 5, 4, 0, 4, 4, 2, 0, 5, 3, 2, 4, 2, 5, 5, 0, 3, 5, 2, 1, 5, 4, 1, 3, 4, 3, 4, 3, 0, 3, 2, 5, 4, 4, 3, 1, 4, 5, 1, 1, 3, 5, 3, 4, 2, 3, 1, 5, 4, 0, 4, 2, 3, 5, 5, 1, 0, 3, 2, 2, 5, 4, 0, 2, 5, 3, 1, 4, 2, 4, 5, 3, 1, 0, 1, 1, 2, 2, 1, 2, 2, 4, 4, 0, 5, 4, 1, 1, 4, 4, 0, 1, 3, 2, 3, 4, 1, 3, 0, 2, 0, 3, 2, 0, 1, 5, 2, 2, 0, 2, 5, 5, 2, 4, 5, 0, 5, 2, 5, 4, 1, 4, 0, 1, 3, 2, 1, 2, 5, 4, 4, 4, 1, 3, 5, 3, 3, 1, 1, 0, 0, 0, 2, 3, 0, 3, 5, 4, 0, 4, 0, 1, 1, 1, 4, 0, 0, 4]
```

---

## 2008.09415 — Acyclic, Star and Injective Colouring: A Complexity Picture for H-Free Graphs

*graph structures* · [paper](https://arxiv.org/abs/2008.09415) · preset `easy` `{"n": 24}` · search space ≈ `620448401733239439360000`

```text
Acyclic colouring of a co-bipartite graph

The graph has 2n vertices, where n = 24.  They are split into
A1,...,A24 and B1,...,B24.  Every two distinct A-vertices are adjacent,
and every two distinct B-vertices are adjacent.  Cross-adjacency is given by
the matrix below: entry 1 means A_i is adjacent to B_j, and entry 0 means they
are nonadjacent.  The graph is undirected, simple, and has no loops.

    B1 B2 B3 B4 B5 B6 B7 B8 B9 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19 B20 B21 B22 B23 B24
A1: 0 0 0 1 1 0 0 1 0 1 0 1 1 0 1 0 0 1 1 0 0 0 1 0
A2: 1 0 0 1 1 0 0 0 0 0 0 0 0 0 0 0 1 1 0 0 1 0 0 1
A3: 0 1 0 1 0 1 0 0 0 0 0 1 0 1 0 0 0 1 0 0 1 0 0 0
A4: 1 1 1 0 0 0 0 0 0 1 0 0 0 1 0 1 0 0 0 0 0 0 1 0
A5: 1 1 0 1 0 1 0 1 0 0 1 0 0 0 1 1 0 1 0 0 0 0 1 0
A6: 0 0 0 1 0 0 0 1 1 0 0 0 0 0 1 0 0 0 1 0 0 0 1 0
A7: 0 0 1 1 1 0 0 1 1 0 1 1 0 0 0 0 0 0 0 0 0 0 0 0
A8: 0 1 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0
A9: 0 0 0 0 1 0 1 0 0 1 0 0 0 0 0 0 0 0 1 1 0 0 0 1
A10: 1 0 0 0 0 0 0 0 0 0 1 0 0 1 0 1 0 1 0 1 0 1 0 0
A11: 0 0 0 1 0 0 0 1 0 0 1 0 1 0 0 1 1 0 0 1 1 0 0 0
A12: 0 0 0 0 0 1 1 0 0 0 1 0 0 1 1 0 0 0 0 1 0 0 0 1
A13: 0 1 0 1 0 0 0 0 0 0 1 1 0 1 0 1 0 1 0 0 0 0 0 1
A14: 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 1 1 0 0 1 0 1 1 1
A15: 0 0 0 0 0 1 0 1 0 0 1 1 1 0 0 0 0 0 1 1 0 1 1 0
A16: 0 0 0 0 1 0 1 1 1 0 0 0 1 0 1 1 1 0 0 1 0 1 1 0
A17: 1 1 0 0 0 1 0 0 0 0 0 0 1 0 1 0 1 0 0 0 1 0 0 0
A18: 0 0 0 0 0 0 0 0 0 1 0 0 1 0 0 0 0 0 1 0 1 0 0 1
A19: 0 0 0 1 1 1 0 0 1 0 1 0 0 0 0 0 0 1 0 0 1 1 0 1
A20: 0 0 0 1 1 1 1 0 0 0 0 0 1 0 1 0 0 0 0 1 0 1 1 0
A21: 0 0 0 0 1 1 0 1 0 1 0 1 0 0 1 1 1 0 1 0 0 1 1 0
A22: 0 0 0 0 1 0 1 1 1 1 0 1 0 0 1 0 0 1 1 1 0 1 0 0
A23: 0 0 1 0 0 0 0 0 1 1 0 0 1 0 0 0 0 0 0 0 0 0 0 1
A24: 1 0 0 1 0 0 0 0 0 0 0 1 0 1 1 0 0 1 0 0 0 1 0 0

A proper colouring assigns one of the colours 1,...,24 to every vertex and
never gives adjacent vertices the same colour.  It is acyclic when, for every
two colours, the subgraph induced by all vertices having either colour contains
no cycle.  Find an acyclic colouring using at most 24 colours.

Because each of A and B is a clique of size 24, every such colouring must pair
each A_i with exactly one B-vertex.  Report the pairing as exactly 24 integers
p1,...,p24: p_i = j means A_i and B_j receive the same colour.  The integers
must be a permutation of 1,...,24; order is by A-index, and indices are
1-based.  Repetitions are forbidden.  Colour names do not need to be reported.

Give your final answer inside <answer></answer> tags, as comma-separated integers.
Example format: <answer>3, 1, 2</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[16, 6, 19, 24, 14, 11, 18, 12, 15, 17, 2, 13, 22, 7, 10, 3, 23, 5, 20, 8, 9, 1, 4, 21]
```

---

## 2011.04650 — Large rainbow matchings in edge-colored graphs

*graph structures* · [paper](https://arxiv.org/abs/2011.04650) · preset `medium` `{"n": 32, "choices": 5}` · search space ≈ `23283064365386962890625`

```text
Find a full rainbow matching in a coloured bipartite multigraph

There are three separately labelled sets, each of size 32:
- colours 0 through 31;
- left vertices L0 through L31; and
- right vertices R0 through R31.

Each input line `c l r` is one edge from left vertex Ll to right vertex Rr,
with colour c.  All labels are 0-indexed and both bounds are inclusive.
Different colours may give parallel edges with the same endpoints.  No exact
triple is repeated.  The order of the input lines has no meaning.

Choose exactly 32 listed triples so that every colour occurs exactly once,
every left vertex occurs exactly once, and every right vertex occurs exactly
once.  Thus the chosen edges are pairwise vertex-disjoint and have pairwise
distinct colours.  The order of your chosen triples has no meaning, and you
may not repeat a triple.

The 160 input edges are:
26 31 7
11 10 2
12 25 18
23 10 6
16 17 17
1 9 10
2 13 25
19 30 24
22 2 31
17 1 1
13 25 18
24 29 3
19 12 29
10 27 2
16 30 14
14 26 31
7 16 5
9 12 9
27 8 28
21 25 2
11 14 16
25 2 25
29 3 10
1 11 11
2 4 26
31 14 31

    ... [127 lines of instance data omitted] ...

30 0 10
0 16 30
18 22 25
28 8 4
28 12 8
3 9 0
5 20 26

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly 32 triples `[c,l,r]` using decimal integers.
Example of the syntax: <answer>[[0,2,1],[1,0,3]]</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[[0, 26, 23], [1, 5, 25], [2, 10, 7], [3, 15, 22], [4, 25, 13], [5, 11, 0], [6, 22, 19], [7, 6, 15], [8, 19, 5], [9, 12, 9], [10, 16, 28], [11, 9, 18], [12, 28, 17], [13, 14, 31], [14, 24, 16], [15, 20, 21], [16, 30, 14], [17, 1, 1], [18, 13, 29], [19, 18, 20], [20, 2, 11], [21, 17, 26], [22, 21, 12], [23, 3, 2], [24, 29, 3], [25, 4, 30], [26, 27, 24], [27, 31, 6], [28, 8, 4], [29, 23, 8], [30, 0, 10], [31, 7, 27]]
```

---

## 2102.01986 — A unified half-integral Erd\H{o}s-P\'{o}sa theorem for cycles in graphs labelled by multiple abelian groups

*graph structures* · [paper](https://arxiv.org/abs/2102.01986) · preset `standard` `{"n": 96, "bits_num": 1, "bits_den": 1, "min_bits": 24}` · search space ≈ `14227161…(437 digits)`

```text
Exact-value cycle in an edge-labelled graph

The graph is finite, undirected, and simple.  Its vertices are the integers
0 through 291.  Every edge has a label in the cyclic
additive group Z/79228162514264337593543950336Z.  The value of a cycle is the sum of the
labels of all its edges, reduced modulo 79228162514264337593543950336; edge traversal
direction does not change a label.

A simple cycle uses distinct vertices and returns from its last listed vertex
to its first.  Find any simple cycle containing exactly
193 distinct vertices whose value is exactly
67441492798331309534631366419 modulo 79228162514264337593543950336.

There are 388 edges.  Each following line is
"endpoint endpoint label".  Endpoints are 0-based.  Edge order and endpoint
order carry no meaning.

51 142 47046569641945067502819358186
29 136 27869203941535925169614383044
239 60 5033183506188869533867093224
29 182 2147245866444821860074651190
161 28 36164632185286825584739783207
180 88 18138637184330494521925170870
255 126 7700343639031059471792907681
69 115 31054110891566997029751067949
122 101 36468979662460210155130442192
218 203 30025343915945692096708655824
59 149 13805206464402040286729121753
169 212 40832894666417405295036819092
38 1 16805865891210994866545561223
217 225 43023324265596570770670560569
34 200 45312384253024649392281977680
44 185 18634772600500858744926288588
109 205 32875125693003341732211710041
259 125 29023531709741127756887672976
249 108 49202853697552254764671919685
201 74 4450413911979969213799400295
284 46 75310739344589893700293856719
99 215 58726363181201715802313555997
225 169 70472382096025143924464451879
83 286 612426260756791134552839074
246 238 19080502030574260165330425514
239 14 19854998567497343348325162132
195 236 33262556783897283410651181777
70 48 53397303003254472721123943596

    ... [357 lines of instance data omitted] ...

240 50 35075971754408685882765011567
143 216 77708419306978291030513451768
46 126 10748413337003100725406035226

Represent the cycle as a JSON array of exactly 193
distinct vertex IDs in cyclic order.  Do not repeat the first vertex at the
end.  Any starting vertex and either direction are allowed; repeats are not.

Give your final answer inside <answer></answer> tags, as one JSON array of
integers.
Example: <answer>[3, 17, 42]</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[35, 257, 132, 1, 38, 210, 227, 234, 81, 39, 276, 20, 76, 91, 182, 29, 136, 3, 261, 124, 94, 161, 84, 113, 106, 42, 139, 114, 199, 0, 122, 101, 258, 177, 187, 188, 99, 215, 231, 273, 105, 196, 253, 44, 138, 134, 289, 218, 203, 77, 229, 263, 19, 202, 88, 180, 26, 111, 209, 47, 60, 239, 260, 23, 168, 107, 7, 15, 214, 279, 17, 148, 259, 125, 256, 152, 179, 232, 280, 30, 169, 225, 217, 278, 198, 174, 226, 160, 206, 163, 22, 66, 144, 189, 252, 262, 43, 119, 69, 115, 45, 63, 33, 12, 190, 242, 201, 98, 181, 157, 151, 250, 112, 40, 153, 83, 286, 184, 70, 271, 236, 267, 171, 127, 62, 282, 150, 78, 75, 287, 82, 129, 211, 61, 59, 149, 97, 90, 166, 72, 46, 126, 255, 167, 118, 264, 96, 137, 245, 27, 223, 34, 200, 186, 246, 103, 25, 11, 65, 13, 178, 145, 216, 92, 109, 205, 57, 244, 222, 251, 165, 140, 183, 159, 16, 272, 175, 32, 162, 95, 269, 86, 51, 249, 108, 50, 240, 130, 8, 128, 155, 9, 283]
```

---

## 2104.04330 — Equiangular lines in Euclidean spaces: dimensions 17 and 18

*geometric configurations* · [paper](https://arxiv.org/abs/2104.04330) · preset `easy` `{"n": 720, "margin_tenths": 50}` · search space ≈ `34087835…(36 digits)`

```text
EQUIANGULAR INTEGER-VECTOR SUBSET

There are 720 labelled vertices, numbered 0 through 719.  Their undirected
simple graph is encoded below by one hexadecimal integer.  Ignore whitespace
between its lines.  Expand it to exactly 258840 binary bits, preserving
leading zeroes, then discard the first 0 padding bit(s).
The remaining 258840 bits give edges in this exact order:
    (0,1),(0,2),...,(0,719),(1,2),(1,3),...,(1,719),...,
    (718,719).
A bit is 1 exactly when that unordered pair is an edge.  There are no loops.

This graph also defines 720 integer vectors x_0,...,x_719 without listing
their many zero coordinates.  There is one coordinate p_(a,b) for every pair
0 <= a < b < 720.  At p_(a,b), vector x_a has value 1, vector x_b has value 1
if a and b are adjacent (otherwise 0), and every other vector has value 0.
For each i, add private coordinates used only by x_i, each with value 1, until
the squared length of x_i is exactly 719.  This is always possible because
the pair coordinates contribute at most 719 to that squared length.

Consequently, every x_i has squared length 719, and for distinct i,j:
    x_i dot x_j = 1  if i and j are adjacent,
    x_i dot x_j = 0  otherwise.
Thus a set of indices gives equiangular lines with common absolute normalized
inner product 1/719 exactly when every two of its vertices are adjacent.

Find exactly 18 DISTINCT indices whose vectors are pairwise equiangular; in
graph terms, find a clique of size 18.  The order of the submitted indices
does not matter.  Repeated indices are forbidden.  Bounds are inclusive:
every index must lie from 0 through 719.

HEX-ENCODED UPPER TRIANGLE (64710 hex digits)
594fba5799e6f794ca2e8f7c72c978411eb135904ccf2047e27ea0315b940990e3937b27376908342e57f1aa17c2ac5587fbd669b40a26e037b85a8a63d28e59
d9447e9ce97e92e5698b9fc9d664f8cd5ebda752f14405c366316b16d2525671fbbb657f5e4a487ba76d26fbc88eb91ed6d09168fdd5590ab782f2f259d65cd5
30d02a2cb7e6526643e799bfc45212c4357a3eeb192655ffbe1a163cd017a344860ec30a810ef8c2ab8277114a336cf80dce7bfde054809ee7e7951db1ae22de
18fe34f396bfed04c437f5d0fd26ae4ecf2b5695be234d50882fa1b650bf2038dba126cff25247785bb59c14d718dc4ac93a8ea1190ecf33d3c18ea8ac492ca6
e12d7ead5f52919d8756519fb9d44cf472db9f763d6cec70804dd2c120b3ae4c85491f28a8322df2369a15398f5ed455fa7f53f33804f7aad26bfd24eac3e3da
e1951b8e3a09cf3cb16dfb36d3e8dc7b622a6b9ea2520539483fae6439df5f5ce7b1cb9a26b4542db05f99e3ed35aa7501e6f82790b99f7c5c1fb4bb40d4d6ac
0a9c3a7e332dd72a9863da0e8f80cf3bc633f5ba3223f71e367b946912cef8251b7b8f8b79caf45dcdf704fb2c31cd41d02221c17417ed000116c09b0fc70a77
0c6eed96f64546bf5bf9677db60fe0f90670683065b759a698e447b710dd515ee805287f40aa17930b04bda7bb53cc3367bcaaaccbfcead8ae343cdc97dbaca1
36b8e30cece438b940b15a0628f7362d692c989fbbce97c0dd4735c896bc9e0da7f2e119e28be1db24f1185e66133bf06538e9ac41b1ddf117a6e3168bb5ab33
0b7027005825bcc52995c30e27b64d3d31b08427a300f7d6670273ae89f779e2f6dddf4048d3787ae9d05ba7f9c717be5ee889dfc08a1524bf160d12f3d3604f
d03a03c0a48cc400a72dd5bec1dff336a19d9f155bf07eb5d16078d2a31771b2c35d633e34145684d8dc0f6a57e563bca07a7ef2153f1afaaa45f9bdd5e15f7a
19892fcad191f1a320d9d510aae59831279cc9e1cb1cded6412716e6e22b90ac15cb6a60b4c9cb16c825ae378dcabf920affdef98ebf36a42590c85835f76953
da587b64788e349f67a6ddf6c7b3e291f7bf1adfbd57df6a146b2cc9fb9f68f64fafbee8cb04618afce6ab30a0f7e63eb38cf70cb3e9dd5feec40ad082bdd99a
6312f67fdb8771e3c30f7ec868c506da82ea7424d6ceaeed5ee1f18afd87ed101714cfb733d9a65ec181d29160cd85bdf46957b9ac03ea3be2fbe966cff059c3

    ... [486 lines of instance data omitted] ...

c648ae66a32015f35fe9efd242ef78840bdaebc80f9caf9fc713395722808f2733fc74347c4b7ca13707b9c42705caa843653c8797f5242c1599f10515e72383
7a76b541253adf9c348f16c5cf69d663a506e4951e31f5f65d2eaccd355e6378653b13eef0c41a67ff8ac61ce06dd6dc99859ffa84798a582a1b687085088fb9
ec1ce6e85ef62cd03f00b0ddb9370976fdd8b77b8b4db561a9c1964a160ceca23d557b69b3a1a65532a95467a7e7d4fd8645ac96ef7f7fa3a14adf68286a7af6
c87daa40be721eec862505d226dd26272cb9419acee90ca583828885704f61a4baf181bb124782797f963e88ae7b85f466cad5787a159ca5ca29d2b38f0bdf12
37c8cca81fa47297e73894f80de93df7673a75d7da9677f58fff3b5257d0980c6d91ad249fa05384703d4d90f52f75fcff081b0a0d1108618a62ca07b53c1544
6517c187996067b814c798c23c6162f37534492b27f7c8d2e746af8c6b8e1adce7b08a

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly 18 integer indices separated by commas.
Example of the required format: <answer>[3, 17, 42]</answer>
The example illustrates syntax only and is not an answer to this instance.
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[25, 30, 32, 89, 95, 104, 114, 142, 223, 228, 238, 250, 281, 432, 558, 604, 654, 692]
```

---

## 2105.10184 — Balancing the Spread of Two Opinions in Sparse Social Networks

*graph structures* · [paper](https://arxiv.org/abs/2105.10184) · preset `medium` `{"n": 16, "part_size": 16, "degree": 11, "mix_steps": 6}` · search space ≈ `53387533…(289 digits)`

```text
FOUR-ROUND TWO-OPINION GOOD-SEED SEARCH

This is the exact selection core of a four-round 2-Opinion Target Set
Selection instance. There are K vertex-selection groups (colour classes)
and one edge-selection group for every unordered pair of classes.
A good added seed set T_b chooses exactly one selection vertex from every
group; T_a is empty. The incidence gadgets balance after round 4 exactly
when every chosen edge has the two chosen vertex labels as its endpoints.
Thus no knowledge of opinion diffusion or of the source paper is needed:
the complete, exact witness conditions are stated below.

K = 16
Q = 16
R = 11
B = 136

Vertex groups are ordered by class c = 0,1,...,K-1. Class c has local
labels x = 0,1,...,Q-1. Choosing label x in class c means choosing the
global selection-vertex ID c*Q+x.

Edge groups are ordered by (i,j) in the PAIR lines below; the lines use
lexicographic order 0<=i<j<K. ROW_MASKS contains Q hexadecimal integers.
For row u, bit v (least-significant bit is v=0) is 1 exactly when edge
(u,v) is available. Leading zeroes have no meaning. Every row has R bits.
Available edges are ordered by increasing u and then increasing v. If a
PAIR has OFFSET o, edge (u,v) has global selection-vertex ID
o + R*u + (number of set bits below v in row u).

A valid witness is an ordered JSON array of exactly B distinct global IDs:
first one ID from each of the K vertex groups, then one ID from each PAIR
group in the displayed order. For every PAIR (i,j), its chosen edge must
equal (the chosen local label in class i, the chosen local label in class
j). Order is required, IDs are 0-indexed integers, and repeats are forbidden.

PAIR_DATA_BEGIN
PAIR 0 1 OFFSET 256 ROW_MASKS f33d,dafa,97f9,9e5f,efd1,7b5b,cdbe,dd67,3eed,74bf,f9c7,73f5,ecf3,2fbe,f78e,af6e
PAIR 0 2 OFFSET 432 ROW_MASKS f3ab,ef95,f1d7,adde,5fdc,7f66,fc7c,3fab,77ae,d9f3,fe59,b6f3,ca7f,1fed,a73f,c8ff
PAIR 0 3 OFFSET 608 ROW_MASKS bf56,f8bd,7b67,53f7,b7ec,7d57,ab6f,4ebf,f0fb,fcb9,877f,ef99,37fa,dcdd,efa6,dfca
PAIR 0 4 OFFSET 784 ROW_MASKS 7e76,bfa6,cebd,6b9f,ab6f,fda3,74fb,a77e,5cbf,57fa,bf5a,efc9,b1f7,d3dd,d8fd,ff45
PAIR 0 5 OFFSET 960 ROW_MASKS eed6,b5fc,63df,7f9a,57db,cdd7,89ff,f32f,db79,f2f5,3daf,fe36,ef69,7db9,9e6f,bee6
PAIR 0 6 OFFSET 1136 ROW_MASKS 7f74,a77b,f5ae,8efd,7d4f,dfc9,75ed,beb6,f85f,7afc,e3eb,8fd7,bfb2,d3b7,6cfb,db1f
PAIR 0 7 OFFSET 1312 ROW_MASKS fc1f,8fcf,75dd,df56,67f9,9bfc,f2f3,fa6b,cdaf,1eef,f1f6,7b3b,b6de,6fad,bf71,edb6
PAIR 0 8 OFFSET 1488 ROW_MASKS 3afd,0f7f,fb3c,b6f6,fe5c,55fe,ff16,cf8f,75cf,bee3,dce7,d37b,bdb9,6bbb,e9cf,e7f1
PAIR 0 9 OFFSET 1664 ROW_MASKS f5d6,9fd9,ef65,5ecf,23ff,57eb,793f,aff4,e99f,9e3f,fe3a,bdea,fc97,f3f2,5eed,e37d
PAIR 0 10 OFFSET 1840 ROW_MASKS 1ff3,95ef,ea5f,7797,bfcc,daeb,bb76,aff4,cded,7cfa,7a7b,feb2,657f,c79f,f9ad,f71d

    ... [104 lines of instance data omitted] ...

PAIR 12 13 OFFSET 20320 ROW_MASKS af9e,9d7e,376f,5fd9,dcf5,e7b9,d9bb,e9ee,e577,ff51,7abe,babb,72ef,ced7,f74d,3fe6
PAIR 12 14 OFFSET 20496 ROW_MASKS 7bd5,ed6e,b6fc,eec7,fc3b,19ff,f85f,3fd3,e75e,d6be,1ff3,b7bc,f72b,4fed,f9a7,cbf9
PAIR 12 15 OFFSET 20672 ROW_MASKS b37b,bbf8,4f7b,63fd,f6e5,feaa,bdf4,fb1b,bc6f,5cdf,75d7,c6bf,df8e,7d7c,abb7,cfc7
PAIR 13 14 OFFSET 20848 ROW_MASKS db9b,5f1f,e6db,fc6e,6bf5,ceed,73f6,35fb,f9ba,afa7,8df7,775d,becd,9f3d,fe72,f1ee
PAIR 13 15 OFFSET 21024 ROW_MASKS dde3,ddf8,fad9,b76e,f49f,d2fd,9dd7,3777,6eaf,1f77,efb2,7ccf,efa9,e37e,6bfc,bb1f
PAIR 14 15 OFFSET 21200 ROW_MASKS dfca,cdcf,4bbf,f1dd,f5b3,3f5d,3afd,eeae,ee75,b7e6,deba,b5eb,7e3e,fd59,c3f7,3b77
PAIR_DATA_END

Give your final answer inside <answer></answer> tags, as one JSON array
containing exactly 136 integer global selection-vertex IDs.
Example of the required syntax (not a solution): <answer>[0,16]</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[3, 16, 40, 55, 71, 84, 99, 114, 141, 145, 160, 178, 198, 215, 224, 246, 289, 471, 647, 822, 995, 1171, 1346, 1530, 1698, 1873, 2050, 2229, 2405, 2577, 2757, 2901, 3076, 3253, 3428, 3602, 3778, 3960, 4129, 4304, 4481, 4660, 4837, 5008, 5187, 5454, 5629, 5803, 5977, 6153, 6338, 6505, 6680, 6858, 7037, 7213, 7384, 7565, 7729, 7903, 8079, 8255, 8437, 8606, 8781, 8958, 9137, 9313, 9485, 9665, 9839, 10015, 10191, 10375, 10542, 10717, 10894, 11073, 11249, 11421, 11601, 11743, 11916, 12101, 12269, 12444, 12621, 12799, 12976, 13148, 13327, 13491, 13673, 13841, 14017, 14195, 14373, 14549, 14721, 14902, 15072, 15239, 15414, 15591, 15770, 15947, 16118, 16298, 16592, 16767, 16944, 17124, 17298, 17471, 17650, 17691, 17869, 18047, 18223, 18395, 18575, 18737, 18918, 19091, 19264, 19445, 19643, 19818, 19990, 20168, 20391, 20562, 20741, 20925, 21106, 21202]
```

---

## 2110.05917 — On complexity of substructure connectivity and restricted connectivity of graphs

*graph structures* · [paper](https://arxiv.org/abs/2110.05917) · preset `hard` `{"n": 384, "degree": 3}` · search space ≈ `39402006…(116 digits)`

```text
Non-Monotone 2-3Sat witness problem

There are 384 Boolean variables, numbered 1 through 384 (1-indexed).
A positive literal +i is true exactly when variable i is true; a negative
literal -i is true exactly when variable i is false. A clause is an OR:
it is satisfied when at least one listed literal is true. Satisfy every
clause simultaneously. Each line below is one clause; literal order and
clause order have no meaning. Variables within a clause are distinct.
Every clause has two or three literals, and every three-literal clause
contains at least one positive and at least one negative literal.

Clauses (1536):
C1: +234 -23
C2: +80 +12
C3: +20 -334 +262
C4: +16 -142
C5: +143 +266
C6: +118 +256 -2
C7: +372 +27
C8: -103 -101
C9: +62 -367
C10: +188 +270
C11: +310 -330
C12: -196 +285
C13: -154 +329
C14: +125 +279
C15: +228 -35
C16: -45 +379
C17: +267 +97
C18: -203 +341
C19: +346 -158
C20: -252 -58
C21: +36 -163
C22: +199 +178
C23: +183 -352
C24: -102 -281
C25: -37 -339 +72
C26: -137 -328
C27: +131 -127
C28: +203 -232 -370
C29: -290 +347
C30: -180 +123 -360
C31: -41 -279 +137
C32: +57 -258
C33: +375 +293

    ... [1500 lines of instance data omitted] ...

C1534: -378 +288
C1535: -382 +353 +319
C1536: -75 +98 -301

Output exactly 384 comma-separated signed integers in variable order.
At position i write +i to set variable i true or -i to set it false.
Every variable must occur exactly once; repetitions are forbidden.
Order inside the answer therefore matters and is fixed as 1,2,...,n.

Give your final answer inside <answer></answer> tags, as signed integers.
Example: <answer>1, -2, 3</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[1, -2, -3, 4, -5, -6, -7, -8, 9, -10, 11, 12, 13, 14, -15, 16, -17, -18, -19, -20, -21, -22, 23, 24, -25, 26, -27, 28, 29, 30, 31, -32, -33, -34, 35, -36, 37, 38, -39, 40, 41, -42, 43, -44, -45, -46, -47, -48, 49, 50, -51, -52, -53, -54, -55, -56, 57, -58, 59, -60, 61, -62, 63, -64, 65, -66, 67, 68, -69, -70, 71, -72, 73, 74, 75, 76, 77, -78, 79, -80, 81, -82, -83, 84, -85, 86, -87, 88, -89, 90, -91, 92, -93, -94, -95, -96, 97, 98, -99, -100, -101, -102, -103, 104, -105, 106, 107, 108, 109, -110, 111, 112, -113, 114, 115, -116, -117, -118, -119, -120, 121, 122, 123, 124, 125, -126, 127, -128, 129, 130, 131, -132, -133, 134, -135, 136, -137, -138, -139, -140, -141, 142, 143, 144, 145, 146, -147, -148, 149, -150, -151, 152, 153, 154, -155, -156, -157, -158, -159, 160, 161, 162, -163, 164, 165, -166, 167, 168, -169, -170, -171, 172, 173, -174, 175, -176, -177, 178, -179, 180, -181, -182, 183, -184, 185, 186, -187, 188, -189, -190, -191, 192, 193, -194, 195, -196, 197, 198, 199, 200, -201, 202, 203, -204, 205, 206, 207, 208, -209, 210, 211, -212, -213, -214, -215, -216, -217, -218, 219, 220, 221, 222, -223, 224, 225, 226, -227, 228, 229, -230, 231, 232, -233, 234, 235, 236, 237, -238, -239, -240, 241, -242, 243, 244, 245, 246, 247, 248, -249, 250, -251, -252, -253, -254, 255, -256, 257, 258, 259, 260, -261, -262, -263, -264, 265, 266, 267, -268, -269, 270, -271, 272, -273, 274, 27  … (2008 chars total)
```

---

## 2112.06333 — Single-conflict colorings of degenerate graphs

*graph structures* · [paper](https://arxiv.org/abs/2112.06333) · preset `medium` `{"n": 72, "matchings": 4, "triangle_free": true}` · search space ≈ `11433811…(104 digits)`

```text
Single-conflict coloring witness problem

There are 216 vertices, numbered 0 through 215, and 3 colors,
numbered 0 through 2. A coloring assigns exactly one color to
every vertex. Colors may be reused, and the coloring need not use every color.

A conflict edge has two endpoints and one forbidden ordered color pair.
For each unordered constraint pair `u v` listed below (always u < v),
there are exactly 3 parallel conflict edges. For color c in
{0, ..., 2}, the c-th parallel edge forbids (c,c) from u to v;
the reverse orientation forbids the reversed pair, which is also (c,c).
Thus a coloring is valid exactly when every listed pair has differently
colored endpoints. The order of the listed pairs has no meaning.

CONSTRAINT_PAIRS 864
124 185
63 108
10 34
56 170
72 163
8 154
91 120
55 138
176 196
83 199
125 212
139 170
53 58
27 139
161 165
43 116
62 128
70 137
65 203
23 157
170 181
14 70
33 96
136 201
65 183
119 168
64 192
139 178
189 190
49 150

    ... [832 lines of instance data omitted] ...

39 132
71 102
END_CONSTRAINT_PAIRS

Output exactly 216 base-10 integers. Integer number v is the color of
vertex v, so order matters and vertices are 0-indexed. Separate integers
with commas. Do not include vertex numbers, brackets, or repeated entries.

Give your final answer inside <answer></answer> tags, as a comma-separated
list of colors in vertex order.
Example of the format only: <answer>0, 2, 1, 0</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[0, 2, 0, 1, 1, 0, 1, 1, 0, 2, 2, 2, 1, 2, 0, 0, 1, 0, 2, 2, 0, 1, 2, 2, 2, 0, 1, 0, 1, 2, 2, 0, 0, 1, 0, 2, 2, 1, 0, 0, 1, 1, 1, 0, 2, 0, 0, 0, 1, 1, 1, 1, 2, 1, 2, 1, 1, 0, 0, 2, 1, 0, 0, 2, 1, 2, 0, 1, 1, 1, 1, 2, 2, 2, 0, 2, 2, 1, 0, 2, 1, 1, 2, 2, 1, 0, 1, 2, 2, 1, 0, 1, 2, 0, 1, 1, 0, 2, 1, 1, 2, 2, 1, 2, 2, 0, 1, 2, 1, 2, 0, 1, 1, 1, 2, 1, 1, 2, 0, 2, 0, 0, 2, 1, 0, 1, 0, 0, 1, 2, 0, 2, 1, 2, 2, 0, 0, 0, 0, 1, 1, 0, 1, 1, 2, 2, 0, 2, 2, 1, 0, 2, 0, 0, 2, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 2, 1, 1, 0, 1, 2, 2, 1, 2, 0, 2, 1, 2, 2, 0, 0, 0, 2, 1, 0, 1, 2, 2, 2, 2, 0, 1, 2, 2, 1, 0, 0, 0, 0, 0, 1, 2, 0, 1, 2, 2, 0, 2, 0, 0, 0, 0, 2, 0, 0, 2]
```

---

## 2205.04710 — Matrix Waring Problem -- II

*algebraic decomposition* · [paper](https://arxiv.org/abs/2205.04710) · preset `hard` `{"n": 24}` · search space ≈ `50809828…(947 digits)`

```text
Matrix Waring witness problem over a prime field

Let F_p be the field of integers modulo the prime p=21789309426606147004390309175379418434209095816567392007375406252547884139637957468112089238951358349366065278639669249.  All additions and
multiplications below are performed modulo p, with residues represented by the
integers 0 through p-1 inclusive.

The exponent is k=16777216.  For a square matrix X, X^k means the ordinary matrix
product of exactly k copies of X; it is not entrywise exponentiation.  Matrix
row and column indices are 0-based.  Find two 2 by 2 matrices A and B over
F_p such that

    A^k + B^k = T.

The order of A and B does not matter, repeats are allowed, and every entry must
be an integer in the inclusive range 0..p-1.  The target T is given row by row:

21032838841068915677659325287686069127747387149176285514391699764688179153467269381991766062152309398819121158304283418 15658411910059636389495710156331519550917411278378503737707697287757731863363682292234154699821300976588864679874150726
13691557940191567970212734460123580403477671069302642109345753596314491461460888490380094321695979865538462075012038797 19725813694942948962642682728612206182721020215457612862384972732411067820837477400486895635064804406784060480097318704

Your witness must contain exactly two matrices, each with exactly 2 rows and
2 entries per row.  Use JSON with the exact keys "A" and "B".

Give your final answer inside <answer></answer> tags, as
<answer>{"A":[[a00,a01],[a10,a11]],"B":[[b00,b01],[b10,b11]]}</answer>
with the obvious same row shape if the displayed dimension is not 2.
Example of the required syntax: <answer>{"A":[[0,0],[0,0]],"B":[[0,0],[0,0]]}</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
{"A": [[270664213911209592072218164654297012647542334775852128950150626865964369008470682617440334268176916697599729211999785, 4111071144983574645461974471703787484629180766699551754841076722197725208325210017372424008938038854131647710383649547], [21649803663680496024161565800280628407503914833747793880426755151474913147295689497558926652400524823995807685347782929, 14612695273202611152972311983994230356743945348689383249512511724777950275515752744874523503989526643385543304227887992]], "B": [[9411378708872646944032651960872471161731061085693654239484024628369845962343942996032892022811318920675233182486714815, 6589781076447272822525669729165248230979119782329016516852994747653883736904231081756883203544750186602782440400922757], [5770772588258990707199030943572912538019210281056196899756391711740666633316186439510483573706015229169139685092668990, 16099010896091225857539520457931135882945540571117552253733682199186579598824831327917321871352810744611899633063374814]]}
```

---

## 2302.11250 — Dynamic Debt Swapping in Financial Networks

*reconfiguration* · [paper](https://arxiv.org/abs/2302.11250) · preset `easy` `{"n": 24, "spread": 0.3, "attack_filter": true}` · search space ≈ `37496588…(208 digits)`

```text
Semi-positive debt-swap reachability

A financial network is a directed multigraph of banks and named debt contracts.
A contract e=(debtor -> creditor, liability L) pays an integer amount between 0
and L.  A bank's total assets are its nonnegative integer external assets plus
all incoming payments.  It pays those assets along its outgoing contracts in
increasing rank order, filling each liability before paying the next.  Unspent
assets are allowed only after all outgoing liabilities are full.  This instance
is acyclic, so its clearing state is obtained exactly by processing debtors
before creditors.  Banks and contracts not assigned external assets have 0.

A debt swap chooses two CURRENT contracts with the same liability.  If their
current endpoints are u1->v1 and u2->v2, then u1,u2,v1,v2 must be four pairwise
distinct banks.  The swap changes them to u1->v2 and u2->v1.  Contract names,
debtors, liabilities, and ranks never change.  A swap is semi-positive when,
comparing exact clearing states immediately before and after it, both old
creditors v1 and v2 have weakly larger total assets and exactly one has strictly
larger total assets.

All indices below are 0-based.  Let q=24, so there are 72 item banks and
2q-1 gate banks.  The complete bank set is:
  V, R;
  I0..I71, C0..C71;
  U0..U46;
  S0..S22, D0..D22.

External assets of item bank Ii are listed as index:value:
  0:1345, 1:1387, 2:1428, 3:1650, 4:1450, 5:1434, 6:1346, 7:1586, 8:1363, 9:1432, 10:1514, 11:1544, 12:1548, 13:1435, 14:1589, 15:1339, 16:1537, 17:1638, 18:1563, 19:1484, 20:1453, 21:1583, 22:1335, 23:1542, 24:1430, 25:1515, 26:1452, 27:1540, 28:1653, 29:1412, 30:1324, 31:1461, 32:1443, 33:1632, 34:1524, 35:1652, 36:1333, 37:1590, 38:1449, 39:1550, 40:1584, 41:1502, 42:1362, 43:1534, 44:1395, 45:1599, 46:1405, 47:1410, 48:1489, 49:1375, 50:1309, 51:1568, 52:1468, 53:1312, 54:1497, 55:1447, 56:1582, 57:1349, 58:1456, 59:1651, 60:1641, 61:1343, 62:1337, 63:1526, 64:1462, 65:1483, 66:1367, 67:1633, 68:1454, 69:1493, 70:1645, 71:1469
Every listed item value is strictly between T/4 and T/2; consequently exactly
three item payments, neither fewer nor more, can total T.
Each Sj has external assets 1.  Every other bank has external assets 0.

The complete initial contract set is defined by these inclusive index ranges:
  i<idx>: I<idx> -> R, liability c=8887, rank 0, for idx=0..71.
  c<idx>: C<idx> -> V, liability c=8887, rank 0, for idx=0..71.
  g<h>: V -> U<h>, rank h, for h=0..46; its liability is T=4443
      when h is even and 1 when h is odd.
  r<j>: U(2j) -> R, liability M=8889, rank 0, for j=0..23.
  p<j>: S<j> -> U(2j+1), liability d=8888, rank 0, for j=0..22.
  d<j>: D<j> -> V, liability d=8888, rank 0, for j=0..22.
Here, for example, i7 is the literal contract name "i7", and U(2j+1)
means the bank whose name is obtained by evaluating 2j+1 (for j=2, bank U5).

The target network keeps every debtor, liability, and rank unchanged.  Its
creditors are:
  i<i> -> V and c<i> -> R for every i=0..71;
  p<j> -> V for every j=0..22;
  the d-contract targets are: d0->U39, d1->U11, d2->U15, d3->U31, d4->U25, d5->U43, d6->U5, d7->U13, d8->U37, d9->U19, d10->U27, d11->U1, d12->U9, d13->U45, d14->U41, d15->U17, d16->U35, d17->U3, d18->U21, d19->U7, d20->U23, d21->U33, d22->U29;
  every g<h> and r<j> keeps its initial creditor.

Find a sequence of exactly 95 semi-positive debt swaps
that transforms the initial network into that target.  A contract may occur in
at most one submitted swap.  Sequence order matters.  Each swap is represented
as a JSON array of its two contract-name strings.  Inside each swap, put the
lexicographically smaller contract name first; repeats are forbidden.

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly 95 two-string arrays.
Format example only: <answer>[["c0","i0"],["d0","p0"]]</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[["c41", "i3"], ["c23", "i61"], ["c69", "i4"], ["d11", "p0"], ["c51", "i19"], ["c61", "i49"], ["c10", "i40"], ["d17", "p1"], ["c37", "i39"], ["c65", "i31"], ["c0", "i9"], ["d6", "p2"], ["c39", "i24"], ["c19", "i34"], ["c67", "i48"], ["d19", "p3"], ["c68", "i22"], ["c42", "i35"], ["c6", "i58"], ["d12", "p4"], ["c30", "i37"], ["c22", "i10"], ["c58", "i15"], ["d1", "p5"], ["c5", "i70"], ["c38", "i8"], ["c50", "i13"], ["d7", "p6"], ["c1", "i56"], ["c48", "i16"], ["c33", "i30"], ["d2", "p7"], ["c32", "i6"], ["c57", "i43"], ["c7", "i18"], ["d15", "p8"], ["c11", "i60"], ["c12", "i71"], ["c18", "i36"], ["d9", "p9"], ["c28", "i33"], ["c27", "i50"], ["c56", "i41"], ["d18", "p10"], ["c15", "i27"], ["c8", "i38"], ["c16", "i68"], ["d20", "p11"], ["c66", "i59"], ["c62", "i46"], ["c46", "i1"], ["d4", "p12"], ["c64", "i17"], ["c54", "i52"], ["c70", "i62"], ["d10", "p13"], ["c36", "i63"], ["c13", "i51"], ["c4", "i57"], ["d22", "p14"], ["c60", "i28"], ["c25", "i2"], ["c53", "i42"], ["d3", "p15"], ["c2", "i47"], ["c55", "i5"], ["c3", "i45"], ["d21", "p16"], ["c52", "i53"], ["c49", "i23"], ["c63", "i14"], ["d16", "p17"], ["c43", "i21"], ["c14", "i25"], ["c35", "i0"], ["d8", "p18"], ["c44", "i20"], ["c40", "i54"], ["c59", "i69"], ["d0", "p19"], ["c17", "i7"], ["c24", "i64"], ["c29", "i44"], ["d14", "p20"], ["c71", "i67"], ["c31", "i32"], ["c21", "i66"], ["d5", "p21"], ["c9", "i11"], ["c34", "i55"],  … (1480 chars total)
```

---

## 2306.12713 — A constructive solution to the Oberwolfach Problem with a large cycle

*designs and codes* · [paper](https://arxiv.org/abs/2306.12713) · preset `easy` `{"n": 64, "min_cycles": 3, "min_distinct_cycles": 3, "path_min_ratio": 0.1, "path_max_ratio": 0.65, "build_attempts": 1400}` · search space ≈ `23324803…(87 digits)`

```text
Graceful labeling problem (one path plus disjoint cycles)

The graph has one path with 12 edges (therefore 13 vertices) and
3 vertex-disjoint cycles.  In the input order, the cycle lengths are:
[13, 34, 5]

These components are mutually vertex-disjoint.  A cycle of length ell has ell
vertices and ell edges.  Thus the whole graph has 65 vertices and 64 edges.

Assign every integer label from 0 through 64, inclusive, to exactly one vertex.
For an edge whose endpoint labels are x and y, its edge difference is |x-y|.
Your labeling is valid exactly when the 64 edge differences are all distinct;
equivalently, they must be precisely 1 through 64, inclusive.

Represent the path by listing its 13 labels in traversal order.  Represent
each cycle by listing its labels in cyclic order; the last entry is adjacent to
the first.  Reversing the path, rotating or reversing a cycle, and reordering
cycles are allowed.  The multiset of submitted cycle lengths must equal the
input multiset.  Labels are 0-indexed integers, repetitions are forbidden, and
no edges exist between different listed components.

Give your final answer inside <answer></answer> tags, as one JSON object with
exactly the keys "path" and "cycles", each mapped to arrays of integers.
Format-only example: <answer>{"path":[0,1],"cycles":[[2,3,4]]}</answer>
The example numbers are not an answer to this instance.  Output nothing else
inside the tags.
```

**Answer** (verified ✓):

```json
{"path": [31, 20, 49, 9, 62, 2, 60, 3, 57, 12, 46, 23, 37], "cycles": [[19, 36, 28, 29, 44], [6, 56, 13, 43, 24, 34, 30, 25, 41, 21, 48, 11, 58], [0, 61, 5, 54, 10, 51, 15, 39, 32, 35, 22, 53, 7, 55, 16, 42, 33, 27, 45, 17, 52, 14, 47, 26, 38, 40, 18, 50, 8, 59, 4, 63, 1, 64]]}
```

---

## 2307.10607 — Parameterized Complexity of Biclique Contraction and Balanced Biclique Contraction

*reconfiguration* · [paper](https://arxiv.org/abs/2307.10607) · preset `easy` `{"n": 18, "set_factor": 6}` · search space ≈ `139258480300974996780`

```text
Find an edge-contraction witness that turns the graph below into a star.
A star is a complete bipartite graph K_{1,t}: one centre adjacent to every
other vertex, with no edges among the other vertices.

The graph is specified compactly but completely.
There are 54 element vertices B0,...,B53; matching pendant vertices
P0,...,P53; 108 set vertices S0,...,S107; one vertex x; and
73 guard leaves C0,...,C72.
Its undirected edges are exactly these (there are no other edges):
  * x--Sj for every set ID j from 0 through 107;
  * x--Ch for every guard index h from 0 through 72;
  * Bi--Pi for every element index i from 0 through 53;
  * Sj--Bi exactly when element i occurs in the triple listed for Sj.
The contraction budget is k=72. Contracting an edge merges its endpoints;
the merged vertex is adjacent to the union of their former neighbours, and
self-loops and parallel copies are discarded.

Return a compact witness consisting of exactly
q=18 distinct set IDs. The checker expands it into these contractions:
  1. contract x--Sj for every returned set ID j;
  2. for every element i, contract Bi--Sj where j is the unique returned
     set whose listed triple contains i.
Thus the expanded witness has exactly q+54=72 edges. It is accepted only
if every element has exactly one such selected set and replaying the
contractions produces a star. The order of returned IDs does not matter.
Set IDs and element IDs are 0-indexed; repeated IDs are forbidden.

Candidate triples (format: set ID: three element IDs):
S0: 7 19 27
S1: 30 31 44
S2: 4 13 43
S3: 22 35 46
S4: 11 36 39
S5: 2 26 33
S6: 8 18 28
S7: 18 32 50
S8: 27 38 45
S9: 34 46 52
S10: 14 49 53
S11: 0 15 50
S12: 21 43 50
S13: 2 7 49
S14: 23 37 41
S15: 4 17 21
S16: 2 38 44

    ... [84 lines of instance data omitted] ...

S101: 1 11 12
S102: 5 19 48
S103: 33 42 48
S104: 9 17 44
S105: 19 29 48
S106: 7 14 50
S107: 23 25 39

Give your final answer inside <answer></answer> tags, as exactly q
comma-separated set IDs, with no S prefix.
Example: <answer>3, 17, 42, 8</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[1, 25, 30, 41, 50, 60, 61, 65, 67, 69, 75, 77, 78, 81, 82, 99, 101, 102]
```

---

## 2309.11256 — Tropical cryptography III: digital signatures

*algebraic decomposition* · [paper](https://arxiv.org/abs/2309.11256) · preset `medium` `{"n": 36, "coefficient_max": 127}` · search space ≈ `18461222…(148 digits)`

```text
FORMAL TROPICAL POLYNOMIAL FACTORIZATION

A coefficient list A=[a_0,...,a_n] denotes a formal one-variable
polynomial.  Tropical multiplication of A and B=[b_0,...,b_n] is the
coefficient list C=[c_0,...,c_{2n}] defined exactly by

    c_k = min(a_i + b_j over all integers i,j with 0<=i,j<=n and i+j=k).

The plus sign inside that formula is ordinary integer addition.  Equality is
equality of every formal coefficient, not merely equality of the functions
obtained by evaluating the polynomials.

Here n=36.  Find two lists A and B, each containing exactly 37 ordinary
    integers.  Both lists must have endpoint coefficients zero,
a_0=a_36=b_0=b_36=0.  Every non-endpoint entry must lie in the inclusive
range [1,127].  A and B may be equal; no entries may be omitted;
repeated coefficient values are allowed.  The order of the two factors does
not matter, but the position within each list is its degree and is 0-indexed.
Their tropical product must equal the public C below at every degree.

Public coefficients, one line as "degree: coefficient":
0: 0
1: 36
2: 15
3: 4
4: 1
5: 36
6: 16
7: 5
8: 18
9: 36
10: 14
11: 30
12: 19
13: 28
14: 15
15: 12
16: 32
17: 14
18: 5
19: 4
20: 12
21: 16
22: 6
23: 5

    ... [44 lines of instance data omitted] ...

68: 40
69: 29
70: 49
71: 11
72: 0

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the keys "factor_a" and "factor_b", whose values are the two integer
lists in increasing degree order.
Example of the required shape (the values shown are only a format example):
<answer>{"factor_a":[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],"factor_b":[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
{"factor_a": [0, 82, 15, 4, 95, 36, 32, 29, 18, 95, 14, 87, 95, 115, 70, 12, 76, 55, 5, 4, 12, 28, 30, 65, 78, 4, 72, 26, 92, 84, 90, 70, 54, 29, 58, 76, 0], "factor_b": [0, 36, 104, 112, 1, 98, 104, 21, 90, 55, 44, 36, 20, 28, 123, 98, 44, 14, 12, 49, 13, 46, 109, 45, 78, 34, 104, 6, 94, 59, 69, 16, 125, 119, 49, 11, 0]}
```

---

## 2310.02137 — Random Diophantine Equations in the Primes II

*integer equations* · [paper](https://arxiv.org/abs/2310.02137) · preset `easy` `{"n": 60, "weight_bits": 60}` · search space ≈ `118264581564861424`

```text
BALANCED PRIME-COORDINATE QUADRATIC EQUATION

There are 60 ordered variables x_1,...,x_60.  Each variable must be one of
the two primes p=1000000007 and q=1000000009.  Exactly 30 variables must equal q; all
other variables must equal p.  Thus repeats of prime values are required, but
an index can be chosen only once.  Indices are 1-based and run from 1 through
60, inclusive.

For the integer weights a_i below, define

  A(x) = sum from i=1 to 60 of a_i*x_i,
  S(x) = sum from i=1 to 60 of x_i,
  F(x) = A(x)*S(x).

This is a homogeneous polynomial of degree 2.  Equivalently, the coefficient
of x_i^2 is a_i and the coefficient of x_i*x_j for i<j is a_i+a_j.  All
arithmetic is exact integer arithmetic.  Find a permitted, non-diagonal prime
tuple for which F(x)=0.  (The exact-30 rule already makes it non-diagonal.)

Weights, in `index: a_i` format:
  1: 201744926749750386
  2: -236190635138249482
  3: -235855273732461357
  4: 92165995908707890
  5: 158886375344165736
  6: -264862717706211684
  7: 464954358761330050
  8: -136643970610399663
  9: 308071132815812057
  10: 293424096056057951
  11: -451455250846823577
  12: -80531158486950486
  13: 568968191006836916
  14: -356749021411770769
  15: -545465331073981305
  16: -228439170742185669
  17: -316640032348025627
  18: 484466865033741747
  19: -400633730573931151
  20: 40497781428290016
  21: -25072291353854531
  22: -483786223499224273
  23: 76642303669397404
  24: 56721430268439329
  25: -375546423200042832

    ... [31 lines of instance data omitted] ...

  57: 469532073537145874
  58: -354094795988640679
  59: -133637839855558311
  60: 46417370160944765

Output the 30 distinct indices whose variables equal q.  Their order in the
answer does not matter; every unlisted index is assigned p.

Give your final answer inside <answer></answer> tags, as 30 comma-separated
base-10 integers.  Example of format only:
<answer>1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[2, 3, 6, 7, 8, 9, 13, 14, 15, 16, 18, 19, 27, 28, 29, 33, 35, 36, 38, 40, 41, 43, 44, 47, 48, 49, 52, 54, 57, 58]
```

---

## 2311.00090 — Doubly-weighted zero-sum constants

*additive combinatorial structures* · [paper](https://arxiv.org/abs/2311.00090) · preset `easy` `{"n": 64}` · search space ≈ `1832624140942590534`

```text
Balanced doubly-weighted zero-sum witness

All arithmetic below is in the ring Z/18446744073709551616Z: reduce an integer modulo 18446744073709551616,
with residue representatives 0 through 18446744073709551615.  The input is an ordered
sequence of 64 residues, labelled by 1-based positions:

1: 5125821543982213238
2: 1885446857198079865
3: 1784102302261635709
4: 14888888820055909286
5: 10650267372227927280
6: 1283066103397798384
7: 18174129289355940941
8: 7012091250016467664
9: 3000438492122948673
10: 11954142942718655192
11: 11713281966713340531
12: 13450015493620327431
13: 8527195849335553775
14: 12628903898023244582
15: 14850473871353034915
16: 4938947538669714523
17: 11858523945066023525
18: 4886176751863151491
19: 7367638952773315056
20: 9399101105401083268
21: 13941720072365397720
22: 2022669518369799574
23: 7097704095687072272
24: 18375196213244601545
25: 13851250634050167604
26: 11823658297578414819
27: 5414121733845069545
28: 8369725103947974346
29: 14055721717480188255
30: 16835012238916414748
31: 11534752662811201046
32: 3669262207937771719
33: 14065841566123610476
34: 11048577505222294225
35: 359282477494518661
36: 4417115578808483583
37: 1452811136191383414
38: 14127151791164321382
39: 12170254566408733533

    ... [38 lines of instance data omitted] ...

32 positions given weight +1; "minus" contains exactly 32
positions given weight -1.  The two lists must be disjoint and together must
be exactly the positions 1 through 64.  List order does not matter.  Repeats
are forbidden.  These shape rules make the second congruence explicit; the
first congruence is equivalently
sum(x_i for i in plus) - sum(x_i for i in minus) = 0 (mod 18446744073709551616).

Give your final answer inside <answer></answer> tags, as one JSON object with
exactly the keys "plus" and "minus", each mapped to a JSON list of integers.
Syntax example for a four-position instance:
<answer>{"plus":[1,3],"minus":[2,4]}</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
{"plus": [1, 2, 3, 6, 7, 9, 11, 13, 14, 15, 16, 18, 27, 28, 29, 33, 35, 36, 38, 39, 44, 45, 48, 52, 53, 54, 57, 59, 61, 62, 63, 64], "minus": [4, 5, 8, 10, 12, 17, 19, 20, 21, 22, 23, 24, 25, 26, 30, 31, 32, 34, 37, 40, 41, 42, 43, 46, 47, 49, 50, 51, 55, 56, 58, 60]}
```

---

## 2311.15057 — On Layered Area-Proportional Rectangle Contact Representations

*geometric configurations* · [paper](https://arxiv.org/abs/2311.15057) · preset `standard` `{"n": 14, "layer_ratio": 1.0, "max_width": 3, "canvas_factor": 14, "plant_span_factor": 4, "plant_trials": 32}` · search space ≈ `37802672…(287 digits)`

```text
INTEGER LAYERED RECTANGLE CONTACT WITNESS

There are unit-height, axis-aligned rectangles on fixed horizontal layers.
Rectangle v(i,j) is on layer i at fixed left-to-right position j, has the
listed positive integer width, and must be assigned an integer left x-coordinate
x[i][j]. All indices are 0-based. Coordinates must satisfy 0 <= x[i][j] and
x[i][j] + width[i][j] <= B. On one layer, rectangles must occur in the
listed order and their interiors may not overlap: x[i][j]+width[i][j] <=
x[i][j+1]. Equality is allowed and is a horizontal contact. Gaps are allowed.

Rectangles on adjacent layers have a vertical contact exactly when their closed
x-intervals overlap in a segment of POSITIVE length. Endpoint-only intersection
has length zero and is not a contact. A horizontal contact exists exactly at
equality for consecutive rectangles on one layer. A contact is permitted only
when its pair appears in the corresponding edge list below; any other contact is
a forbidden false adjacency. Listed edges need not all be realized.

Find coordinates that form a valid representation with at least k realized
listed edges. Each contact counts once. The required answer is one JSON outer
array in layer order, containing exactly one inner array of exactly n integer
left coordinates per layer, in the fixed rectangle order. Repeats are not
allowed because widths are positive; the coordinate order is not permutable.

L = 14
n = 14
B = 196  (right boundary is inclusive for rectangle endpoints)
k = 217

WIDTHS
layer 0: 3 1 1 3 2 1 1 1 3 1 3 3 3 1
layer 1: 3 2 1 1 1 1 1 3 3 1 3 1 3 3
layer 2: 3 3 2 1 2 3 2 1 1 3 2 2 2 1
layer 3: 1 2 1 1 2 1 2 2 3 2 1 3 2 3
layer 4: 1 2 1 3 2 3 3 2 3 1 3 1 1 3
layer 5: 1 2 1 1 1 2 2 2 3 2 1 2 2 1
layer 6: 3 2 3 3 3 1 3 3 1 3 3 1 1 2
layer 7: 2 2 3 3 3 1 3 2 1 1 1 2 2 2
layer 8: 1 1 3 3 2 1 3 2 2 3 2 1 2 1
layer 9: 1 3 3 3 2 3 3 2 3 2 2 1 1 3
layer 10: 2 1 1 1 1 3 1 3 2 3 1 2 2 3
layer 11: 2 3 2 3 1 3 3 1 3 3 2 3 2 1
layer 12: 2 2 1 2 1 3 3 2 3 1 3 1 3 2
layer 13: 3 3 3 1 1 2 1 3 3 1 3 2 2 1

HORIZONTAL EDGES

    ... [22 lines of instance data omitted] ...

layers 6/7: 0-0 1-0 1-1 2-1 2-2 3-2 4-2 4-3 4-4 5-4 6-4 7-4 7-5 7-6 7-7 8-7 9-7 9-8 9-9 10-9 11-9 11-10 12-10 12-11 13-11 13-12 13-13
layers 7/8: 0-0 1-0 1-1 1-2 2-2 2-3 3-3 3-4 4-4 4-5 4-6 5-6 6-6 6-7 7-7 8-7 9-7 9-8 10-8 10-9 11-9 11-10 12-10 12-11 12-12 12-13 13-13
layers 8/9: 0-0 1-0 1-1 1-2 1-3 2-3 3-3 4-3 4-4 4-5 5-5 5-6 6-6 6-7 6-8 6-9 7-9 8-9 8-10 9-10 10-10 10-11 10-12 11-12 12-12 12-13 13-13
layers 9/10: 0-0 1-0 2-0 2-1 3-1 3-2 3-3 3-4 4-4 4-5 5-5 6-5 6-6 6-7 7-7 7-8 8-8 8-9 9-9 10-9 10-10 10-11 11-11 11-12 12-12 13-12 13-13
layers 10/11: 0-0 0-1 1-1 2-1 3-1 3-2 4-2 4-3 4-4 4-5 5-5 5-6 5-7 5-8 5-9 6-9 7-9 7-10 8-10 9-10 9-11 9-12 10-12 11-12 11-13 12-13 13-13
layers 11/12: 0-0 1-0 1-1 2-1 2-2 3-2 4-2 4-3 4-4 5-4 6-4 7-4 7-5 7-6 8-6 8-7 9-7 9-8 10-8 10-9 10-10 11-10 12-10 13-10 13-11 13-12 13-13
layers 12/13: 0-0 1-0 1-1 2-1 3-1 4-1 5-1 5-2 5-3 5-4 6-4 6-5 6-6 7-6 7-7 8-7 8-8 9-8 9-9 10-9 10-10 11-10 11-11 12-11 12-12 13-12 13-13

Give your final answer inside <answer></answer> tags, as the JSON array
specified above (with the actual L rows and n entries per row).
Example syntax only: <answer>[[0,2,5],[1,4,8]]</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[[70, 75, 76, 85, 89, 91, 96, 104, 110, 113, 114, 117, 121, 124], [71, 79, 82, 83, 84, 85, 86, 95, 98, 106, 107, 116, 119, 122], [69, 75, 84, 86, 87, 89, 94, 98, 104, 105, 108, 112, 115, 121], [71, 75, 84, 85, 90, 95, 96, 99, 101, 108, 110, 114, 118, 120], [71, 72, 79, 82, 86, 88, 99, 102, 108, 111, 113, 116, 120, 122], [72, 74, 77, 79, 80, 88, 98, 100, 102, 107, 109, 115, 122, 124], [69, 76, 78, 82, 87, 92, 96, 100, 104, 107, 110, 114, 117, 120], [74, 77, 81, 89, 95, 100, 101, 104, 108, 113, 116, 117, 121, 123], [71, 78, 79, 82, 94, 96, 98, 110, 112, 114, 118, 120, 121, 123], [69, 72, 75, 79, 86, 94, 97, 104, 107, 111, 117, 119, 120, 122], [69, 83, 84, 85, 86, 96, 101, 102, 105, 109, 116, 117, 119, 121], [69, 71, 75, 77, 80, 86, 90, 94, 96, 101, 109, 113, 116, 118], [72, 75, 77, 80, 82, 83, 93, 97, 103, 109, 115, 118, 119, 122], [71, 76, 84, 87, 94, 95, 99, 102, 106, 109, 115, 118, 120, 122]]
```

---

## 2401.06027 — Examining Kempe equivalence via commutative algebra

*reconfiguration* · [paper](https://arxiv.org/abs/2401.06027) · preset `standard` `{"n": 128}` · search space ≈ `38562048…(216 digits)`

```text
Compressed bounded Kempe-switching certificate

A proper k-coloring assigns one integer color to every graph vertex,
with different colors at the ends of every edge.  A Kempe switching
chooses two distinct colors, takes the connected components of the
subgraph induced by vertices currently having either color, chooses
exactly one such component, and exchanges the two colors on every
vertex of that component.

This instance uses colors 0 through 128 inclusive.
Colors 0 through 127 are ordinary; 128 is a buffer.
The graph being recolored is a star: one center is adjacent to every
leaf, and there are no leaf-leaf edges.  The center has the buffer
color in both the source and target colorings.

The leaves are specified compactly by the undirected cubic graph below.
For each listed edge u-v and each r with 0 <= r < 257, there are
two distinct star leaves L(u,v,r) and L(v,u,r).  Leaf L(u,v,r) has
source color u and target color v.  Thus all leaf names, source colors,
target colors, and star edges are fully determined by this rule.
There are 98688 leaves and 98689 star vertices.
The compact graph vertices/colors are 0-indexed.  Edges are undirected.
Cubic edges (192 total):
0-20 0-48 0-124 1-7 1-69 1-87 2-66 2-74 2-87 3-28 3-80 3-94 4-38 4-54 4-126 5-33 5-58 5-85 6-55 6-67 6-86 7-85 7-124 8-24 8-90 8-117 9-28 9-56 9-92 10-37 10-72 10-81 11-30 11-69 11-75 12-45 12-48 12-125 13-31 13-86 13-125 14-55 14-64 14-90 15-68 15-81 15-121 16-49 16-62 16-89 17-120 17-125 17-127 18-73 18-74 18-96 19-93 19-106 19-108 20-95 20-99 21-30 21-47 21-119 22-52 22-76 22-100 23-35 23-70 23-97 24-46 24-104 25-63 25-71 25-91 26-71 26-79 26-101 27-29 27-109 27-116 28-67 29-64 29-107 30-118 31-35 31-127 32-50 32-118 32-123 33-49 33-105 34-47 34-51 34-72 35-94 36-58 36-80 36-85 37-46 37-79 38-61 38-111 39-59 39-72 39-74 40-50 40-97 40-106 41-66 41-84 41-111 42-56 42-91 42-100 43-93 43-102 43-112 44-45 44-105 44-114 45-54 46-97 47-82 48-109 49-76 50-63 51-61 51-116 52-59 52-70 53-105 53-115 53-122 54-75 55-84 56-78 57-68 57-113 57-122 58-68 59-95 60-73 60-96 60-101 61-62 62-103 63-123 64-77 65-77 65-90 65-98 66-80 67-121 69-114 70-111 71-110 73-95 75-108 76-102 77-110 78-84 78-100 79-87 81-98 82-83 82-104 83-89 83-91 86-120 88-108 88-117 88-119 89-115 92-101 92-102 93-110 94-99 96-123 98-107 99-112 103-104 103-126 106-121 107-117 109-119 112-122 113-115 113-124 114-120 116-126 118-127

Your witness is a compressed Kempe sequence: give exactly one cyclic
ordering h0,...,h127 of all ordinary colors.  Every integer 0 through
127 must occur exactly once; do not repeat h0 at the end.  Rotation
and reversal are both allowed.  The ordering expands deterministically:

1. Define pred(h[(i+1) mod n]) = h[i].  Visit leaves in increasing
   lexicographic order (u,v,r).  If a leaf L(u,v,r) currently has color
   u != pred(v), switch the singleton component containing that leaf
   using colors u and pred(v).
2. Starting with the center still at the buffer color, switch the
   component containing the center successively with the named colors
   h[n-1], h[n-2], ..., h[0], and finally the buffer color.

The expanded sequence must use at most 65921 Kempe switchings
and must finish at the target coloring.  Equivalently, every consecutive
pair in your cyclic ordering, including the last paired with the first,
must be one of the listed cubic edges.

Give your final answer inside <answer></answer> tags, as exactly the
128 comma-separated ordinary colors in cyclic order.
Example: <answer>3, 17, 42, 8</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[9, 92, 102, 76, 49, 16, 62, 103, 104, 82, 47, 21, 30, 118, 32, 50, 63, 123, 96, 18, 74, 2, 66, 80, 36, 85, 7, 1, 87, 79, 26, 101, 60, 73, 95, 59, 39, 72, 34, 51, 61, 38, 111, 41, 84, 78, 56, 42, 100, 22, 52, 70, 23, 97, 40, 106, 121, 67, 6, 55, 14, 90, 65, 98, 107, 117, 8, 24, 46, 37, 10, 81, 15, 68, 58, 5, 33, 105, 44, 45, 12, 48, 109, 119, 88, 108, 19, 93, 43, 112, 99, 20, 0, 124, 113, 57, 122, 53, 115, 89, 83, 91, 25, 71, 110, 77, 64, 29, 27, 116, 126, 4, 54, 75, 11, 69, 114, 120, 86, 13, 125, 17, 127, 31, 35, 94, 3, 28]
```

---

## 2404.18447 — The PRODSAT phase of random quantum satisfiability

*constraint satisfaction* · [paper](https://arxiv.org/abs/2404.18447) · preset `small` `{"n": 12, "p": 11}` · search space ≈ `8916100448256`

```text
Find a zero-energy product-state witness for this finite-field 3-QSAT core.

All arithmetic is in the prime field F_11: add and multiply modulo 11. Indices are 0-based.

There are 12 variables q[0],...,q[11]. Each variable is one projective point of P^1(F_11), encoded by exactly one integer in the inclusive range 0 through 11:
  q in 0,...,10 represents the nonzero two-vector v(q)=(1,q);
  q=11 represents the point at infinity v(q)=(0,1).
Vectors differing by a nonzero scalar represent the same point, which is why this encoding is canonical.

Each constraint lists three DISTINCT variable indices (a,b,c), in that order, and eight coefficients C000,C001,C010,C011,C100,C101,C110,C111 in that exact binary order. It is satisfied when
  sum over i,j,k in {0,1} of Cijk * v(q[a])[i] * v(q[b])[j] * v(q[c])[k] = 0 (mod 11).
All 12 constraints must be satisfied simultaneously. The factor graph is connected; every variable occurs in exactly three constraints and every constraint contains exactly three variables. Repeated q values are allowed, and the order of the 12 answer entries matters. Any satisfying witness is accepted.

Constraint data, one constraint per line:
0: vars 11 1 8 ; coeff 10 8 4 10 4 7 3 4
1: vars 7 6 10 ; coeff 4 7 1 0 2 7 5 7
2: vars 7 8 1 ; coeff 3 5 9 2 5 5 5 6
3: vars 5 4 0 ; coeff 5 8 7 1 5 3 7 1
4: vars 0 3 6 ; coeff 7 3 2 1 0 4 0 9
5: vars 11 4 0 ; coeff 3 2 5 9 5 3 2 8
6: vars 3 7 9 ; coeff 7 4 7 0 1 6 8 5
7: vars 10 3 5 ; coeff 3 9 5 6 0 4 7 9
8: vars 5 11 2 ; coeff 4 8 0 1 6 2 0 5
9: vars 9 1 10 ; coeff 5 0 6 0 9 8 4 5
10: vars 9 8 2 ; coeff 1 6 8 7 8 4 3 10
11: vars 2 6 4 ; coeff 6 1 6 5 5 8 5 2

Give your final answer inside <answer></answer> tags, as one JSON array of exactly 12 integers, in variable-index order.
Example of the exact syntax (illustrates syntax only and normally is not a solution):
<answer>[0,0,0,0,0,0,0,0,0,0,0,0]</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[10, 1, 0, 11, 4, 3, 3, 2, 11, 1, 10, 11]
```

---

## 2405.20406 — Bijective solutions to the Pentagon Equation

*algebraic identity solutions* · [paper](https://arxiv.org/abs/2405.20406) · preset `standard` `{"n": 6, "m": 4, "p": 3}` · search space ≈ `6461081889226673298932241`

```text
Find an isomorphism between two finite set-theoretic solutions of the pentagon equation.

All arithmetic below is in the finite field F_3: add and multiply integers modulo 3. Vectors are columns. Indices are 0-based.

An alternating bilinear map B: F_3^6 x F_3^6 -> F_3^4 is encoded by 4 matrices B[k], with
    B(u,v)[k] = u^T B[k] v  (mod 3).
The displayed matrices are alternating: their diagonal is zero and B[k][j][i] = -B[k][i][j] modulo 3.

Such a B defines a finite group on pairs (u,z) in F_3^6 x F_3^4; its multiplication is
    (u,z) * (v,w) = (u+v, z+w+inv2*B(u,v)),
where inv2=2 is the inverse of 2 modulo 3. This group defines the bijective pentagon map s_B(x,y)=(x*y,y). You do not need to list this exponentially large map.

The two tensors SOURCE and TARGET below define two such pentagon maps. Find two matrices:
  - P, exactly 6 by 6, invertible over F_3;
  - Q, exactly 4 by 4, invertible over F_3.
They must satisfy, for every k=0,...,3,
    P^T TARGET[k] P = sum over ell=0,...,3 of Q[k][ell] SOURCE[ell]  (mod 3).
Equivalently, F(u,z)=(P u,Q z) is an isomorphism of the two groups and of their pentagon maps. Other valid isomorphisms may exist; any one is accepted.

Matrix entries must be JSON integers in the inclusive range 0 through 2. Row order and column order matter. Repetitions are allowed as entries, but P and Q must each be invertible.

SOURCE has 4 component matrices, numbered 0 through 3:
SOURCE[0]
0 2 0 2 2 0
1 0 2 2 0 0
0 1 0 1 1 1
1 1 2 0 2 2
1 0 2 1 0 2
0 0 2 1 1 0
SOURCE[1]
0 0 2 1 0 0
0 0 0 1 1 1
1 0 0 0 0 2
2 2 0 0 2 1
0 2 0 1 0 0
0 2 1 2 0 0
SOURCE[2]
0 2 1 1 2 1
1 0 0 1 0 0
2 0 0 2 2 2
2 2 1 0 1 2
1 0 1 2 0 2
2 0 1 1 1 0
SOURCE[3]
0 1 2 1 1 0

    ... [28 lines of instance data omitted] ...

TARGET[3]
0 0 1 0 1 2
0 0 0 2 1 0
2 0 0 2 1 2
0 1 1 0 1 1
2 2 2 2 0 0
1 0 1 2 0 0

Give your final answer inside <answer></answer> tags, as one JSON object with exactly the keys "P" and "Q", each containing a row-major array of rows.
Example of the exact syntax (the identity matrices illustrate syntax only and normally are not a solution):
<answer>{"P":[[1,0,0,0,0,0],[0,1,0,0,0,0],[0,0,1,0,0,0],[0,0,0,1,0,0],[0,0,0,0,1,0],[0,0,0,0,0,1]],"Q":[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]}</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
{"P": [[0, 2, 1, 1, 1, 0], [0, 1, 0, 0, 1, 0], [1, 1, 2, 1, 0, 2], [1, 2, 0, 1, 0, 2], [1, 2, 2, 1, 2, 0], [2, 0, 0, 2, 0, 1]], "Q": [[0, 0, 0, 1], [1, 1, 2, 1], [0, 1, 1, 0], [2, 1, 2, 2]]}
```

---

## 2407.11768 — Independent Set Reconfiguration Under Bounded-Hop Token

*reconfiguration* · [paper](https://arxiv.org/abs/2407.11768) · preset `easy` `{"n": 48, "rounds": 8, "k": 3}` · search space ≈ `281474976710656`

```text
Bounded-hop independent-set reconfiguration witness

First invert these two fully specified Boolean mixing branches.  Their shared
secret input is S[0],...,S[47].  Each branch starts from that input.  In each
round use the three integer offsets a,b,c listed below and simultaneously
compute, for every i=0,...,47 (all subscripts modulo 48):

    A[i] = S[i+a] AND S[i+b]
    X[i] = S[i] XOR S[i+c]
    S_new[i] = A[i] XOR X[i]

Read S[0]...S[47] after the final round of branch 0 and then after the final
round of branch 1, and concatenate them.  The required
96-bit output is:
000101110110010001111010101000111111001011110101110001110110111100000001001110110101101010000101

Branch/round offsets (a b c):
B0R0: 7 26 23
B0R1: 31 42 25
B0R2: 11 24 35
B0R3: 14 44 35
B0R4: 46 45 25
B0R5: 40 42 7
B0R6: 36 16 17
B0R7: 31 26 17
B1R0: 42 46 25
B1R1: 45 21 23
B1R2: 16 3 5
B1R3: 26 18 31
B1R4: 15 38 7
B1R5: 14 43 31
B1R6: 26 42 47
B1R7: 10 17 43

Here is the exact E3-SAT formula and graph implied by that circuit.  This also
defines the reconfiguration witness encoded by your preimage.  Formula variable
IDs are 1-based.  Inputs use IDs 1,...,48.  Two free padding variables are
z=49 and w=50.  Then, in increasing branch, round, and i order,
allocate three fresh IDs A[i], X[i], S_new[i], in that order.  Each branch begins
again with input IDs 1,...,48.  A signed integer q denotes
variable q when positive and NOT variable |q| when negative.  Append clauses in
the order shown by these macros, preserving literal order:

AND(a,b,y): (-a,-b,+y), (+a,-y,+z), (+a,-y,-z),
            (+b,-y,+z), (+b,-y,-z)

    ... [30 lines of instance data omitted] ...

v(i,6).  Finally move the remaining s vertex of each variable to t(j,0),
again in increasing variable order.  The checker reconstructs and replays every
move; it never compares your preimage with a planted one.

All ranges are inclusive, strings are in increasing index order, and repeats are
not allowed where the construction says "fresh".  Any 48-bit preimage producing
the target is accepted.

Give your final answer inside <answer></answer> tags, as one JSON object with the
single key "preimage", whose value is exactly 48 binary characters.
Example of the required shape: <answer>{"preimage":"000000000000000000000000000000000000000000000000"}</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
{"preimage": "001000001000000010110011100100101110101011000010"}
```

---

## 2408.17266 — Sufficient conditions for solvability of linear Diophantine equations, and Frobenius numbers

*integer equations* · [paper](https://arxiv.org/abs/2408.17266) · preset `hard` `{"n": 54, "layers": 7}` · search space ≈ `12403790…(67 digits)`

```text
Find a nonnegative integer solution of one linear Diophantine equation.

Definitions and exact encoding.
There are m=378 variables x_1,...,x_378, indexed from 1.
Let q=54, B=55, and U=162. Ground-element labels are the integers 0 through 161.
Each variable i has a listed support triple (u,v,w) of three distinct ground elements.
Its raw coefficient is A_i = B^U + B^u + B^v + B^w. Let d=2.
The equation coefficient is the exact integer a_i=A_i/d.
The exact right-hand side is
    b = (q*B^U + sum(B^j for j=0,...,U-1))/d.
For this instance, b=23456778761009514050779956789076259161372335489089752279276823316747362969127841132037624244969773279960508288083834692422623912341586193985400443830180289539069234117823738111739589677768484055122974643443334483252555945358942887495942563408654780124876729722153093596851384198224103.
You must find nonnegative integers satisfying sum(a_i*x_i for i=1,...,m)=b.

The base encoding guarantees that every solution has exactly q entries equal to 1 and all other entries 0.
Therefore output exactly q distinct variable indices; omitted indices mean x_i=0 and listed indices mean x_i=1.
Order does not matter. Repeats are forbidden. Equivalently, the q listed support triples must cover every ground element exactly once.

Support triples, one per line in the parseable format `index: u v w`:
1: 56 106 153
2: 6 11 32
3: 28 138 147
4: 8 14 51
5: 6 64 82
6: 11 65 155
7: 17 84 156
8: 44 113 145
9: 48 74 125
10: 13 81 84
11: 20 101 112
12: 42 86 103
13: 35 48 96
14: 2 18 83
15: 30 49 59
16: 98 106 109
17: 44 69 108
18: 50 143 154
19: 5 68 154
20: 97 122 147
21: 12 46 118
22: 23 40 122
23: 14 72 85
24: 8 83 144
25: 42 85 144
26: 59 114 125
27: 66 79 159

    ... [343 lines of instance data omitted] ...

371: 80 98 140
372: 15 58 68
373: 147 160 161
374: 22 60 151
375: 50 93 110
376: 100 116 142
377: 111 125 149
378: 72 94 131

Give your final answer inside <answer></answer> tags, as exactly q comma-separated 1-indexed variable indices.
Example format: <answer>3, 17, 42, 58</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[18, 25, 45, 49, 59, 60, 83, 104, 120, 121, 124, 127, 132, 134, 137, 142, 145, 147, 150, 151, 156, 159, 170, 178, 187, 190, 194, 204, 211, 215, 227, 230, 245, 246, 248, 271, 274, 275, 284, 288, 306, 311, 324, 337, 339, 340, 344, 346, 348, 353, 355, 364, 372, 378]
```

---

## 2411.04916 — Improved kissing numbers in seventeen through twenty-one dimensions

*geometric configurations* · [paper](https://arxiv.org/abs/2411.04916) · preset `medium` `{"n": 108, "degree": 5, "mix_factor": 40}` · search space ≈ `33813919…(52 digits)`

```text
Find a kissing subconfiguration in the following finite pool.

A kissing configuration is a set of unit vectors in Euclidean space such that
the inner product of every two distinct selected vectors is at most 1/2.

There are 108 vertex groups, numbered 0 through 107.  Group v contains the
three candidate centers with IDs 3*v, 3*v+1, and 3*v+2; their local colours are
0, 1, and 2 respectively.  IDs and vertices are 0-indexed.  You must select
exactly one candidate from every group, hence exactly 108 distinct candidates.
The output IDs must be in strictly increasing order.  Order otherwise has no
mathematical significance, and repetitions are forbidden.

Here is the exact coordinate definition.  Make a conflict graph on all 324
candidate IDs.  Two candidates conflict exactly when either:
  (a) they are different candidates in the same vertex group; or
  (b) they have the same local colour and their vertex pair is in BASE_EDGES.
Every candidate has conflict degree D=7.  Give the ambient space D common
coordinates C_0,...,C_(D-1), followed by one coordinate Q_e for every unordered
conflict-graph edge e.  For candidate i, let z_i be the 0/1 vector that is 1 in
all D common coordinates and in Q_e exactly when e is incident with i, and 0
elsewhere.  Define the actual center x_i = z_i/sqrt(2*D).

Thus ||x_i||=1 exactly.  For distinct candidates i,j, direct substitution gives
<x_i,x_j>=(D+1)/(2*D)>1/2 if they conflict, and exactly 1/2 otherwise.  Therefore
the requested IDs are precisely a pairwise nonconflicting selection.  You may
use either this inner-product definition or the equivalent conflict rules.

All unordered base-graph edges follow, one "u v" pair per line.  Edges are
inclusive data; a pair not listed is not a base edge.
BASE_EDGES
0 4
0 17
0 77
0 81
0 85
1 33
1 72
1 76
1 92
1 96
2 10
2 21
2 56
2 90
2 95

    ... [249 lines of instance data omitted] ...

99 101
99 105
99 106
101 104
101 107
102 107
END_BASE_EDGES

Give your final answer inside <answer></answer> tags, as exactly 108
comma-separated integer candidate IDs in strictly increasing order.
Example of the required syntax: <answer>0, 4, 8</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[1, 3, 6, 10, 14, 15, 19, 22, 26, 27, 32, 35, 36, 39, 43, 46, 49, 53, 56, 58, 61, 64, 67, 70, 74, 77, 79, 81, 84, 88, 91, 93, 96, 100, 103, 107, 109, 111, 115, 118, 121, 125, 128, 131, 134, 136, 138, 142, 145, 147, 152, 153, 156, 159, 162, 167, 169, 171, 175, 177, 181, 183, 188, 190, 192, 196, 200, 203, 206, 209, 210, 215, 217, 221, 222, 225, 230, 233, 235, 239, 241, 245, 246, 250, 254, 257, 259, 261, 264, 269, 272, 273, 277, 281, 282, 286, 290, 293, 294, 299, 300, 303, 306, 309, 314, 315, 318, 323]
```

---

## 2411.07981 — Codegree conditions for (fractional) Steiner triple systems

*designs and codes* · [paper](https://arxiv.org/abs/2411.07981) · preset `medium` `{"n": 21, "layers": 5}` · search space ≈ `25987751…(72 digits)`

```text
STEINER TRIPLE SYSTEM INSIDE AN ALLOWED 3-UNIFORM HYPERGRAPH

The vertices are the integers 0 through 20, inclusive.
An unordered pair means two distinct vertices; (a,b) and (b,a) are
the same pair.  A triple is an unordered set of three distinct vertices.

Choose exactly 70 distinct triples from the allowed list below so
that every unordered pair of distinct vertices occurs in exactly one
chosen triple.  Order within a triple and order among triples do not
matter.  Repeated vertices and repeated triples are forbidden.

ALLOWED_TRIPLES 317
2 17 20
3 8 16
6 7 14
0 3 14
5 7 16
1 3 14
8 9 10
12 13 14
4 12 18
3 15 17
10 13 15
4 6 14
3 14 17
1 5 18
9 12 17
17 18 20
8 11 14
5 14 19
5 14 18
11 12 19
4 9 13
3 19 20
9 11 13
9 10 13
2 17 18
4 13 20
4 11 19
5 15 17
0 9 17
8 12 20
0 6 19
0 1 15
3 5 6

    ... [279 lines of instance data omitted] ...

2 6 8
14 17 18
5 10 12
0 3 11
0 6 7
END_ALLOWED_TRIPLES

Give your final answer inside <answer></answer> tags, as one JSON array
containing exactly 70 three-integer arrays.  JSON whitespace and
the order conventions above are ignored.
Example: <answer>[[0,1,2],[0,3,4]]</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[[1, 5, 12], [10, 13, 15], [4, 11, 19], [2, 5, 9], [6, 9, 17], [10, 11, 18], [2, 16, 20], [4, 9, 13], [3, 6, 7], [7, 11, 13], [2, 14, 15], [10, 14, 16], [5, 13, 18], [3, 9, 14], [9, 15, 19], [7, 12, 19], [4, 6, 14], [7, 8, 16], [4, 12, 18], [17, 18, 20], [3, 13, 17], [8, 9, 18], [2, 3, 18], [1, 9, 16], [2, 6, 12], [2, 4, 8], [0, 16, 18], [8, 15, 20], [5, 15, 16], [2, 7, 17], [1, 15, 17], [1, 13, 14], [0, 1, 7], [0, 3, 20], [5, 14, 19], [5, 8, 17], [1, 8, 10], [4, 7, 15], [6, 13, 16], [0, 2, 13], [12, 14, 20], [1, 18, 19], [7, 9, 10], [10, 12, 17], [8, 12, 13], [0, 4, 5], [9, 11, 20], [3, 16, 19], [0, 17, 19], [13, 19, 20], [3, 12, 15], [6, 8, 19], [1, 2, 11], [4, 10, 20], [2, 10, 19], [5, 6, 11], [7, 14, 18], [11, 14, 17], [11, 12, 16], [0, 6, 10], [0, 8, 14], [0, 9, 12], [6, 15, 18], [3, 8, 11], [4, 16, 17], [3, 5, 10], [1, 3, 4], [5, 7, 20], [1, 6, 20], [0, 11, 15]]
```

---

## 2411.14821 — Ex-post Stability under Two-Sided Matching: Complexity and Characterization

*schedules and allocations* · [paper](https://arxiv.org/abs/2411.14821) · preset `medium` `{"n": 32, "degree": 6}` · search space ≈ `28615177…(37 digits)`

```text
SUPPORTED WEAKLY-STABLE MATCHING — COMPACT SELECTOR WITNESS

There are 96 ground elements, numbered 0 through 95,
and 192 set gadgets, numbered 0 through 191.  Each set
gadget contains exactly three distinct ground elements; every ground element
occurs in exactly 6 gadgets.  The gadget data are:

  0: 51 52 74
  1: 21 28 34
  2: 37 41 51
  3: 45 68 83
  4: 14 49 73
  5: 22 44 95
  6: 24 76 77
  7: 40 44 55
  8: 59 62 84
  9: 51 54 78
  10: 18 70 77
  11: 25 37 78
  12: 17 52 58
  13: 3 61 78
  14: 6 23 95
  15: 21 41 94
  16: 42 50 94
  17: 0 5 35
  18: 75 85 93
  19: 4 9 19
  20: 47 63 93
  21: 0 66 89
  22: 9 78 87
  23: 16 18 54
  24: 2 70 75
  25: 7 27 74
  26: 2 8 67
  27: 27 29 85
  28: 0 20 83
  29: 22 24 58
  30: 5 24 32
  31: 19 36 67
  32: 64 71 95
  33: 25 53 87
  34: 9 44 92
  35: 65 77 92
  36: 23 33 59
  37: 11 54 89

    ... [190 lines of instance data omitted] ...

Select exactly 32 distinct gadget indices whose triples cover every ground
element exactly once.  The checker expands them canonically: selected c ports
take their a-items; unselected c ports take their same-port x-items; every d
takes its y-item; z(e) takes the selected port's remaining x-item containing e;
and s1-o1, s2-o2 are paired.  The checker then recomputes bijectivity, support,
and weak stability.  Order of the 32 output indices does not matter; indices
are 0-based and repeats are forbidden.

Give your final answer inside <answer></answer> tags, as exactly 32
comma-separated base-10 gadget indices with no brackets.
Example (format only): <answer>0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[0, 8, 10, 16, 27, 28, 29, 32, 33, 46, 47, 49, 51, 54, 64, 68, 82, 83, 85, 88, 99, 107, 113, 128, 131, 135, 141, 148, 155, 181, 184, 191]
```

---

## 2411.19413 — $S_h$-sets and linear codes over $\mathbb{F}_q$

*additive combinatorial structures* · [paper](https://arxiv.org/abs/2411.19413) · preset `standard` `{"n": 160, "rows": 92, "weight": 16, "marker_vertices": 12, "marker_edges": 18}` · search space ≈ `4059949873964357469950`

```text
Exact-weight binary syndrome problem

All vectors below belong to the binary vector space F_2^r. Addition in
this space is coordinatewise XOR: 0+0=0, 0+1=1, and 1+1=0.
Here r=92. Each displayed bit string has exactly 92 coordinates;
the leftmost displayed bit is coordinate 1 and the rightmost is coordinate r.

Choose exactly h=16 DISTINCT vectors from the n=160 indexed vectors
so that their XOR is exactly the target. Each index may be used at most once.
Indices are 1-based and inclusive (1 through n). Order does not matter.

target: 00111011001110011000010100111001111100000010011111010011011010010111101101001001110010001011
vectors:
  1: 00111111000001111111100000011001000111010110001111110111100011100011111010011101111010011010
  2: 10001101000001011101100110000010110010011001100110100100011001000111011011000111000101001100
  3: 11011001110000100001111001100100110010001010000100011101000001000011000000100111111001100010
  4: 11110001000011000111000110000001111010110000111000111000101001100111010111011101010110110000
  5: 01101000011000111111100001100101100110001010110011001100000011010001101111001010110100110001
  6: 10011110000000101110111010101110001010011001011010110110010101111010111111010001111101101001
  7: 01001100110011001001101111001010010100111111100010100010100010101011111100111110001111111101
  8: 00110101001111001001100111110010101010010111010000000001011000011001111010100100110100000011
  9: 01001111111111010011000101001110100001001001100110111011110011100100110000001000011110101010
 10: 01100111010111110101010011011111111110101000010100101100001000101100101010001000011011100101
 11: 01111101010000111010010001011100010110100111111101010101110110111001101100000000001100101011
 12: 10110011111111001001000110110011111100110101110000000000001000110001110011000101010110111011
 13: 01001011011000101010011110000000000000001110100000001001000001001000101101101010010111011111
 14: 00100100010110100001010101010111000000101111010001101100011000111011110000110110011110110111
 15: 10001011011000010001011011100000001110011011011001101010100001101110111011111111110101001000
 16: 10101011011100110010100101010011010001001010010101001011100001000010110000011000101001100011
 17: 11111000000001101000000001100011100100101111011101000110001000101100111001010000001110100111
 18: 01110110001010101100111010001000101010101001010100010100101010100100010011010110111111111100
 19: 11010100010010010101100110000001011011011001110111001100101000000100000010101100110011011001
 20: 10001111101111000000000101110110010011000000100111110011010110100011110000001011000011010100
 21: 11000001111011001001010111000110001111010001111110111000100011101001011101011001110010101000
 22: 10110100110111101000101101011000101000000001000100111110010000111001000011111101111000111110
 23: 00010111001110100111011001011001101100111101111010010000010110000000011110100110100110010011
 24: 11011100001110010001111000101010001001010101111010001100101101011001011001110101100010011110
 25: 10011001000101000101001111010010111111100101010111010110110100000101011011101010100110100010
 26: 10011000101110001111101010100111110010100001011111011010100011101110100000101011100111000011
 27: 10101101000110111001110011011100000000111111001100001110101011000010011100101111101101101101
 28: 11101111001001110010010001011001111001100001100110011000000000000111001110010001111111110110
 29: 00010010100100100010111110001110111110001100010010000101101111000000011110100011000011110011
 30: 01100100101100000101101000101011101011000110000001100100001001011010100001000110101010011101
 31: 11110000001010011010111011010000000111000101000101010101110100111110100000011001010010011111
 32: 01001110110110110011001100101001111110101100000110100011010011000000010100100000101101100001

    ... [121 lines of instance data omitted] ...

154: 11011111101011110001011101010111110110110101110000011111010100111001111111101011000110101101
155: 11011100000100011101111011000110111101100111111101101001010001001101000011011111110010111000
156: 10101011011101101101010110001011100001001101010111100100100000011011001101110110011011000101
157: 00110101101100101011010001111001011110000101010010001100010101111110001111000011101000100110
158: 11000110011101011011000101000101001011001111011110010111010111101111111000000111011101010010
159: 00101001110110001000001110101110011100011101101001010011001000101000100100100001100001110110
160: 00101110000010000111001010111110110010101101110101000000001000001100101000011000100100111010

Give your final answer inside <answer></answer> tags, as exactly
16 comma-separated decimal indices. Repeats are forbidden; order is ignored.
Example of the required syntax (not a hint): <answer>1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[7, 8, 9, 23, 24, 27, 29, 36, 56, 58, 60, 63, 71, 109, 140, 152]
```

---

## 2412.14615 — Additive codes attaining the Griesmer bound

*designs and codes* · [paper](https://arxiv.org/abs/2412.14615) · preset `medium` `{"n": 96, "bits": 12, "min_degree": 3, "guard_restarts": 16, "guard_nodes": 25000}` · search space ≈ `14396165…(361 digits)`

```text
BINARY PROJECTIVE-LINE PARTITION WITNESS PROBLEM

Work with 12-bit vectors over GF(2). Addition in GF(2) is
coordinate-wise XOR. In the binary projective space, every nonzero
vector below represents one point (there is no nontrivial scalar
rescaling to identify). A projective line is exactly a set of three
distinct points {a,b,c} whose vectors satisfy a XOR b XOR c = 0;
equivalently c = a XOR b.

The instance contains 288 distinct nonzero points, labelled
1 through 288. Partition all of them into exactly 96
projective lines. Every label must occur exactly once. A block is an
unordered triple, the blocks are unordered, and repeats are forbidden.
All bounds are inclusive and labels are 1-indexed.

POINTS (label: fixed-width vector)
001: 101000111100
002: 001001000001
003: 101111001001
004: 111110001010
005: 101111011010
006: 000110100011
007: 101101111101
008: 010000000110
009: 010010110111
010: 010011001101
011: 101100000011
012: 000101110101
013: 111101000011
014: 110110010000
015: 101111110101
016: 110100100111
017: 011101101001
018: 000100100101
019: 001101101001
020: 000100000001
021: 100010111010
022: 110000111000
023: 110100011010
024: 100010001100
025: 011000001111
026: 000010000100
027: 010100010010
028: 111011111101
029: 110000100101

    ... [256 lines of instance data omitted] ...

286: 000111001001
287: 001010001110
288: 111111000100

Output exactly 96 triples. Separate labels within a triple by
commas and separate triples by semicolons. Do not use brackets. Order
inside a triple and the order of triples do not matter.

Give your final answer inside <answer></answer> tags, as
semicolon-separated comma-separated triples of decimal point labels.
Example: <answer>1, 2, 3; 4, 5, 6</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[[1, 15, 286], [2, 112, 224], [3, 216, 255], [4, 67, 84], [5, 82, 267], [6, 179, 253], [7, 106, 234], [8, 248, 259], [9, 94, 190], [10, 13, 71], [11, 191, 265], [12, 205, 227], [14, 65, 192], [16, 52, 223], [17, 166, 236], [18, 30, 97], [19, 22, 249], [20, 45, 143], [21, 147, 176], [23, 127, 181], [24, 171, 239], [25, 51, 109], [26, 85, 134], [27, 182, 271], [28, 132, 273], [29, 95, 172], [31, 48, 165], [32, 187, 260], [33, 35, 80], [34, 104, 254], [36, 209, 275], [37, 121, 169], [38, 66, 284], [39, 55, 96], [40, 193, 206], [41, 49, 128], [42, 58, 86], [43, 54, 125], [44, 164, 285], [46, 91, 194], [47, 148, 174], [50, 93, 183], [53, 157, 238], [56, 120, 158], [57, 116, 126], [59, 163, 279], [60, 101, 142], [61, 119, 170], [62, 168, 251], [63, 145, 185], [64, 197, 241], [68, 72, 264], [69, 141, 144], [70, 213, 282], [73, 218, 287], [74, 118, 212], [75, 214, 268], [76, 115, 167], [77, 202, 203], [78, 110, 220], [79, 102, 151], [81, 129, 136], [83, 178, 228], [87, 269, 270], [88, 184, 252], [89, 211, 242], [90, 152, 221], [92, 133, 188], [98, 130, 155], [99, 160, 199], [100, 200, 222], [103, 138, 175], [105, 173, 277], [107, 153, 266], [108, 219, 278], [111, 161, 258], [113, 198, 256], [114, 196, 281], [117, 124, 208], [122, 135, 261], [123, 217, 283], [131, 195, 250], [137, 262, 280], [139, 201, 246], [140, 210, 243], [146, 159, 207], [149, 156, 233], [150, 226, 230], [154, 244,   … (1524 chars total)
```

---

## 2504.12430 — Fractional hypergraph coloring

*graph structures* · [paper](https://arxiv.org/abs/2504.12430) · preset `standard` `{"n": 18, "degree": 5}` · search space ≈ `35046120…(318 digits)`

```text
Proper (6:2)-fractional coloring of a graph

A graph is a set of vertices together with undirected edges.  Here it
is also viewed as a 2-uniform hypergraph: every edge has exactly two
distinct endpoints.  There are no loops and no repeated edges.

Assign every vertex exactly two DISTINCT colors chosen from
{0,1,2,3,4,5}.  An edge is properly fractionally colored exactly when
no color is assigned to both endpoints.  Equivalently, the two
2-element color sets at the endpoints must be disjoint.  Every listed
edge must satisfy this rule.

Vertices are the integers 0 through 269, inclusive
(0-indexed).  Every vertex must appear exactly once in the answer.
The order of vertex records and the order of the two colors within a
record do not matter.  Different vertices may receive the same pair.
Only the edges listed below impose constraints; nonedges impose none.

Edges (675 total), one pair of endpoints per line:
94 208
215 245
66 92
69 110
142 237
38 136
21 173
43 143
123 203
114 215
128 194
70 159
126 128
234 252
119 191
98 220
104 195
2 86
23 263
252 256
78 178
64 253
32 69
106 158
19 78
22 195

    ... [643 lines of instance data omitted] ...

80 145
74 142
135 226
151 174
210 229
129 132

Give your final answer inside <answer></answer> tags as one JSON array.
It must contain exactly one [vertex,color1,color2] record per vertex.
Both colors in a record must be integers in 0..5 and must be distinct.
Example format: <answer>[[0,0,1],[1,2,3]]</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[[0, 1, 4], [1, 0, 3], [2, 0, 4], [3, 3, 4], [4, 2, 4], [5, 0, 4], [6, 1, 3], [7, 2, 5], [8, 0, 1], [9, 1, 2], [10, 2, 5], [11, 1, 5], [12, 0, 1], [13, 3, 5], [14, 3, 4], [15, 1, 5], [16, 3, 4], [17, 1, 2], [18, 2, 5], [19, 1, 3], [20, 3, 5], [21, 2, 5], [22, 1, 2], [23, 4, 5], [24, 2, 5], [25, 4, 5], [26, 0, 1], [27, 1, 3], [28, 1, 2], [29, 4, 5], [30, 0, 5], [31, 4, 5], [32, 2, 3], [33, 0, 5], [34, 1, 2], [35, 2, 5], [36, 2, 5], [37, 3, 5], [38, 0, 2], [39, 0, 3], [40, 2, 4], [41, 0, 5], [42, 2, 5], [43, 3, 4], [44, 0, 1], [45, 1, 4], [46, 0, 3], [47, 3, 5], [48, 2, 4], [49, 0, 4], [50, 2, 4], [51, 0, 5], [52, 2, 3], [53, 3, 5], [54, 3, 5], [55, 1, 3], [56, 0, 1], [57, 3, 4], [58, 4, 5], [59, 0, 5], [60, 1, 5], [61, 3, 5], [62, 4, 5], [63, 1, 5], [64, 1, 4], [65, 0, 3], [66, 3, 4], [67, 1, 2], [68, 0, 2], [69, 1, 5], [70, 2, 4], [71, 1, 3], [72, 0, 2], [73, 0, 4], [74, 0, 4], [75, 4, 5], [76, 1, 4], [77, 1, 3], [78, 2, 4], [79, 2, 4], [80, 1, 5], [81, 0, 1], [82, 0, 5], [83, 0, 5], [84, 0, 1], [85, 0, 2], [86, 2, 3], [87, 0, 3], [88, 4, 5], [89, 1, 4], [90, 2, 3], [91, 2, 3], [92, 0, 5], [93, 4, 5], [94, 3, 5], [95, 2, 3], [96, 1, 3], [97, 4, 5], [98, 0, 2], [99, 2, 4], [100, 0, 5], [101, 1, 2], [102, 0, 5], [103, 0, 3], [104, 2, 5], [105, 4, 5], [106, 1, 5], [107, 0, 2], [108, 1, 4], [109, 1, 4], [110, 0, 2], [111, 1, 3], [112, 1, 5], [113, 0, 1], [114, 3, 5], [115, 2, 5], [  … (3400 chars total)
```

---

## 2506.23363 — Parameterized Critical Node Cut Revisited

*graph structures* · [paper](https://arxiv.org/abs/2506.23363) · preset `medium` `{"n": 66, "constraint_degree": 8}` · search space ≈ `10393671…(334 digits)`

```text
CRITICAL NODE CUT — EXACT ZERO-PAIR WITNESS

You are given a simple undirected graph.  Vertices are the integers 1 through
1188, inclusive.  Each row in the edge list is one unordered
edge {u,v}; there are no loops or duplicate edges.

For a deletion set S, remove every vertex in S and every incident edge.  Two
distinct remaining vertices form a connected pair when an undirected path
joins them in the remaining graph.  If the remaining connected components
have sizes c_1,c_2,..., the number of unordered connected pairs is
sum_i c_i*(c_i-1)/2.

Find exactly 770 distinct vertices whose deletion leaves at most
0 connected pairs.  Because the bound is zero, equivalently every
listed edge must have at least one endpoint in your deletion set.  Order does
not matter.  Repeated vertices are forbidden, and no vertex outside the
inclusive range 1..1188 is allowed.

VERTEX_COUNT 1188
EDGE_COUNT 2178
DELETE_EXACTLY 770
CONNECTED_PAIR_BOUND 0
EDGES
810 1114
255 644
688 721
497 528
16 967
115 737
156 870
289 1067
1042 1184
152 301
256 1145
607 939
50 730
690 1111
10 84
674 1009
298 1039
555 653
827 1088
152 1012
457 885
153 1122

    ... [2151 lines of instance data omitted] ...

738 866
225 1042
713 1144
433 725
643 777
END_EDGES

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly 770 distinct vertex integers.
Syntax example only, for a hypothetical instance asking for three vertices:
<answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[535, 684, 979, 935, 913, 329, 471, 531, 752, 242, 663, 887, 880, 813, 617, 609, 205, 758, 806, 1071, 781, 372, 1003, 787, 189, 710, 542, 602, 677, 981, 715, 650, 1154, 437, 38, 3, 712, 1060, 645, 103, 548, 247, 669, 622, 490, 509, 318, 826, 546, 1169, 375, 704, 111, 744, 674, 1149, 1181, 69, 523, 615, 390, 777, 878, 127, 161, 1029, 330, 857, 1082, 1170, 374, 276, 993, 209, 1167, 1057, 527, 419, 551, 968, 135, 232, 146, 377, 1135, 1061, 396, 45, 688, 348, 841, 411, 224, 261, 625, 6, 779, 1020, 1125, 310, 137, 445, 334, 177, 20, 290, 314, 433, 147, 397, 215, 126, 174, 496, 604, 989, 620, 190, 592, 789, 937, 972, 1136, 711, 153, 214, 742, 719, 1092, 406, 1054, 176, 79, 378, 479, 272, 510, 204, 1162, 1104, 249, 652, 292, 33, 1090, 654, 1114, 258, 409, 812, 914, 113, 305, 768, 1037, 999, 746, 873, 308, 80, 544, 1188, 842, 729, 632, 1152, 881, 855, 991, 1, 1043, 243, 879, 327, 104, 805, 1023, 199, 775, 603, 301, 799, 81, 858, 963, 361, 696, 169, 114, 687, 368, 1163, 473, 426, 1039, 1109, 303, 457, 743, 581, 220, 1139, 627, 590, 591, 182, 143, 1111, 1175, 964, 949, 352, 345, 324, 82, 61, 765, 661, 223, 717, 467, 679, 424, 582, 629, 57, 32, 1021, 360, 485, 447, 241, 790, 12, 1127, 910, 321, 1045, 543, 851, 952, 443, 705, 379, 689, 735, 1166, 1115, 151, 695, 1019, 732, 449, 899, 637, 681, 824, 1121, 567, 256, 369, 519, 162, 978, 145, 93, 828, 319, 166, 1153, 470, 834, 461, 184, 534, 98  … (3916 chars total)
```

---

## 2506.24001 — Fantastic Flips and Where to Find Them: A General Framework for Parameterized Local Search on Partitioning Problems

*schedules and allocations* · [paper](https://arxiv.org/abs/2506.24001) · preset `medium` `{"n": 64, "subset_fraction": 0.3, "value_bits": 40}` · search space ≈ `8719878125622720`

```text
LOCAL-SEARCH MULTI KNAPSACK (one knapsack)

There is one knapsack and a set of indivisible items.  Every item has a
nonnegative integer weight and value.  An assignment is feasible when the sum
of weights of the items inside the knapsack is at most its capacity.  Its score
is the sum of values inside.  A flip changes one item's status from inside to
outside or from outside to inside.  The flip distance is the number of items
whose final status differs from the supplied initial assignment.

Find a feasible assignment with score STRICTLY larger than the initial score
and flip distance at most 20.

This instance has 64 ordinary items and one special item.  All
ordinary items start inside; special item 65 starts outside.
Every value equals its weight.  Your witness must name exactly 19 distinct
ordinary items to remove; special item 65 is then inserted
automatically.  Order does not matter and repeated IDs are forbidden.  Item
IDs are the integers shown below and are 1-indexed.

Knapsack capacity: 1439440474520183
Initial total weight: 1439440474520182
Initial score: 1439440474520182
Required flip distance: exactly 20 (19 removals plus the special insertion)

For clarity, with these data the replay is feasible and strictly improving if
and only if the removed ordinary weights sum exactly to
427153168981112.  This equality is a derived aid; the checker still
replays the flips, checks capacity, and recomputes the score.

ITEMS (one row per item: ID WEIGHT VALUE INITIAL_STATUS)
1 22048652781124 22048652781124 in
2 22426434781606 22426434781606 in
3 22473070716580 22473070716580 in
4 22006851073867 22006851073867 in
5 22739371980049 22739371980049 in
6 22330728420233 22330728420233 in
7 22732246112750 22732246112750 in
8 22192535008237 22192535008237 in
9 22202317728381 22202317728381 in
10 22823122472097 22823122472097 in
11 22089315540434 22089315540434 in
12 22491288866201 22491288866201 in
13 22629208018570 22629208018570 in
14 22166262741580 22166262741580 in
15 22505007225382 22505007225382 in

    ... [44 lines of instance data omitted] ...

60 22144061204064 22144061204064 in
61 22269945567056 22269945567056 in
62 23036743216652 23036743216652 in
63 22570762355371 22570762355371 in
64 22920550792486 22920550792486 in
65 427153168981113 427153168981113 out

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly 19 distinct ordinary item IDs.  Do not include special item
65; it is inserted automatically.
Example: <answer>1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[2, 3, 6, 7, 9, 14, 15, 16, 18, 28, 35, 38, 44, 48, 52, 57, 62, 63, 64]
```

---

## 2508.11570 — NP-Completeness Proofs of Puzzles using the T-Metacell Framework

*constraint satisfaction* · [paper](https://arxiv.org/abs/2508.11570) · preset `standard` `{"n": 11}` · search space ≈ `34642936…(544 digits)`

```text
Grand Tour witness problem

The graph is a 22-row by 22-column rectangular grid of 484 vertices.
Rows are 0 through 21, columns are 0 through 21, and the vertex
at (row r, column c) has ID r*22+c.  Thus IDs are 0 through 483.
Two vertices have an available undirected edge exactly when their grid cells share
a side: their coordinates differ by 1 in exactly one coordinate and agree in the
other.  Diagonal and wraparound edges do not exist.

Find one simple closed loop that visits every vertex exactly once and uses every
forced edge below.  A forced edge a-b is undirected.  The forced edges are:
0-22 1-2 3-25 4-26 5-6 7-29 8-30 9-10 11-33 12-34 13-14 15-37 16-38 17-18 19-20 21-43 23-24 27-28 31-32 35-36 39-40 41-42 44-66 45-46 47-48 49-71 50-72 51-52 53-54 55-56 57-58 59-81 60-82 61-83 62-84 63-85 64-86 65-87 67-68 69-70 73-74 75-76 77-78 79-80 88-110 89-111 90-112 91-92 93-94 95-96 97-119 98-120 99-100 101-123 102-124 103-125 104-126 105-106 107-108 109-131 113-114 115-116 117-118 121-122 127-128 129-130 132-154 133-155 134-156 135-157 136-158 137-159 138-160 139-140 141-163 142-164 143-165 144-166 145-146 147-148 149-171 150-172 151-152 153-175 161-162 167-168 169-170 173-174 176-198 177-178 179-180 181-182 183-205 184-206 185-186 187-209 188-210 189-211 190-212 191-213 192-214 193-194 195-217 196-218 197-219 199-200 201-202 203-204 207-208 215-216 220-242 221-243 222-244 223-224 225-247 226-248 227-228 229-251 230-252 231-232 233-255 234-256 235-257 236-258 237-238 239-240 241-263 245-246 249-250 253-254 259-260 261-262 264-286 265-287 266-288 267-268 269-291 270-292 271-272 273-274 275-297 276-298 277-299 278-300 279-280 281-303 282-304 283-305 284-306 285-307 289-290 293-294 295-296 301-302 308-330 309-331 310-332 311-333 312-334 313-335 314-336 315-337 316-338 317-318 319-341 320-342 321-322 323-324 325-326 327-349 328-350 329-351 339-340 343-344 345-346 347-348 352-374 353-375 354-376 355-356 357-358 359-381 360-382 361-383 362-384 363-364 365-387 366-388 367-368 369-391 370-392 371-393 372-394 373-395 377-378 379-380 385-386 389-390 396-418 397-398 399-421 400-422 401-423 402-424 403-404 405-406 407-429 408-430 409-431 410-432 411-433 412-434 413-414 415-416 417-439 419-420 425-426 427-428 435-436 437-438 440-462 441-463 442-464 443-444 445-446 447-469 448-470 449-471 450-472 451-452 453-475 454-476 455-456 457-458 459-481 460-482 461-483 465-466 467-468 473-474 477-478 479-480

Represent the loop by exactly 484 comma-separated vertex IDs v0,...,v483
in cyclic order.  Every ID must occur exactly once.  Consecutive IDs must share an
available edge, including v483 back to v0.  The starting vertex and direction
are arbitrary; do not repeat v0 at the end.

Give your final answer inside <answer></answer> tags, as comma-separated integers.
Example: <answer>0, 1, 5, 4</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[0, 1, 2, 3, 25, 24, 23, 45, 46, 47, 48, 26, 4, 5, 6, 7, 29, 28, 27, 49, 71, 70, 69, 91, 92, 93, 94, 95, 96, 97, 119, 118, 117, 139, 140, 141, 163, 185, 186, 164, 142, 120, 98, 76, 75, 74, 73, 72, 50, 51, 52, 53, 54, 32, 31, 30, 8, 9, 10, 11, 33, 55, 56, 57, 58, 36, 35, 34, 12, 13, 14, 15, 37, 59, 81, 103, 125, 147, 148, 149, 171, 170, 169, 168, 167, 189, 211, 233, 255, 277, 299, 321, 322, 323, 324, 302, 301, 300, 278, 256, 234, 212, 190, 191, 213, 235, 257, 279, 280, 281, 303, 325, 326, 304, 282, 260, 259, 258, 236, 214, 192, 193, 194, 172, 150, 151, 152, 130, 129, 128, 127, 126, 104, 82, 60, 38, 16, 17, 18, 19, 20, 21, 43, 65, 87, 86, 64, 42, 41, 40, 39, 61, 83, 105, 106, 84, 62, 63, 85, 107, 108, 109, 131, 153, 175, 174, 173, 195, 217, 216, 215, 237, 238, 239, 240, 218, 196, 197, 219, 241, 263, 285, 307, 329, 351, 373, 395, 394, 372, 350, 328, 306, 284, 262, 261, 283, 305, 327, 349, 371, 393, 415, 416, 417, 439, 461, 483, 482, 460, 438, 437, 436, 435, 434, 412, 413, 414, 392, 370, 348, 347, 369, 391, 390, 389, 411, 433, 455, 456, 457, 458, 459, 481, 480, 479, 478, 477, 476, 454, 432, 410, 388, 366, 367, 368, 346, 345, 344, 343, 342, 320, 298, 276, 254, 253, 275, 297, 319, 341, 363, 364, 365, 387, 409, 431, 430, 408, 386, 385, 384, 362, 340, 339, 361, 383, 405, 406, 407, 429, 451, 452, 453, 475, 474, 473, 472, 450, 428, 427, 449, 471, 470, 448, 426, 425, 424, 402, 380, 379, 4  … (2310 chars total)
```

---

## 2509.03064 — Word-Representable Co-Bipartite Graphs: Vertex Ordering, Representation Number, Speed, and Entropy

*words and permutations* · [paper](https://arxiv.org/abs/2509.03064) · preset `easy` `{"n": 24, "k": 3, "mode": "random"}` · search space ≈ `12923075…(86 digits)`

```text
Exact 3-uniform word representation

The undirected simple graph has vertices labelled 0 through 23 inclusive.
Its 46 edges are listed below, one unordered pair per line.
Pairs not listed are non-edges; the order of edges and of endpoints is irrelevant.

2 22
2 15
0 4
12 23
0 19
6 10
13 22
1 18
5 19
14 15
0 8
17 23
7 19
16 19
20 21
2 23
2 9
5 6
12 15
5 18
17 22
12 22
2 18
8 18
12 18
5 20
5 8
5 21
12 17
14 23
0 20
5 15
13 23
10 11
0 7
1 4
3 15
7 16
4 19

    ... [10 lines of instance data omitted] ...

order of symbols matters.

For two distinct labels x and y, form their induced subword by deleting every
symbol other than x and y.  The labels alternate exactly when every two
consecutive symbols of this length-6 subword are different (so it is
x,y,x,y,... or y,x,y,x,...).  Your word must make x and y alternate if and only
if {x,y} is a listed edge, for every unordered pair of distinct vertices.

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly 72 base-10 integer labels.  Do not use brackets.  Output nothing
else inside the tags.
Example syntax: <answer>0, 1, 0, 1</answer>
```

**Answer** (verified ✓):

```json
[15, 2, 17, 13, 12, 22, 6, 3, 14, 23, 13, 17, 5, 8, 9, 15, 18, 12, 3, 7, 11, 2, 19, 21, 14, 10, 20, 6, 11, 10, 5, 11, 6, 21, 10, 15, 0, 20, 3, 22, 4, 23, 14, 16, 7, 19, 16, 8, 0, 1, 18, 17, 7, 5, 4, 19, 8, 21, 20, 0, 12, 1, 9, 13, 16, 4, 2, 18, 23, 22, 1, 9]
```

---

## 2509.10361 — Parameterized Complexity of Vehicle Routing

*schedules and allocations* · [paper](https://arxiv.org/abs/2509.10361) · preset `medium` `{"n": 48, "b_factor": 12}` · search space ≈ `15410530…(123 digits)`

```text
LOAD-AND-GAS-CAPACITATED VEHICLE ROUTING ON A STAR

The input is an undirected weighted star.  Its centre is the sole depot,
vertex 0.  Every other listed vertex is a client and has exactly
one edge, joining it to the depot, with the listed integer EDGE_WEIGHT.  Every
client has demand 1.

A vehicle route is a closed walk that starts and ends at the depot.  A client
is served by the route to which it is assigned.  The load of a route is the
sum of demands assigned to it, and the route weight is the sum of traversed
edge weights, counting every traversal.  At most 48
routes may be used.  Each route has load at most 3 and
weight at most 73770.  The sum of all route weights must be at
most 3540960.

Find a routing that serves every one of the 144 clients.  For this
star and these tight bounds, a witness can and must be written as exactly
48 disjoint groups of three clients.  Each group must contain exactly
one client of displayed type X, one of type Y, and one of type Z.  A group
[a,b,c] denotes the closed route
0-a-0-b-0-c-0; the order
inside a group and the order of groups do not matter.  Every client ID must
occur exactly once.  IDs are arbitrary integers: use them exactly as listed;
there is no positional or 0/1-index convention to infer.

The VALUE column is a derived aid.  Edge weights are encoded as 64*VALUE+tag,
where the tags for X,Y,Z are 1,4,16.  Consequently a valid group has one of
each type and its three VALUEs sum exactly to 576.  The
checker nevertheless replays the star routes and recomputes all load and
weight bounds.

CLIENT DATA
Each entry is ID:VALUE:EDGE_WEIGHT.  Entries after the initial type letter may
be reordered without changing the instance.
X 2:355:22721 5:251:16065 17:147:9409 19:228:14593 26:157:10049 31:125:8001 33:180:11521 37:90:5761 39:342:21889 40:271:17345 42:85:5441 43:167:10689 52:197:12609 57:205:13121 61:298:19073 62:132:8449 64:78:4993 65:123:7873 66:138:8833 67:368:23553 68:136:8705 72:178:11393 73:194:12417 75:280:17921 79:264:16897 82:88:5633 87:237:15169 93:106:6785 97:126:8065 103:259:16577 107:114:7297 108:72:4609 111:192:12289 114:182:11649 116:318:20353 120:171:10945 121:236:15105 122:174:11137 123:220:14081 124:285:18241 127:176:11265 128:207:13249 129:80:5121 131:198:12673 133:99:6337 134:108:6913 137:391:25025 141:405:25921
Y 3:227:14532 4:73:4676 6:102:6532 10:166:10628 11:155:9924 15:354:22660 16:417:26692 18:149:9540 22:211:13508 25:130:8324 30:109:6980 32:95:6084 35:229:14660 38:133:8516 41:105:6724 47:110:7044 48:316:20228 50:339:21700 53:163:10436 59:75:4804 69:117:7492 74:104:6660 77:165:10564 80:267:17092 81:89:5700 83:310:19844 85:219:14020 86:232:14852 88:181:11588 89:301:19268 91:253:16196 94:248:15876 95:97:6212 96:366:23428 99:278:17796 100:116:7428 101:238:15236 102:243:15556 105:309:19780 106:410:26244 113:193:12356 117:291:18628 126:101:6468 132:83:5316 135:296:18948 136:258:16516 138:305:19524 142:333:21316
Z 1:107:6864 7:201:12880 8:93:5968 9:346:22160 12:161:10320 13:142:9104 14:98:6288 20:320:20496 21:292:18704 23:91:5840 24:151:9680 27:152:9744 28:215:13776 29:87:5584 34:269:17232 36:128:8208 44:169:10832 45:307:19664 46:254:16272 49:168:10768 51:124:7952 54:74:4752 55:120:7696 56:111:7120 58:140:8976 60:245:15696 63:96:6160 70:162:10384 71:81:5200 76:112:7184 78:189:12112 84:139:8912 90:118:7568 92:82:5264 98:214:13712 104:141:9040 109:242:15504 110:213:13648 112:76:4880 115:156:10000 118:250:16016 119:79:5072 125:183:11728 130:314:20112 139:416:26640 140:113:7248 143:94:6032 144:119:7632

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly 48 three-integer arrays.  Each inner array is one route group;
do not include the depot and do not repeat a client ID.
Format example only: <answer>[[2, 3, 1]]</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[[2, 25, 23], [5, 3, 14], [17, 99, 24], [19, 80, 71], [26, 41, 130], [31, 50, 76], [33, 74, 21], [37, 96, 55], [39, 4, 12], [40, 10, 84], [42, 59, 139], [43, 135, 140], [52, 77, 98], [57, 69, 46], [61, 47, 49], [62, 142, 56], [64, 105, 78], [65, 38, 20], [66, 83, 36], [67, 126, 1], [68, 48, 51], [72, 138, 8], [73, 88, 7], [75, 132, 110], [79, 113, 144], [82, 85, 34], [87, 81, 118], [93, 89, 44], [97, 15, 63], [103, 11, 70], [107, 100, 9], [108, 106, 143], [111, 102, 104], [114, 22, 125], [116, 6, 115], [120, 53, 109], [121, 136, 92], [122, 32, 45], [123, 101, 90], [124, 18, 13], [127, 94, 27], [128, 35, 58], [129, 16, 119], [131, 117, 29], [133, 86, 60], [134, 91, 28], [137, 30, 112], [141, 95, 54]]
```

---

## 2509.14357 — Freeze-Tag is NP-hard in 2D with $L_1$ distance

*schedules and allocations* · [paper](https://arxiv.org/abs/2509.14357) · preset `standard` `{"n": 125, "band": 2}` · search space ≈ `35444733…(419 digits)`

```text
Planar L1 Freeze-Tag: find a deadline-feasible normal-form schedule

There are 502 labeled robots at integer points in the plane.  Distance
between (x1,y1) and (x2,y2) is the Manhattan distance
|x1-x2|+|y1-y2|.  Robot O is active at time 0; every other robot is frozen.
An active robot moves at speed at most 1.  When it reaches a frozen robot, that
robot activates immediately, and the arriving robot and the newly active robot
may move independently.  Waiting is allowed.  All robots must be active by the
inclusive deadline L=7141286250.

For this instance, construct the following normal-form schedule.  Robot O moves
along the straight segment from O to Z, activating every A robot on that segment
in increasing distance from O.  On reaching A_i, one available robot goes by a shortest
L1 path directly to one B_j.  The two robots then available at B_j go by shortest
L1 paths, one directly to C_k.1 and one directly to C_k.2.  Choose exactly one
B_j and one paired C_k for each A_i, using every B index j=0,...,124 exactly
once and every C-pair index k=0,...,124 exactly once.  Routes may cross and
robots may wait; there are no collision, congestion, or capacity constraints.

Robot data are shuffled.  Each line is: label x y.  Labels and indices are
literal and 0-based; C_k.1 and C_k.2 are two distinct robots in pair k.
C100.2 5744880000 1393563050
B8 -101250 -1317618
B31 -360000 -1058846
B76 -866250 -552890
C80.2 4607280000 2531163066
C94.2 5403600000 1734842970
A95 2773 0
C44.2 2559600000 4578843326
A60 2830 0
C84.1 4806360000 2332082960
C0.1 28440000 7110002772
A1 2424 0
C43.2 2502720000 4635722646
C68.2 3924720000 3213723094
A29 2592 0
B47 -540000 -878781
C96.1 5488920000 1649523128
B115 -1305000 -113814
C57.2 3299040000 3839402770
B79 -900000 -519177
A15 2866 0
C53.1 3043080000 4095363048
A119 2854 0
C106.1 6057720000 1080723404

    ... [475 lines of instance data omitted] ...

C75.1 4294440000 2844002606
C83.1 4749480000 2388962814
B16 -191250 -1227729

Output a JSON array of exactly 125 two-integer rows.  Row i (rows are ordered
i=0,...,124) must be [j,k], meaning A_i activates B_j and B_j activates both
C_k.1 and C_k.2.  Both columns must be permutations of 0,...,124; order
inside [j,k] matters, and repeats are forbidden.

Give your final answer inside <answer></answer> tags, as that JSON array.
Example: <answer>[[2,0],[0,1],[1,2]]</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[[9, 44], [96, 72], [99, 74], [98, 121], [70, 119], [16, 53], [60, 9], [47, 102], [101, 24], [80, 111], [67, 3], [21, 51], [30, 73], [84, 88], [32, 40], [62, 84], [72, 91], [119, 21], [93, 113], [61, 103], [56, 26], [2, 57], [65, 60], [78, 29], [36, 124], [97, 18], [7, 71], [1, 45], [85, 120], [52, 75], [26, 61], [88, 122], [73, 123], [102, 93], [92, 28], [113, 23], [39, 78], [100, 106], [34, 12], [50, 90], [38, 94], [108, 27], [41, 81], [82, 86], [76, 16], [59, 10], [42, 35], [124, 79], [22, 42], [51, 50], [95, 109], [23, 108], [40, 95], [63, 107], [117, 4], [66, 52], [6, 31], [55, 66], [123, 105], [87, 5], [103, 36], [18, 56], [49, 15], [104, 7], [74, 30], [8, 39], [24, 46], [46, 99], [37, 2], [10, 62], [79, 41], [15, 97], [68, 104], [58, 69], [5, 89], [33, 47], [44, 116], [45, 25], [12, 77], [48, 83], [106, 38], [115, 115], [114, 13], [105, 85], [19, 22], [90, 64], [43, 33], [109, 0], [20, 58], [0, 114], [120, 55], [110, 37], [57, 98], [118, 43], [53, 82], [112, 34], [89, 68], [83, 100], [91, 117], [25, 92], [71, 112], [107, 1], [77, 70], [64, 32], [29, 67], [27, 59], [111, 118], [122, 48], [4, 49], [54, 8], [75, 76], [11, 54], [69, 87], [116, 101], [86, 20], [13, 80], [121, 19], [17, 14], [28, 110], [31, 6], [35, 96], [94, 11], [3, 63], [14, 65], [81, 17]]
```

---

## 2511.01003 — On the Classification of Dillon's APN Hexanomials

*finite field constructions* · [paper](https://arxiv.org/abs/2511.01003) · preset `medium` `{"n": 3}` · search space ≈ `26385458…(47 digits)`

```text
AFFINE EQUIVALENCE OF TWO BINARY POINT SETS

The ambient space is the 12-dimensional vector space over GF(2).  A point
is written as exactly 3 hexadecimal digits, with leading zeroes retained;
this is the ordinary 12-bit binary encoding.  The two blocks below are
UNORDERED sets, each containing exactly 64 distinct points.
Their line order has no meaning.

Find any affine permutation T(v) = M v XOR t that maps the entire SOURCE set
onto the entire TARGET set.  Here M is an invertible 12 by 12 binary
matrix and t is a 12-bit vector.  All arithmetic is over GF(2): matrix
products use XOR for addition and AND/parity for scalar products.

Matrix convention: provide 12 binary row strings, top row first.  The top
row computes the leftmost (most significant) output bit.  Inside every row and
vector string, the rightmost bit is coordinate 0.  Thus an identity matrix is
listed from 100000000000 down to 000000000001.
Order within the answer matters for matrix rows.  Repeated rows are allowed by
the syntax but make M singular and are invalid.

SOURCE
252
01c
efc
098
035
f58
c0b
6db
7f5
641
9f2
f63
024
382
c38
135
d49
345
70b
aea
537
3ea
6e1
aeb

    ... [104 lines of instance data omitted] ...

f7a
e60
0a4
END TARGET

Give your final answer inside <answer></answer> tags, as one JSON object with
exactly two fields: "matrix", a list of exactly 12 binary strings of length
12, and "offset", one binary string of length 12.  Do not use 0x
prefixes.  The following shows the exact format (it is the identity example,
not necessarily a solution):
<answer>{"matrix":["100000000000","010000000000","001000000000","000100000000","000010000000","000001000000","000000100000","000000010000","000000001000","000000000100","000000000010","000000000001"],"offset":"000000000000"}</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
{"matrix": [2619, 456, 102, 3037, 1126, 1003, 914, 571, 3016, 2771, 3033, 2233], "offset": 712}
```

---

## 2601.19161 — Price of Locality in Permutation Mastermind: Are TikTok influencers Chaotic Enough?

*words and permutations* · [paper](https://arxiv.org/abs/2601.19161) · preset `hard` `{"n": 120, "clause_ratio": 0.82}` · search space ≈ `59494005…(32 digits)`

```text
Restricted 3-local permutation Mastermind witness problem

A permutation of 1,...,360 is an ordered list in which every integer occurs
exactly once.  Positions and values are both 1-indexed.  Split them into 120
ordered blocks: block i consists of 3i-2, 3i-1, 3i.  A permitted secret must use
one of exactly two orientations independently in every block:

  A_i = (3i-1, 3i, 3i-2)
  B_i = (3i, 3i-2, 3i-1).

The full secret is the concatenation of those 120 block triples, in block order.
Thus order matters, values may not repeat, and no other block orientation is
allowed.

Here is the lossless compact representation of a black-peg transcript.  A
black-peg score is the number of positions where a query permutation equals the
secret.  For three positions p,q,r, move A(p,q,r) replaces the current entries
(g[p],g[q],g[r]) by (g[q],g[r],g[p]); move B(p,q,r) is its inverse.  Each move
changes exactly three positions, so consecutive queries are 3-local.

For every listed clause (i,j,k), start at the identity query and perform:

  A(3i-2,3j-2,3k-2), A(3i-1,3j-1,3k-1), A(3i,3j,3k),
  A(3i-2,3i-1,3i), A(3j-2,3j-1,3j), A(3k-2,3k-1,3k),
  B(3i-2,3j-2,3k-2), B(3i-1,3j-1,3k-1), B(3i,3j,3k).

The nine resulting black-peg scores must be
  0 0 0 0 0 0 1 2 3.
Then undo those nine moves in reverse order; the resulting scores must be
  2 1 0 0 0 0 0 0 0,
returning to the identity (whose score is 0) before the next clause.  This is a
complete procedural specification of every query permutation and score; there
are no omitted queries.  For the two permitted block orientations, matching the
gadget is equivalent to requiring exactly one of blocks i,j,k to have type A.

As a redundant check obtainable by adding all clause equations, if d_i is the
number of listed clauses containing block i and x_i is 1 for type A (0 for B),
then sum(d_i*x_i) must equal 98.  Here the degree list d_1,...,d_120 is:
  2 2 2 3 2 2 2 3 3 2 2 3 3 2 3 2 3 3 2 3 2 3 2 3 2 3 3 3 2 2 2 3 2 2 2 3 3 3 3 2 2 2 2 3 3 2 2 2 2 3 3 2 3 2 2 3 2 3 3 3 3 3 3 2 2 3 2 3 2 3 3 2 2 2 2 3 2 3 2 2 2 3 3 3 2 3 2 2 2 2 3 2 3 2 2 2 2 2 3 3 3 3 2 2 2 3 2 2 3 3 2 2 3 3 3 2 2 2 2 3

Instance: 98 clauses.  Each row is "row_number: i j k" and contains three
distinct 1-indexed block numbers.  Clause order and the order within a row have
no semantic effect.
1: 70 34 98
2: 80 82 81

    ... [90 lines of instance data omitted] ...

93: 43 31 116
94: 88 24 36
95: 69 2 108
96: 28 27 22
97: 32 91 85
98: 119 22 105

Find any permitted secret permutation matching every score in the transcript.
Give your final answer inside <answer></answer> tags, as all 360 integers of the
permutation in position order, separated by commas.
Format example for a two-block permutation: <answer>2, 3, 1, 6, 4, 5</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[2, 3, 1, 6, 4, 5, 9, 7, 8, 11, 12, 10, 14, 15, 13, 18, 16, 17, 21, 19, 20, 24, 22, 23, 27, 25, 26, 30, 28, 29, 33, 31, 32, 35, 36, 34, 39, 37, 38, 41, 42, 40, 44, 45, 43, 48, 46, 47, 51, 49, 50, 53, 54, 52, 57, 55, 56, 60, 58, 59, 62, 63, 61, 66, 64, 65, 69, 67, 68, 72, 70, 71, 75, 73, 74, 77, 78, 76, 81, 79, 80, 83, 84, 82, 86, 87, 85, 89, 90, 88, 93, 91, 92, 95, 96, 94, 99, 97, 98, 102, 100, 101, 105, 103, 104, 107, 108, 106, 111, 109, 110, 114, 112, 113, 117, 115, 116, 120, 118, 119, 123, 121, 122, 126, 124, 125, 129, 127, 128, 131, 132, 130, 135, 133, 134, 138, 136, 137, 141, 139, 140, 144, 142, 143, 147, 145, 146, 150, 148, 149, 153, 151, 152, 156, 154, 155, 159, 157, 158, 161, 162, 160, 164, 165, 163, 168, 166, 167, 171, 169, 170, 173, 174, 172, 177, 175, 176, 180, 178, 179, 183, 181, 182, 186, 184, 185, 189, 187, 188, 192, 190, 191, 194, 195, 193, 198, 196, 197, 201, 199, 200, 204, 202, 203, 207, 205, 206, 209, 210, 208, 213, 211, 212, 215, 216, 214, 219, 217, 218, 222, 220, 221, 225, 223, 224, 227, 228, 226, 231, 229, 230, 233, 234, 232, 237, 235, 236, 240, 238, 239, 243, 241, 242, 245, 246, 244, 249, 247, 248, 251, 252, 250, 255, 253, 254, 257, 258, 256, 260, 261, 259, 264, 262, 263, 267, 265, 266, 269, 270, 268, 273, 271, 272, 275, 276, 274, 279, 277, 278, 282, 280, 281, 284, 285, 283, 288, 286, 287, 291, 289, 290, 294, 292, 293, 297, 295, 296, 300, 298, 299, 303, 30  … (1692 chars total)
```

---

## 2603.07251 — $\{\pm 1\}$-weighted zero-sum constants

*additive combinatorial structures* · [paper](https://arxiv.org/abs/2603.07251) · preset `easy` `{"n": 64}` · search space ≈ `1832624140942590534`

```text
Balanced {+1,-1}-weighted zero-sum witness

All arithmetic below is in the ring Z/18446744073709551616Z: reduce every integer modulo 18446744073709551616,
using residue representatives 0 through 18446744073709551615.  The input is this ordered
sequence of 64 residues, labelled by 1-based positions:

1: 5125821543982213238
2: 1885446857198079865
3: 1784102302261635709
4: 14888888820055909286
5: 10650267372227927280
6: 1283066103397798384
7: 18174129289355940941
8: 7012091250016467664
9: 3000438492122948673
10: 11954142942718655192
11: 11713281966713340531
12: 13450015493620327431
13: 8527195849335553775
14: 12628903898023244582
15: 14850473871353034915
16: 4938947538669714523
17: 11858523945066023525
18: 4886176751863151491
19: 7367638952773315056
20: 9399101105401083268
21: 13941720072365397720
22: 2022669518369799574
23: 7097704095687072272
24: 18375196213244601545
25: 13851250634050167604
26: 11823658297578414819
27: 5414121733845069545
28: 8369725103947974346
29: 14055721717480188255
30: 16835012238916414748
31: 11534752662811201046
32: 3669262207937771719
33: 14065841566123610476
34: 11048577505222294225
35: 359282477494518661
36: 4417115578808483583
37: 1452811136191383414
38: 14127151791164321382
39: 12170254566408733533

    ... [38 lines of instance data omitted] ...

positions assigned -1.  The lists must be disjoint and together contain every
integer position from 1 through 64.  Positions are 1-indexed, list order does
not matter, and repeated positions are forbidden.  These shape rules make the
second congruence hold; the first is equivalently

  sum(x_i for i in plus) - sum(x_i for i in minus) = 0 (mod 18446744073709551616).

Give your final answer inside <answer></answer> tags, as one JSON object with
exactly the keys "plus" and "minus", each mapped to a JSON list of integers.
Syntax example for a four-position instance:
<answer>{"plus":[1,3],"minus":[2,4]}</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
{"plus": [1, 2, 3, 6, 7, 9, 11, 13, 14, 15, 16, 18, 27, 28, 29, 33, 35, 36, 38, 39, 44, 45, 48, 52, 53, 54, 57, 59, 61, 62, 63, 64], "minus": [4, 5, 8, 10, 12, 17, 19, 20, 21, 22, 23, 24, 25, 26, 30, 31, 32, 34, 37, 40, 41, 42, 43, 46, 47, 49, 50, 51, 55, 56, 58, 60]}
```

---

## 2603.20961 — Graham conjecture on small sets in abelian groups

*additive combinatorial structures* · [paper](https://arxiv.org/abs/2603.20961) · preset `easy` `{"n": 120, "slack": 6}` · search space ≈ `66895029…(199 digits)`

```text
Cyclic distinct-partial-sums problem

Work in the cyclic additive group Z/127Z.  Its elements are the integer residues
0, 1, ..., 126; addition and every sum below are reduced modulo 127.

The following is an unordered set A of 120 distinct nonzero residues:
A = [62, 28, 3, 40, 13, 71, 96, 121, 89, 60, 65, 84, 6, 8, 61, 50, 22, 42, 38, 54, 16, 14, 87, 41, 77, 37, 83, 69, 117, 74, 47, 20, 126, 67, 64, 81, 122, 70, 45, 9, 118, 106, 48, 36, 105, 52, 5, 66, 18, 25, 97, 76, 112, 111, 82, 73, 11, 24, 88, 99, 90, 58, 102, 4, 43, 103, 93, 100, 113, 26, 7, 109, 79, 85, 1, 107, 119, 120, 108, 94, 95, 19, 34, 39, 78, 124, 63, 35, 114, 44, 49, 104, 80, 59, 30, 46, 75, 86, 33, 51, 17, 116, 27, 125, 110, 56, 53, 123, 68, 23, 72, 2, 31, 101, 115, 57, 32, 55, 15, 29]

Find a sequencing of A: output an ordered list a_1, ..., a_120 that uses every
member of A exactly once, with no repetitions.  For each 1-indexed position i,
define the inclusive partial sum p_i = (a_1 + ... + a_i) mod 127.  The residues
p_1, ..., p_120 must be pairwise distinct, and p_i must be nonzero for every
1 <= i < 120.  (The total sum p_120 is fixed by A and is nonzero in this
instance.)  Order matters.  Only the displayed canonical representatives
0 through 126 may be used.

Give your final answer inside <answer></answer> tags, as exactly 120 base-10
integers separated by commas, in the desired order.  Do not put brackets around
the list.  Example of syntax only: <answer>3, 17, 42</answer>
Output nothing else inside the tags.
```

**Answer** (verified ✓):

```json
[9, 63, 56, 73, 71, 108, 5, 25, 86, 46, 107, 22, 44, 7, 95, 11, 120, 35, 75, 90, 125, 99, 101, 15, 31, 93, 106, 81, 117, 74, 88, 59, 48, 42, 1, 37, 53, 6, 122, 110, 76, 65, 77, 113, 111, 89, 36, 50, 39, 34, 116, 49, 102, 20, 30, 41, 4, 118, 55, 69, 13, 43, 72, 29, 40, 112, 8, 114, 28, 26, 84, 18, 2, 105, 82, 100, 96, 51, 14, 79, 45, 66, 123, 70, 83, 3, 94, 17, 58, 78, 67, 47, 54, 23, 97, 24, 85, 121, 64, 124, 103, 52, 126, 38, 57, 19, 62, 104, 16, 119, 115, 109, 33, 27, 61, 60, 68, 80, 32, 87]
```

---

