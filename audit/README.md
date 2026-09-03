# Domain-attack audit of shipped results

These are the attacks that G6 did not require until commit `606332e`. Each one is
the standard algorithm for its problem class — the thing a specialist reaches for
first — run against the module's **shipping** preset and graded by the module's own
`verify()`.

```bash
python3 audit/attack_clique.py clique 45     # 0901.3348   spectral + randomized greedy
python3 audit/attack_clique.py disjoint 60   # 1008.2814   same, per clique
python3 audit/attack_1in3.py 2507 30         # 2507.17878  1-in-3 propagation + DPLL
python3 audit/attack_1in3.py 1512 25         # 1512.03127  same
python3 audit/attack_cover.py 55             # 2503.01929  Algorithm X / DLX with MRV
```

Every one of the five families audited was broken. See `AUDIT.md`.
