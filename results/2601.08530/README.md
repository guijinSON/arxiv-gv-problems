# Tournament-fixing witness generator

| axis | declaration |
|---|---|
| native domain | `combinatorics` |
| computational core | `permutation` |
| intended intuition | recursive bracket decomposition |

This is a native discrete tournament-fixing family, not a discretised analogue: the solver receives the directed tournament and designated favorite used in the paper’s own formulation, and searches for a leaf-order permutation.  The bounded-occurrence 3-SAT reduction guides hard-instance construction; it does not replace a continuous object or discard continuous structure, so `NATIVE["reduction"]` is `None`.

This directory turns Wang, Peng, Liu, and Xiao’s [*How Hard Is It to Rig a Tournament When Few Players Can Beat or Be Beaten by the Favorite?*](https://arxiv.org/abs/2601.08530) into a deterministic inverse generator.  The solver receives every predetermined pairwise result in a tournament and must return a complete leaf order for a balanced knockout bracket in which the designated favorite wins.  Verification is exact and cheap: check that the answer is a permutation, replay each round, and compare the final champion.

## Why this is the hard regime

Section 2 and Definition 1 fix the exact seeding and round semantics; Proposition 1 gives the equivalent spanning-binomial-arborescence witness.  General Tournament Fixing is NP-hard.  More specifically, Section 4, Theorem 2 invokes the bounded-occurrence 3-SAT reduction and proves under ETH that no algorithm runs in `2^(2^(ell/c)) * poly(n)` for constant `c > 1`, where `ell` is the favorite’s out-degree.  This generator implements that reduction’s spawning, choice, clause/garbage, and filler gadgets.  It samples a satisfying assignment and formula before constructing the returned seeding and all match outcomes, then randomly relabels every player.

Every emitted favorite beats exactly `ell = log2(n)` players—the minimum possible for a winning favorite.  The easy case `ell < log2(n)` from Theorem 1 is therefore avoided, while `ell` grows with `n`.  The favorite’s in-degree is `n - 1 - log2(n)`, avoiding the small-in-degree FPT regime of Section 5, Theorem 3.  The construction is also far from the acyclic and constant feedback-arc/feedback-vertex regimes summarized in Sections 1 and 6.

## Worked example

This is the full renderer output for the smallest preset, `make_instance(n=256, seed=0)`.  The large outcome table is collapsed only for readability; expanding it shows exactly the string given to a solver.

<details>
<summary>Rendered 256-player instance</summary>

```text
Balanced knockout tournament fixing

There are 256 distinct players, numbered 0 through 255.  Player
191 is the favorite.  For every two distinct players, exactly
one is predetermined to beat the other.

Construct one seeding that makes the favorite champion.  A seeding is a list
containing every player exactly once.  List position is the leaf position and
positions are 0-indexed.  In round 1, positions 0 and 1 play, positions 2 and 3
play, and so on.  In every later round, consecutive surviving winners play in
the same left-to-right order.  A match winner is determined by the table below;
there are no ties or probabilistic outcomes.  Continue until one champion
remains.  Swapping subtrees may describe an equivalent bracket, but your output
must still be a complete 256-integer list.

Outcome table (hexadecimal bit masks): row i is a 64-hex-digit nonnegative
integer.  Its bit j, where the least-significant/rightmost bit is bit 0, is 1
exactly when player i beats player j.  Diagonal bits are 0.  Leading zeroes are
shown and are significant only as padding.

0: 579fa5f227bfd9088f167e79abba3ff200bbaf31323e383f90f37f5da277faf8
1: fffffffffbfbff7ffffeffdfffbf7fffaffdfe7fffffeffffbfbfefffffffffd
2: 57fdb7ff6fbbff7dffb67ddffbbf3fff0dfffe7ffe7f6fbfddfbffff76fffef9
3: 508325f002a8d1088f147e19aa881fe2000a24211234182380501f5d8036a250
4: 1081000002a0d00080041c0108000a2000000000021008008002060000100240
5: 508325f002a8d1088f147e19aa881fe2000a24211234182380521f5d8036a258
6: 1080010000a050000004180100000a2000000000000008000002060000000000
7: 579ba5f226bbd1088f167e19aaaa3fe200bbae211234383790f31f5da277ea78
8: fffffffffbfbff7ffffeffdfffbf7fffaffdfe7fffffeffffbfbfefffffffefd
9: 1080010000a050000004180108000a2000000000001008008002060000100040
10: 571ba5f227bbd9088f167e39abba3fe200bbaf21323d383f90f37f5da277eaf9
11: 579ba5f226bbd1088f166e19aaaa3fe200bbae211234383790f31f5da277e278
12: 571ba5f226bbd9088f167e39abba3fe200bbaf21323c383f90f37f5da277eef8
13: 508301b002a8d1088f147c192a881fc0000a2421123008238052075980348250
14: 579ba5f206b8d1088f167e19aa8a3fe200bbae211234382790f31f5da277a278
15: 108301b002a8d1088d047c112a881ee000082400023008208052065880300250
16: 579ba5f206bad1088f167e19aa8a3fe200bbae211234382790f31f5da276a278
17: 508321b002a8d1088f147c192a881fe2000a242102301823805207598034a250
18: 108301b00288d1088f047c192a881fe0000a2421023008238052075880308250
19: 57ffb5ff6f3bff7dffb677dffbbf3ffb4dfefe7ffa7f5fbfd9fbfffff677fef9
20: 1080030000a050008004180100000a2400000000041008000002060000000040
21: 108301b002a0d1008c043c112a0016a000080400023008208052065080100250
22: 538325f202a8c1088f167e19aa8a1fe2000aac211234182390d31f5da036a278
23: 57ffb5ff6f3bff7dffb677dffbbf3ffb4dfefe7ffa7f5fbfd9fbfffff67ffef9
24: dfffb7ff6ffbfffdffb6ffdffbbd2fff8dfffe7ffe5fdfbffbfbfffff6fffefd
25: 579b25f206ba91088f167e19aa8a3fe2003bac211234182790f31f5da076a278
26: 57ffb5f727bffd189f167e7debbb3ffa10ffaf39327f3c3fd1f3ffddb277fef9
27: ffffffffebfbff7dfbb7ffdff9bf3fff8ffff67fffffffbffbfbfffff7fffefd
28: 57dfa5f727bffd189f167e7debbb3ff210fbaf39323f383f91f37f5da277fef9
29: 518325f202a8c1088f167e19aa8a1fe2000aac211234182390d31f5d8036a278
30: 57ffb5ff27bfff399fb67effebbb3ffb15ffef79b27f3cbfd1f3ffdfb677fef9
31: 9080010000a0d0008004180108000a2000000000021008008202060000100254
32: 508301b002a8d1088f147c192a881fe0000a2421123008238052075880348250
33: 57ffb5ff2fbfff399fb67effebbb3ffb15ffef79b27f3cbfd1f3ffddb677fef9
34: 508325f002a8d1088f147e19aa881fe2000a24211234182380521f598036a250
35: 108301b002a0d1008c043c112a001ea000080000023008208052065080300250
36: 1083012002a0d10088043c1128001ea000000000023008208012064080100250
37: 47ffb5ff2fbfff7dffb67ffffbbb3ffb1dffef7fba7f3fbfd9fbffdff677fef9
38: 1083000002a0d00080041c0108000aa000000000021008008002060080100250
39: 57ffb5f727bffd189f167e7debbb3ffa10ffaf39327f383fd1f3fd5db277fef9
40: 108301b012a8d1088d047c192a881ee0000a2420023008228052065880308352
41: 0080010000205000800010000000082004000000000008004002848000000000
42: 0000010000200008000000080088082000000000000008000000000000000000
43: 508321b002a8d1088f147c19aa881fe2000a242112341823805207598036a250
44: 508325b002a8d1088f167e19aa881fe2000a24211234182390d00f598036a250
45: 579ba5f206bbd1088f167e39abaa3fe200bbae213234383790f35f5da277eaf8
46: 579ba5f226bbd1088f167e19abaa3fe200bbae211234383790f31f5da277eaf8
47: 57dfa5f727bffd189f167e7debbb3ffa10fbaf39327f383f91f37d5db277fef9
48: 508325f202a8d1088f167e19aa8a1fe2000aa4211234182380d21f5d8036a278
49: 0000014200200000800000000000080000000000000008000000140000000008
50: fffffffffffbff7ffdfeffdfffbf7fffaffef67efffffffffbfbffffffffffff
51: 57ffb5ff2fbfff799fb67ffffbbb3ffb1dffef7dba7f3dbfd1f3ffdff677fef9
52: 1883012002a0d0008004bc1108000aa00000000002100820a002064080100250
53: 538325f202a8d1088f167e19aa8a1fe2000aac211234182390d31f5da076a278
54: 108301a002a0d10088043c11280016a000080000023008208012065080100250
55: 508325f202a8d1088f167e19aa8a1fe2000aa4211234182380520f5d8036a278
56: 57dfa5f327bffd088f167e78ebbb3ff210bbaf31323f383f90f37f5da277fef9
57: 57fdb7ff6fbbff7dffb67ddffbbf3fff0dfffe7ffe7f6fbfddfbffff76fffefd
58: 7fffffffffbfff7ffffeffffffffffff7fffff7fffff7fbff9fffffffffffffb
59: 57ffb5ff2fbfff79dfb67ffffbbb3ffb1dffef7dba7f3dbfd1fbffdff677fef9
60: 508325f202a8d1088f167e19aa8a1fe2000aac211234182380d30f5d8036a278
61: d7ffb7df6ffbfffdffb67ddffbbf3fff8dfffe7ffe7fefbfdbebfffff6fffefd
62: 57dfb5f727bffd189f167e7debbb3ffa10fbaf39327f383f91f3fd5db277fef9
63: 1080010000a0d0000004180108000a2000000000001008000002060000100040
64: 108301b00288d1088d047c192a881ee0000a2420023008208052075880308250
65: 108301b00288d1088f047c192a881ee000082421023008218052065880308250
66: 569b25f202a8d1088f167e19aa8a1fe2000bac211234182390f31f5da076a278
67: 579ba5f206bbd9088f167e39abba3fe200bbaf21323c383790f37f5da277eaf8
68: 579ba5f206bad1088f167e19aa8a3fe200bbae211234382790f31f5da277e278
69: 1083010002a0d00080041c0108000a2000000000021008008002064080100250
70: ffffffffefffffffffffffffffbf7fffffffffffffffffbffffbfffffffffefd
71: 57ffb5f727bffd399f167e7debbb3ffa14ffaf39327f3c3fd1f3ffddb677fef9
72: 57ffb5ff2fbfff399fb67effebbb3ffb15ffef7dba7f3cbfd1f3ffdff677fef9
73: 57ffb5ff2fbfff799fb67ffffbbb3ffb1dffef7dba7f3dbfd9fbffdff677fef9
74: 57dfb5f727bffd189f167e7debbb3ffa10ffaf39327f383fd1f3ffddb277fef9
75: 00000100000000000800001020000c0000000000000000000000000000000000
76: d88321b012a8d1088f14fc192a881fe0000a242112300823a25207598034a356
77: 579badf206bad10a8f1e7e19aa8a7fe2003bac2112b4582790f31f5da3fea278
78: 57ffb5ff6f3bff7dffb677dffbbf3ffb4dfefe7ffa7f1fbfd9fbfffff677fef9
79: d7feb7ff6dbbff7dffb67fdffbbf3fff0dfef67ffe7f7fbfdffbfffff6fffefd
80: 579fa5f227bff9088f167e79abba3ff210bbaf31323e383f90f37f5da277faf9
81: 579fa5f226bbd9088f167e79abba3fe200bbaf21323c383f90f37f5da277fef8
82: 508321b002a8d1088f147c19aa881fe2000a242102301823805207598036a250
83: 579ba5f206bbd9088f167e39abaa3fe200bbae213234383790f37f5da277eaf8
84: 1080030000a050008004180100000a2400000000040008000002060000000040
85: 1083092002a0d00088043c0108000aa000000000029008208012064081100250
86: 57dfa5f327bffd189f167e7debbb3ffa10fbaf39323f383f91f37f5db277fef9
87: dfffbfff6ffbfffdffb6ffdffbbd2fff8dfffe7ffe5fdfbffbfbfffff7fffefd
88: dfffbf7feffaff7dffb7ffdffbbd3fff8df7fe7ffeffffbffbfbfffff7fffefd
89: 1080010000a0d0008004180108000a2000000000001008008002060000100240
90: 57ffb7ff6fbaff7dffb67ddffbbf3fff4dfffe7ffa6f7fbfd9fbfffff6effef9
91: 57ffb5ff2fbfff399fb67efffbbb3ffb15ffef7db27f3cbfd1f3ffdff677fef9
92: 108305b002a8d1088f147c192a881fc0000a2421023408238052075880368250
93: 579ba5f226bbd1088f166e39abaa3fe200bbae211234383790f35f5da277eaf8
94: 57ffb5ff2fbfff7ddfb67ffffbbb3ffb1dffef7dba7f3fbfd9fbfffff677fef9
95: 57ffb5f727bfff399fb27e7febbb3ffa14ffef39327f3cbfd1f3ffddb677fef9
96: 108301b002a8d1088d047c192ac89ee0000a2420023008218056075880308250
97: 57ffb5ff2fbfff7ddfb67ffffbbb3ffb1dffef7dfa7f3fbfd9fbffdff677fef9
98: 57ffb5ff2fbfff399fb67effebbb3ffb15ffef79b27f3cbfd1f3ffdff677fef9
99: 57dfa5f327bffd188f167e7debbb3ff210fbaf31323f383f91f37f5da277fef9
100: 571fa5f226bfd9088f167e79abba3fe200bbaf21323e383f90f37f5da277fef8
101: 108301b002a8d1088d047c192a881ee000082400023008208052065880308250
102: 57ffb5ff27bfff399fb67effebbb3ffb15ffef39b27f3cbfd1f3ffddb677fef9
103: fffffffffffffffdffb7fffffbffbfffdfffff7fffffffbfffffffffffffffff
104: ff9beff2b6fbd90a8f5efe39affaffe6a2bbae2137bcf837b2f77f5dabffebfe
105: 579ba5f206b8d1088f167e19aa8a3fe200bbac211234382790f31f5da276a278
106: 108301b002a0d1008c043c112a0016a000080000023008208052065880100250
107: 508365f202e8d1088f167e19aaca9fe2820aa4211234982380d71f5d8836a278
108: 57ffb5ff6fbfff7ddfb67ffffbbf3ffb1dffef7ffa7f3fbfd9fbfffff677fef9
109: 108301b002a8d10a8c0c7c112a005ee000080400023008208052065880300250
110: 57ffb5f727bfff399f167e7debbb3ffa14ffaf39327f3cbfd1f3ffddb677fef9
111: 508325f202a8d1088f167e19aa8a1fe2000a24211234182380521f5d8036a278
112: 538325f202e8d1088f167e19aaca9fe2800aac211234d82390f71f5da0fea278
113: 108301b012a8d1088d047c192a881ee000082420023008228052065880308352
114: 57dfb5f727bffd189f167e7debbb3ffa10fbaf39327f383fd1f3ff5db277fef9
115: 3083013082a0d10088043c1128001ea000000000033008208012065080100250
116: 579b25f206bad1088f167e19aa8a3fe2002bac211234182790f31f5da076a278
117: 579b25f202a8d1088f167e19aa8a1fe2000bac211234182790f31f5da076a278
118: 57dfa5f327bffd088f167e7debbb3ff210bbaf31323f383f91f37f5da277fef9
119: 579ba5f206ba91088f167e19aa8a3fe2003bac211234382790f31f5da276a278
120: 57ffb5ff27bfff399fb67e7febbb3ffb14ffef39b27f3cbfd1f3ffddb677fef9
121: ffffbfffebfbff7dfbb7ffdff9bf3fff8dfff67fffffffbffbfbfffff7fffefd
122: 57ffb5f727bffd389f967e7debbb3ffa10ffaf39327f3c3fd1f3fdddb677fef9
123: 47ffb5ff2fbfff799fb67ffffbbb3ffb15ffef7dba7f3dbfd1f3ffdff677fef9
124: ff9feff2b7fff90a8f5efe79affafff6a2bbaf3137bef83fb2f77f5dabffffff
125: ffffffffeff2ff7dfff6ffdffbbd3fbf8ffffeffffffffbffbfbfffffffffefd
126: fffffdffffffff7ffffefffffffffffbbfffff7ffbffbfbffbffffffff77ffff
127: d7feb7ff6dfbff7dffb67fdffbbf3fff0dfef67ffe7fffbfdffbfffff6fffefd
128: 57ffb5ff27bfff399fb67effebbb3ffa14ffef39b27f3cbfd1f3ffddb677fef9
129: 508321b002a8d1088f147c192a881fc0000a242112301823805207598034a250
130: 57ffb7ff6fbaff7dffb67ddffbbf3ffb4dfffe7ffa6f7fbfd9fbfffff6effef9
131: 57dfa5f327bffd088f167e7cebbb3ff210fbaf39323f383f91f37f5db277fef9
132: 579fa5f227bfd9088f167e79abba3fe200bbaf31323e383f90f37f5da277fef8
133: 4000010000200000800000000000080200000000100008000002000000002000
134: 108301b002a0d1008c447c112e801ea020080400023008208052065880300250
135: 1083000002a0d00080041c0108000a2000000000021008208002060080100250
136: 108301b00288d1088f147c192a881ee0000a2421023008238052075880308250
137: 1080010000205000800410010000082000000000000008000002060000000000
138: 1083012002a0d10088043c1108001aa000000000023000208012064080100250
139: 0000011000000000800000000000000000000400000000000040000000200000
140: 1083092002a0d00088043c0108000aa00000000002b008208012064081100250
141: 579b25f206ba91088f167e19aa8a1fe2002bac211234182790f31f5da076a278
142: ffffffffebfbff7ffefeffdfffbf3fffafffdeffffffdfbffbfbfffffffffefd
143: fffffffffffbff7ffdfeffdfffbf7fffaffef67efffffffffbffffffffffffff
144: 57dfa5f327bffd088f167e7debba3ff210bbaf31323f383f90f37f5da277fef9
145: 70832df082a8d1088f547e19ae881fe2200a242113b4182380521f5d8136a278
146: 57ffb5ff6fbfff7dffb67ffffbbb3ffb1dffef7ffa7f3fbfd9fbfffff677fef9
147: 108301b002a8d1088d047c192a801ee000082400023008208052025880300250
148: 579ba5f226bbd9088f167e39abaa3fe200bbae21323c383790f37f5da277eaf8
149: 579ba5f206b9d1088f167e19aa8a3fe200bbae211234383790f31f5da277e278
150: fffffffffffbff7ffdfeffdfffbfffffaffef67efffffffffbffffffffffffff
151: 108301b002a0d1088d047c112a001ea000082400023008208052025880300250
152: 579ba5f226bbd1088f166e19aaaa3fe200bbae211234383790f31f5da277eaf8
153: 108341a002a0d10088043c1128001ea002080000023008208052065088100250
154: ffffffffeff2ff7dfff6ffdffbbd3fbfaffffeffffffffbffbfbfffffffffefd
155: 10800100002050000004100100000a2000000000001008000002060000100040
156: 57ffb5ff27bfff399fb67effebbb3ffb15ffef7db27f3dbfd1f3ffdff677fef9
157: 1083012002a0d00088043c1108001ea000000000023000208012064080100250
158: 57dfa5f327bffd088f167e79abba3ff210bbaf31323f383f90f37f5da277fef9
159: 508321b002a8d1088f147c192a881fe2000a242112301823805207598036a250
160: 0080010100204400800410000000082800000000000008000102060000000000
161: 57ffb5f727bfff399f927e7debbb3ffa14ffef39327f3cbfd1f3ffddb677fef9
162: 57dfa5f327bffd088f167e79ebba3ff210bbaf31323f383f91f37f5da277fef9
163: 108301b002a8d1088d047c112a801ee000082400023008208052025880308250
164: 1083010002a0d00088043c0108001aa000000000023000208002064080100250
165: ff9beff2b6fbd10a8f5efe19afeaffe6a2bbae2117b4f837b2f75f5dabffebfe
166: 579ba5f226bbd9088f167e39abba3fe200bbaf21323c383f90f37f5da277fef8
167: 57ffb5ff27bfff399fb27e7febbb3ffa15ffef39b27f3cbfd1f3ffddb677fef9
168: 47ffb5ff2fbfff399fb67efffbbb3ffb15ffef7dba7f3dbfd1f3ffdff677fef9
169: d88323b002a8d1088f14fc19aa881fe6000a242116341823a2520f598036a254
170: 1082000000a0d0008004180108000a2000000000021008008002060080100240
171: 10800100002050008004100108000a2000000000000048000002060000880000
172: 0080010020204000800000000100082000000000200008000002040000000800
173: 1083010002a0d00080041c0108000aa000000000021008208002064080100250
174: 108301b002a0d1008c043c112a001ea000080400023008208052065880300250
175: dfffb7df6ffbfffdffb67ddffbbf3fff8dfffe7ffe7fefbffbebfffff6fffefd
176: dfffbfff7ffffffffffefffffffffffffdffff7ffeffffbffffffffff7ffffff
177: 508325f202a8d1088f147e19aa8a1fe2000a24211234182380520f5d8036a278
178: 1080010008205000800010820000082000000000800008000002060000000000
179: ffffffffebfbff7ffef6ffdfffbf3fffafffdeffffffdfbffbfbfffffffffefd
180: 108301b002a8d1088f047c192a881ee0000a2421023008238052075880348250
181: 57ffb5f727bfff399f967e7febbb3ffa14ffef39327f3cbfd1f3ffddb677fef9
182: ffffffffeff2ff7dffb6ffdffbbd3fbf8ffffeffffffffbffbfbfffffffffefd
183: 57ffb5f727bffd399f167e7debbb3ffa10ffef39327f3cbfd1f3ffddb677fef9
184: 108301b002a8d10a8c0c7c112a005ee000082400023008208052065880300250
185: 108301b002a8d1088d047c192ac89ee0000a2421023008218056075880308250
186: 108341a002a0d10088043c112a001ea002080000023008208052065088100250
187: 1083012002a0d00080043c0108000aa000000000021000208012064080100250
188: 57dfa5f327bffd188f167e7debbb3ffa10fbaf39323f383f91f37f5da277fef9
189: 57ffb5ff6fbfff7ddfb67ffffbbb3ffb1dffff7ffa7f3fbfd9fbffdff677fef9
190: 47ffb5ff2fbfff799fb67ffffbbb3ffb1dffef7dba7f3fbfd1fbffdff677fef9
191: 0000010000001000000000000800000000000000000008008000040000000240
192: 57ffb5f727bffd189f167e7debbb3ffa14ffaf39327f3c3fd1f3ffddb677fef9
193: ffffffffebfbff7dfef6ffdfffbf3fffafffdeffffffdfbffbfbfffffffffefd
194: 57ffb5ff2fbfff79dfb67ffffbbb3ffb1dffef7dba7f3fbfd9fbffdff677fef9
195: 108301b002a8d1008c047c112a001ee000080400023008208052025880300250
196: 57dfa5f327bffd088f167e7debbb3ffa10fbaf31323f383f91f37f5da277fef9
197: 57ffb5f727bffd199f167e7debbb3ffa10ffaf39327f3c3fd1f3ffddb677fef9
198: 57ffb5ff2fbfff399fb67ffffbbb3ffb15ffef7dba7f3dbfd1f3ffdff677fef9
199: f7fff7ffffffff7ffffe7fffffffffffffffff7fff7fffbfdffffffffeffffff
200: 1083012002a0d00088043c1128001aa000000000023008208012064080100250
201: 57ffb5f727bffd399f967e7debbb3ffa14ffaf39327f3cbfd1f3ffddb677fef9
202: 57dfa5f327bff9088f167e78abba3ff210bbaf31323f383f90f37f5da277fef9
203: 579ba5f226bbd1088f167e39abaa3fe200bbae213234383790f37f5da277eaf8
204: 0500010000204000000010010000082000000000000008000002040020400000
205: 579fa5f227bfd9088f167e79abba3ff200bbaf31323e383f90f37f5da277fef9
206: 0000010000220000800000000000282000800000000008000002040002000000
207: 1080010000a050008004180108000a2000000000001008000002060000100240
208: 779ba7f286bad1088f567e19ae8a3fe620bbae211734383790f31f5da277e278
209: 579b25f206b891088f167e19aaaa1fe2002bae211234182790f31f5da076e278
210: ff9feff2b6fbd90a8f5efe79affaffe6a2bbaf2137bef83fb2f77f5dabfffffe
211: 108301b002a0d1008c447c112e801ee020080400023008208052065880300250
212: 569b25f206a8d1088f167e19aa8a1fe2002bac211234182790f31f5da076a278
213: 0000010000000000800000000000090000000000000008030000000000040000
214: d7feb7ff6dbbff7dffb67fdffbbf3fff0dfef67ffe7fffbfdffbfffff6fffefd
215: 10800100002050008004180108000a2000000000000048000002060000880000
216: 579fa5f226bfd9088f167e79abba3fe200bbaf31323e383f90f37f5da277faf8
217: 1082010000e0d00080041c0108000a2080000000021088008002060080100240
218: 579b65f212a8d10a8f1e7e19aa8a5fe2022bac211234182790f31f5da876a37a
219: 57ffb5ff27bfff399fb27efffbbb3ffb15ffef79b27f3cbfd1f3ffddf677fef9
220: ffffffffebfbff7ffffeffdfffbf7fffaffdfe7fffffeffffbfbfefffffffefd
221: 579ba5f206bbd1088f166e19aaaa3fe200bbae21123c383f90f33f5da277e278
222: 57ffb5ff2fbfff7ddfb67ffffbbb3ffb1dffef7ffa7f3fbfd9fbfffff677fef9
223: dfffbf7f6ffaff7dffb7ffdffbbd3fff8df7fe7ffeffffbffbfbfffff7fffefd
224: 579fa5f227bff9088f167e78abba3ff210bbaf31323f383f90f37f5da277fef9
225: 508325f002a8d1088f147e19aa8a1fe2000a24211234182380501f5d8036a278
226: 57dfa5f327bffd189f167e7debbb3ffa10fbaf39327f383f91f37f5da277fef9
227: 57ffb5f727bfff399fb67e7febbb3ffa14ffef39b27f3cbfd1f3ffddb677fef9
228: 1083012002a0d1008c043c112a0016a000000000023008208052065080100250
229: 1883010002a0d0008004bc1108000aa00000000002100820a002064080100250
230: 508325b002a8d1088f147e19aa881fe2000a24211234182380501f598036a250
231: 3083013082a0d10088043c1128001ea000080000033008208012065080100250
232: 0000000000000000000004000000008000000000000000000000004000000010
233: 57ffb5ff6fbaff7dffb67ddffbbf3ffb4dfffe7ffa6f7fbfd9fbfffff6effef9
234: 508321b002a8d1088f147e19aa881fe2000a24210234182380520f598036a250
235: dfffb7ff6ffbfffdffb6ffdffbbd2fff8dfffe7ffe5fdfbffbfbfffff7fffefd
236: 57dfa5f727bffd189f167e7debbb3ffa10fbaf39327f383f91f3ff5db277fef9
237: 508301b002a8d1088f147c192a881fe0000a242112300823805207598034a250
238: ffffbfffebfbff7dfbb7ffdff9bf3fff8ffff67fffffffbffbfbfffff7fffefd
239: 579b25f206bad1088f167e19aa8a3fe2003bac211234182790f31f5da276a278
240: 1082010002e0d00080041c0108000a2080000000021088008002060080100240
241: 9080010000a0d0008004180108000a2000000000021008008202060080100254
242: 571ba5f226bbd9088f167e79abba3fe200bbaf21323c383f90f37f5da277fef8
243: 579325f202a8d1088f167e19aa8a1fe2000bac211234182390f31f5da076a278
244: 568325f202a8d1088f167e19aa8a1fe2000bac211234182390f31f5da076a278
245: 57dfb5f727bffd189f167e7debbb3ffa10ffaf39327f3c3fd1f3ff5db277fef9
246: 579fa5f327bff9088f167e79abba3ff210bbaf31323f383f90f37f5da277fef9
247: 0004010000205000800000000000082000000010000008000002040000001400
248: 509325f202b8c1088f167e19aa8a1fe2000aac211234182790d31f5d8036a278
249: 518325f202a8d1088f167e19aa8a1fe2000aac211234182390d31f5da036a278
250: 538325f202a8c1088f167e19aa8a1fe2000bac211234182390f31f5da076a278
251: d7ffb7df6ffbfffdffb67ddffbbf3fff8dfffe7ffe7fefbffbebfffff6fffefd
252: 0080010000205000c00011010000082008000000000008000002062000000000
253: dfffbf7feffaff7dffb7ffdffbbd3fff8df7fe7fffffffbffbfbfffff7fffefd
254: 108301b002a8d1088f147c192a881fc0000a2421123008238052075880348250
255: 57fdb7ff6fbbff7dffb67ddffbbf3fff0dfffe7ffe7f6fbfdffbffff76fffefd

Give your final answer inside <answer></answer> tags, as 256 comma-separated
base-10 player numbers in leaf order.
Example format: <answer>0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255</answer>
Output nothing else inside the tags.
```

</details>

The planted response is:

```text
<answer>191, 9, 63, 207, 6, 171, 215, 78, 155, 137, 84, 233, 20, 130, 90, 126, 232, 38, 135, 69, 4, 217, 240, 79, 170, 89, 31, 2, 241, 57, 255, 58, 75, 157, 138, 200, 187, 229, 52, 61, 164, 173, 85, 24, 140, 235, 87, 199, 139, 21, 106, 35, 54, 115, 231, 223, 228, 36, 153, 121, 186, 238, 27, 176, 42, 147, 163, 15, 151, 109, 184, 193, 195, 174, 134, 182, 211, 125, 154, 103, 213, 18, 136, 180, 65, 96, 185, 50, 64, 101, 113, 220, 40, 8, 1, 70, 133, 254, 13, 32, 129, 237, 76, 175, 92, 17, 82, 159, 234, 43, 169, 251, 49, 230, 3, 34, 225, 5, 145, 253, 44, 177, 55, 111, 60, 48, 107, 127, 204, 29, 22, 249, 250, 53, 112, 150, 248, 244, 66, 243, 212, 117, 218, 142, 206, 141, 25, 116, 119, 239, 77, 179, 209, 105, 14, 16, 149, 68, 208, 88, 172, 11, 152, 7, 93, 46, 165, 19, 221, 45, 83, 203, 67, 148, 104, 143, 247, 12, 242, 166, 100, 81, 210, 214, 10, 216, 0, 132, 80, 205, 124, 23, 160, 224, 202, 246, 56, 158, 144, 162, 131, 118, 99, 196, 28, 188, 226, 86, 41, 47, 62, 236, 39, 114, 245, 74, 122, 26, 197, 192, 183, 71, 110, 201, 178, 161, 95, 181, 167, 227, 120, 128, 219, 102, 30, 33, 156, 98, 72, 91, 252, 168, 123, 198, 190, 51, 73, 59, 37, 194, 97, 94, 189, 222, 108, 146</answer>
```

`verify(inst, parse_answer(response))` returns `(True, "ok")`.  Removing the last label returns `(False, "wrong length: expected 256, got 255")`.

## Difficulty presets

| preset | players `n` | favorite out-degree | latent variables | rendered characters | status |
|---|---:|---:|---:|---:|---|
| `easy` | 256 | 8 | 6 | 20,235 | **shipping; hardened** |
| `medium` | 512 | 9 | 12 | 72,205 | local gates pass; not needed by oracle loop |
| `hard` | 1,024 | 10 | 24 | about 275K | local G1 passes; not needed by oracle loop |

`SHIPPING_DIFFICULTY = "easy"`.
After the named ladder, `escalate({"n": 1024})` supplies one final 2,048-player rung and then returns `None`.

Two earlier constructions were rejected rather than promoted to presets.  A conditioned random tournament was solved by the randomized greedy protector on 50/50 instances.  Tightening every favorable opponent to its planted wins stopped that attack but exposed the intended round in the opponent’s degree; a construction-aware subtree assembler then solved 20/20.  The shipped SAT-gadget construction is the response to both failures.

## Gate results

| gate | measured result |
|---|---|
| G1 planted verifies | 12/12 across all presets and four seeds each |
| G2 corruption | 5/5 rejected with five distinct reasons |
| G3 round trip | 256 labels recovered from tagged output with prose and a Markdown fence |
| G4 guess resistance | 0 hits / 200,000 uniform complete permutations; empirical rate 0 |
| G5 shipping difficulty | at shipping `n=256`, 0/200,000 uniformly sampled complete permutations verified; the exact subset DP examined 50,000 subset states and hit its cap without a witness in 0.08911326713860035 seconds |
| G6 adversaries | degree order 0/8; greedy protector 0/8; 256 randomized greedy restarts 0/8; capped exact subset DP 0/8 |
| G7 scaling | 512-player doubled instance built and verified; renderer grew 20,235 → 72,205 characters |
| G8 canonical key | 60/60 relabeling/composition checks, 60/60 transported witnesses, 20/20 unrelated keys distinct |

The complete machine-readable measurements are in [`selftest_report.json`](selftest_report.json).

## Oracle loop

The required harness hardened the first level, so no escalation was used.  Errors are retained but do not count as failed solves.

| preset | model | seed | result | reason |
|---|---|---:|---|---|
| `easy` | GPT-5.6 Terra | 2,119,421,974 | failed | parsed 256 labels; champion was 171, not favorite 31 |
| `easy` | Grok 4.6 | 1,088,832,296 | error, not counted | 900-second hard deadline |
| `easy` | Claude Sonnet 5 | 1,107,697,795 | failed | empty length-limited response after 32K completion tokens |
| `easy` | Gemini 3.1 Pro Preview | 741,731,120 | failed | parsed 257 labels; required 256 |

The authoritative records, replies, timings, and master seed are in [`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl) and `.meta.json`.

## Use

```python
import random
import gen_2601_08530 as gen

inst = gen.make_instance(seed=7, **gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY])
question = gen.render(inst)
candidate = gen.parse_answer(model_reply)
ok, reason = gen.verify(inst, candidate)

# Baseline candidate used by G4:
guess = gen.random_candidate(inst, random.Random(123))
```

From the repository root, emit fresh dataset records with:

```bash
bash scripts/emit.sh 2601.08530 20 easy
```

## Caveats

Theorem 2 is a worst-case asymptotic result; it does not prove that this planted distribution is average-case hard.  G4 samples uniformly from all complete permutations after enforcing the obvious shape and uniqueness constraints.  Its 0/200,000 result is an empirical observation, not an upper confidence bound below `1e-6`, and it says nothing about a construction-aware prior.

The strongest measured baseline is cheap: on the shipping instance, the exact subset DP reached its 50,000-state cap without a witness in 0.08911326713860035 seconds.  This fast resource-limited failure is not evidence of intrinsic hardness; it only says that this attack did not find a witness before its small cap.  The same attack exhausted that cap on all eight G6 trials.  The full `2^n`-scale exact algorithm, the paper’s full color-coding FPT implementation, SAT/ILP encodings, and a bespoke decoder for the reduction gadgets were not run.  Such a decoder is the most important untested attack, especially because the shipping construction contains only six latent Boolean variables even though random relabeling obscures the gadgets.  The oracle evidence is also mixed: two vendors returned malformed or losing concrete candidates, while Claude’s counted failure was an empty length-limited response.  Finally, exact solution density cannot be enumerated at the minimum supported size; the shipping measurement is instead 0 valid answers among 200,000 uniform samples.  These limitations are why the transcript, sampled density, and attack costs are reported rather than treating the theoretical theorem or a large `256!` space as standalone evidence.

For canonicalization, rooted directed color refinement is required to become discrete; generation retries otherwise.  This yields an exact canonical serialization for emitted instances and was tested under arbitrary player relabelings and compositions, but it is not a general-purpose tournament-isomorphism algorithm for hand-built instances passed directly to `canonical_key`.
