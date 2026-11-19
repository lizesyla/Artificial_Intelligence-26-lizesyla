# Uninformed Search Techniques — Raporti i përbashkët

**Lënda:** Inteligjenca Artificiale
**Autore:** lizesyla
**Gjuha e implementimit:** Python 3 (vetëm biblioteka standarde; ndërfaqet grafike përdorin `tkinter`)
**Kodi:** https://github.com/lizesyla/Artificial_Intelligence-26-lizesyla

Ky dokument bashkon raportet e katër pjesëve të projektit. Çdo pjesë ka edhe raportin e vet në dosjen përkatëse (`<pjesa>/report.md`). Ai raport mbetet burimi kryesor; ky skedar krijohet duke i bashkuar ata.

## Përmbajtja

| Pjesa | Problemi | Algoritmi i kërkuar | Dosja |
|---|---|---|---|
| 1 | Social Golfers Problem (32 golfistë, 8 grupe me 4) | DFS me Backtracking | `social_golfers/` |
| 2 | Sudoku Solver (Easy, Medium, Hard) | BFS me Backtracking | `sudoku_solver/` |
| 3 | Latin Square (hyrja n → katror n × n) | IDDFS dhe Backtracking | `latin_square/` |
| 4 | Search Trees: 8-Puzzle, Missionaries and Cannibals, Rotating Workforce Scheduling | BFS, DFS, DLS, IDDFS, UCS | `search_trees/` |
| 5 | Krahasimi i pjesëve dhe përfundimi i përgjithshëm | — | ky dokument |

Për secilin problem, raporti përmban:

- modelimin dhe reprezentimin (gjendja, variablat, domenet, kufizimet);
- funksionin objektiv;
- llogaritjen e landscape-it (madhësia e hapësirës së kërkimit);
- implementimin e algoritmit të kërkuar;
- metodologjinë e testimit;
- rezultatet e matura dhe kompleksitetin.

**Si janë marrë rezultatet:** të gjitha rezultatet janë nga ekzekutime reale të programeve dhe ruhen në dosjet `results/`. Ku një kërkim u ndal nga limiti i kohës ose i nyjeve, kjo shënohet si `LIMIT_REACHED` dhe nuk interpretohet si vërtetim.

