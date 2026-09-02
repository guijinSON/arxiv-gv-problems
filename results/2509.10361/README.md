# Verified generator for arXiv:2509.10361

## What the family is

This module generates the weighted-star restriction of **Load-and-Gas-Capacitated
Vehicle Routing** from [Döring et al., “Parameterized Complexity of Vehicle
Routing”](https://arxiv.org/abs/2509.10361). There is one depot at the centre and
every client is a leaf. A solver must partition all clients into three-client
closed routes, each containing one X, one Y, and one Z client. The checker
reconstructs each route through the depot and checks client coverage, unit load,
per-route gas, and the total integer weight. Any valid routing is accepted.

Generation is inverse: client types and a hidden perfect X-Y-Z matching are
sampled first. Each matched row receives an exchangeable random positive
composition of a common target; all client values are distinct, and X/Y/Z have
the same marginal distribution. Accidental exact-sum triples are indistinguishable
decoys rather than a separate distribution.

## Why it is hard

Section 2.2 fixes the exact routing definition, including the client-to-route
assignment and the fact that load is charged by assignment. Section 4.3's
theorem stating “LoadGasCVRP is strongly NP-hard, even on stars with one depot,
constant load capacities and unit demands” (source label
`thm:loadgascvrp_np_const_demand`) reduces strongly NP-complete Numerical
3-Dimensional Matching to this exact star construction. It proves strong
NP-hardness with treewidth 1, one depot, unit demands, and load capacity 3. The
edge-weight tags 1, 4, and 16 force every tight route to contain one client of
each type.

The easy regimes in Section 4 were deliberately avoided. The paper gives an
`|C|^{O(|C|)}` algorithm, FPT algorithms in `k+ell` and (without zero-weight
edges) total weight `r`, and an XP algorithm in `treewidth+ell+g`. Here
`|C|=3n`, `k=n`, `g=Theta(n)`, and `r=Theta(n^2)` all grow. The fixed parameters
are exactly those retained by the Section 4.3 hardness theorem.

## Worked example (`medium`, seed 0)

This is the complete rendered instance. The compact client rows use
`ID:VALUE:EDGE_WEIGHT` entries.

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
X 4:209:13377 5:152:9729 7:214:13697 15:77:4929 17:199:12737 18:150:9601 20:90:5761 22:127:8129 23:165:10561 24:132:8449 26:336:21505 28:107:6849 30:229:14657 33:94:6017 35:96:6145 44:161:10305 45:126:8065 47:207:13249 48:230:14721 49:337:21569 50:82:5249 51:284:18177 53:74:4737 55:117:7489 59:187:11969 60:173:11073 68:79:5057 74:245:15681 76:108:6913 77:163:10433 83:111:7105 84:91:5825 85:92:5889 89:138:8833 90:210:13441 96:72:4609 97:204:13057 98:172:11009 101:236:15105 102:223:14273 112:290:18561 114:166:10625 115:417:26689 121:113:7233 128:188:12033 133:196:12545 143:129:8257 144:338:21633
Y 1:186:11908 2:260:16644 3:185:11844 6:357:22852 9:213:13636 12:125:8004 14:119:7620 16:97:6212 21:265:16964 29:303:19396 31:123:7876 32:189:12100 37:95:6084 38:371:23748 39:160:10244 42:177:11332 52:205:13124 54:242:15492 58:277:17732 63:122:7812 64:167:10692 66:341:21828 70:256:16388 75:162:10372 80:104:6660 81:273:17476 86:271:17348 87:211:13508 93:135:8644 95:169:10820 100:137:8772 105:73:4676 106:171:10948 107:311:19908 110:134:8580 111:130:8324 113:292:18692 119:314:20100 120:264:16900 122:100:6404 124:285:18244 126:300:19204 129:352:22532 135:105:6724 136:194:12420 139:280:17924 140:83:5316 142:306:19588
Z 8:175:11216 10:220:14096 11:405:25936 13:115:7376 19:275:17616 25:147:9424 27:178:11408 34:101:6480 36:327:20944 40:238:15248 41:331:21200 43:221:14160 46:192:12304 56:109:6992 57:262:16784 61:88:5648 62:315:20176 65:307:19664 67:142:9104 69:106:6800 71:286:18320 72:151:9680 73:325:20816 78:78:5008 79:226:14480 82:222:14224 88:112:7184 91:86:5520 92:268:17168 94:316:20240 99:93:5968 103:128:8208 104:399:25552 108:120:7696 109:81:5200 116:233:14928 117:212:13584 118:149:9552 123:195:12496 125:170:10896 127:140:8976 130:248:15888 131:153:9808 132:103:6608 134:121:7760 137:80:5136 138:217:13904 141:155:9936

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly 48 three-integer arrays.  Each inner array is one route group;
do not include the depot and do not repeat a client ID.
Format example only: <answer>[[4, 1, 8]]</answer>
Output nothing else inside the tags.
```

The planted witness is:

```json
[[4,135,57],[5,1,40],[7,87,72],[15,122,104],[17,3,46],[18,142,108],[20,120,82],[22,63,36],[23,37,94],[24,95,19],[26,12,13],[28,6,88],[30,136,131],[33,21,138],[35,124,123],[44,64,130],[45,139,125],[47,140,71],[48,106,8],[49,111,56],[50,129,67],[51,100,141],[53,16,11],[55,38,61],[59,107,78],[60,70,25],[68,58,10],[74,14,117],[76,54,79],[77,113,134],[83,110,41],[84,39,73],[85,42,65],[89,31,62],[90,81,99],[96,86,116],[97,80,92],[98,29,34],[101,75,27],[102,9,127],[112,52,109],[114,32,43],[115,105,91],[121,119,118],[128,2,103],[133,126,137],[143,66,69],[144,93,132]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Removing one client
from the first group returns `(False, "each route group must contain exactly 3
client IDs")`.

## Difficulty presets

| Preset | Routes `n` | Clients | Target `b` | Structural space `(n!)^2` | Status |
|---|---:|---:|---:|---:|---|
| `medium` | 48 | 144 | 576 | about `1.54e122` | **ships; held all three oracle calls** |
| `hard` | 72 | 216 | 864 | about `3.75e207` | available; not reached |

No preset was rejected by a local gate. `escalate()` grows `n` by one third,
which increases both matching depth and the number of accidental exact triples.

## Gate results

| Gate | Measured result |
|---|---|
| G1 planted verifies | 8/8 across both presets |
| G2 corruption | 5/5 rejected with 5 distinct reasons |
| G3 parser | model-style fenced response round-tripped; 4/4 garbage cases returned `None` |
| G4 structured guessing | **0/200,000** under uniform type-correct perfect partitions |
| G5 sparsity | 1/518,400 valid on exact `n=6` probe (`1.929e-6`) |
| G6 attacks | value-rank 0/8; MRV greedy 0/8; 64 random restarts 0/8 |
| G7 scaling | `n=96` / 288 clients built and verified |
| G8 canonical key | invariance 60/60; carried witnesses 60/60; unrelated keys 24/24 |

The canonical key is complete for this restricted topology: a one-depot weighted
star is determined up to vertex relabeling by its sorted client records and global
bounds. It ignores client IDs and input row order.

## Oracle loop

The required harness used fresh seeds, effort `medium`, and three distinct
vendors. Only Terra emitted a witness; it parsed correctly but duplicated a
client. The other two calls returned HTTP 200 with no answer after consuming
their response budget, which the harness records as length-limited failures.

| Preset | Model | Seed | Solved? | Why |
|---|---|---:|---|---|
| `medium` | `openai/gpt-5.6-terra` | 1277287804 | no | parsed 48 groups; duplicate client |
| `medium` | `anthropic/claude-sonnet-5` | 542247942 | no | empty length-limited response after 32,000 completion tokens |
| `medium` | `google/gemini-3.1-pro-preview` | 1026103546 | no | HTTP-200 empty response, provider finish reason `error` |

Harness verdict: `hardened`, zero escalations, shipping preset `medium`.

## How to use it

```python
from gen_2509_10361 import (
    DIFFICULTY, SHIPPING_DIFFICULTY, make_instance,
    parse_answer, render, verify,
)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
question = render(inst)

# reply is raw solver output containing <answer>...</answer>.
answer = parse_answer(reply)
ok, reason = verify(inst, answer)
```

From the repository root, emit 20 fresh, deduplicated shipping instances:

```bash
bash scripts/emit.sh 2509.10361 20 medium
```

Run the local gates with `python3 results/2509.10361/gen_2509_10361.py`.

## Caveats

- Section 4.3 is a worst-case theorem; it does not prove this planted random
  distribution is average-case hard. The attack panel and oracle run are
  empirical evidence only.
- The `0/200,000` estimate samples uniformly from all perfect partitions that
  already have the correct route count, arity, coverage, distinctness, and one
  client of each type. It does not model a solver that enumerates exact-sum
  triples and performs exponential backtracking, and zero observed hits is not
  a proof of zero probability.
- Small `n` is easy. Holding `|C|`, `k`, `g`, or `r` fixed enters one of the
  paper's tractable regimes; increasing `b_factor` also removes arithmetic
  collisions and makes greedy recovery easier.
- The attacks tried value-rank alignment, deterministic MRV greedy matching,
  and 64 randomized MRV restarts. Full backtracking, SAT/SMT/ILP, and dedicated
  exact-cover solvers were not benchmarked.
- Two of the three oracle failures produced no witness because their response
  budgets were exhausted or the provider ended with an error reason. This is
  weaker evidence than three checked wrong witnesses; rerunning with a larger
  `ORACLE_MAX_TOKENS` would strengthen the empirical claim.
