# Artificial Intelligence — Uninformed Search Techniques

Projekt universitar për **kërkimin e painformuar** (*uninformed search*), i implementuar në Python 3. Çdo pjesë ka:

- programin me algoritmin, validimin dhe testet automatike;
- një ndërfaqe grafike që e tregon kërkimin hap pas hapi;
- raportin teorik në shqip;
- rezultatet e ekzekutimeve reale.

| Pjesa | Problemi | Algoritmi | Dosja |
|---|---|---|---|
| 1 | Social Golfers Problem — 32 golfistë, 8 grupe me 4, pa çifte të përsëritura | DFS me Backtracking | [`social_golfers/`](social_golfers/) |
| 2 | Sudoku Solver — nivelet Easy, Medium, Hard | BFS me Backtracking | [`sudoku_solver/`](sudoku_solver/) |
| 3 | Latin Square — hyrja n, dalja një katror latin n × n | IDDFS dhe Backtracking | [`latin_square/`](latin_square/) |
| 4 | Search Trees — 8-Puzzle, Missionaries and Cannibals, Rotating Workforce Scheduling | BFS, DFS, DLS, IDDFS, UCS | [`search_trees/`](search_trees/) |

📄 **Raporti i përbashkët:** [`report/report.md`](report/report.md). Ai bashkon katër raportet dhe shton një krahasim të pjesëve.

## Kërkesat

- Python **3.8 ose më i ri**. Nuk nevojitet asnjë paketë e jashtme.
- Ndërfaqet grafike përdorin `tkinter`, i cili vjen me instaluesin e Python-it nga python.org (opsioni "tcl/tk and IDLE").

## Si ekzekutohet

Komandat ekzekutohen nga dosja e secilës pjesë, p.sh. në terminalin e VS Code:

```bash
# Pjesa 1 — Social Golfers
cd social_golfers
python social_golfers.py --test                          # testet automatike
python social_golfers.py --groups 2 --size 4 --find-max  # instanca e vogël 8-2-4
python social_golfers.py --groups 8 --size 4 --weeks 5   # instanca e plotë 32-8-4
python ui_golfers.py                                     # ndërfaqja grafike

# Pjesa 2 — Sudoku
cd ../sudoku_solver
python sudoku_solver.py --test
python sudoku_solver.py --level easy        # ose medium, hard
python sudoku_solver.py --generate hard --seed 7
python ui_sudoku.py

# Pjesa 3 — Latin Square
cd ../latin_square
python latin_square.py --test
python latin_square.py 5                    # hyrja n = 5
python ui_latin.py

# Pjesa 4 — Search Trees
cd ../search_trees
python search_trees.py --test
python search_trees.py missionaries --algorithm bfs --draw 40
python search_trees.py puzzle8 --instance medium --algorithm iddfs
python search_trees.py workforce --instance small --algorithm dfs
python search_trees.py --export-trees      # pemët në trees/*.svg
python ui_search_trees.py
```

Shtoni `--save` në çdo komandë për ta ruajtur output-in në `results/` (një skedar `.txt` dhe një rresht në `results/runs.csv`). Komanda `--help` i tregon të gjitha opsionet.

## Struktura

```
├── README.md
├── report/                     # report.md = raporti i përbashkët; rindërtohet me
│                               # python report/build_report.py (intro.md + 4 raportet + outro.md)
├── social_golfers/             # social_golfers.py, ui_golfers.py, report.md, results/
├── sudoku_solver/              # sudoku_solver.py, ui_sudoku.py, report.md, results/
├── latin_square/               # latin_square.py, ui_latin.py, report.md, results/
└── search_trees/               # search_core.py, eight_puzzle.py, missionaries.py, workforce.py,
                                # search_trees.py, ui_search_trees.py, report.md, trees/, results/
```

## Testet

| Pjesa | Teste me `--test` | Vetëkontroll i ndërfaqes |
|---|---|---|
| Social Golfers | 20 | `python ui_golfers.py --selftest` |
| Sudoku | 19 | `python ui_sudoku.py --selftest` (90 raste) |
| Latin Square | 16 | `python ui_latin.py --selftest` (20 raste) |
| Search Trees | 16 | — (ndërfaqja përdor të njëjtin kod kërkimi) |

Vetëkontrollet verifikojnë që ndërfaqja grafike ndjek saktësisht të njëjtën rrugë kërkimi si programi kryesor.
