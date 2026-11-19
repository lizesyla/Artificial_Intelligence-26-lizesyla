# Pjesa 2 — Sudoku Solver me BFS dhe Backtracking

**Lënda:** Inteligjenca Artificiale — Uninformed Search Techniques
**Skedarët:**

| Skedari | Përmbajtja |
|---|---|
| `sudoku_solver.py` | algoritmi, validimi, gjeneratori i niveleve, 19 teste |
| `ui_sudoku.py` | vizualizimi me tkinter |
| `results/` | rezultatet e ekzekutimeve |

**Kërkesa e detyrës:** programi zgjidh Sudoku në tri nivele (Easy, Medium, Hard) me *Breadth First Search (BFS) me Backtracking*.

---

## 1. Modelimi i problemit

Sudoku standard është një grid 9 × 9, i ndarë në 9 kuti 3 × 3. Disa qeliza janë të dhëna (*givens*). Duhet të mbushen qelizat bosh me shifrat 1–9 ashtu që çdo rresht, çdo kolonë dhe çdo kuti të përmbajë secilën shifër saktësisht një herë.

Implementimi është i përgjithësuar për n = R · C ≤ 9, me kuti R × C: 4 × 4 (kuti 2 × 2), 6 × 6 (kuti 2 × 3) dhe 9 × 9 (kuti 3 × 3). Kështu algoritmi mund të testohet fillimisht në instanca të vogla.

**Nivelet (Easy / Medium / Hard).** Niveli përcaktohet nga numri i shifrave të dhëna: më pak shifra do të thotë më shumë qeliza bosh, pra pemë kërkimi më e thellë dhe më e gjerë.

| Niveli | Shifra të dhëna | Qeliza bosh E | Puzzle i integruar |
|---|---|---|---|
| Easy | 38 | 43 | `--level easy` |
| Medium | 30 | 51 | `--level medium` |
| Hard | 24 | 57 | `--level hard` |

Të tre puzzle-t janë krijuar nga gjeneratori i programit me seed të fiksuar (`generate('easy', seed=1)`, `generate('medium', 2)`, `generate('hard', 2)`). Testet verifikojnë që secili ka **saktësisht një zgjidhje**.

**Si punon gjeneratori:**

1. Ndërton një grid të plotë të rastësishëm. Nis nga një model i vlefshëm dhe përdor vetëm lëvizje që e ruajnë vlefshmërinë: përzien rreshtat brenda një bande, përzien bandat, përzien kolonat brenda një shtylle, përzien shtyllat dhe riemërton shifrat.
2. Heq shifra në rend të rastësishëm, por vetëm kur puzzle-i mbetet me zgjidhje unike.

Me `--generate hard --seed 7` krijohen puzzle të reja. Për krahasim, programi përmban edhe puzzle të njohura: "AI Escargot" (23 shifra), një puzzle me 17 shifra, një puzzle pa zgjidhje dhe një puzzle të pavlefshëm.

> **Shënim:** numri i shifrave të dhëna është tregues i thjeshtë i vështirësisë. Faqet e Sudoku (p.sh. sudoku-space.com) zakonisht e matin vështirësinë sipas teknikave logjike që kërkohen. Në seksionin 9 tregohet që, për BFS-in tonë, nivelet tona japin vërtet përpjekje kërkimi gjithnjë e më të madhe.

---

## 2. Reprezentimi i problemit

**State (gjendja):** një grid i pjesshëm, i ruajtur si `bytes` me n² vlera (0 = bosh). Ky reprezentim është i vogël, rreth 120 bajt për 9 × 9, gjë që ka rëndësi sepse BFS ruan shumë gjendje njëkohësisht.

- **Initial state:** puzzle-i i dhënë.
- **Action / successor function** (`expand`):
  1. zgjidh **një** qelizë bosh me një rregull të fiksuar;
  2. për çdo shifër d që **nuk** shfaqet në rreshtin, kolonën apo kutinë e saj, krijo një fëmijë me d në atë qelizë.
- **Rregulli i zgjedhjes së qelizës:**
  - `first` (parazgjedhja): qeliza e parë bosh sipas renditjes së leximit. Ky rregull është plotësisht i painformuar.
  - `mrv` (*minimum remaining values*): qeliza me më pak shifra të lejuara. Ky është një heuristikë e renditjes së variablave dhe përdoret vetëm për krahasim.
- **Goal state:** asnjë qelizë bosh. Meqë asnjë shifër e paligjshme nuk vendoset kurrë, çdo grid i plotë i arritur është zgjidhje.
- **Thellësia e zgjidhjes:** çdo veprim shton saktësisht një shifër, prandaj **të gjitha** zgjidhjet ndodhen në thellësinë E = numri i qelizave bosh.

**Pse pema nuk ka gjendje të përsëritura:** çdo gjendje zgjedh qelizën në mënyrë deterministike, kështu që çdo gjendje ka një rrugë unike nga rrënja. Prandaj nuk nevojitet bashkësi `visited`. Kjo vlen si për `first` ashtu edhe për `mrv`.

---

## 3. Variablat, domenet dhe kufizimet

| Elementi | Përkufizimi |
|---|---|
| Variablat | x_i për çdo qelizë bosh i (E variabla) |
| Domeni | D(x_i) = {1, …, n}; për 9 × 9: {1, …, 9} |
| Domeni efektiv | shifrat që nuk shfaqen te "fqinjët" (*peers*) e qelizës: 20 qeliza në 9 × 9 |
| Kufizimet | **AllDifferent** për 27 njësi (9 rreshta, 9 kolona, 9 kuti); shifrat e dhëna nuk ndryshohen |

Kufizimet mund të shkruhen edhe si çifte: x_i ≠ x_j për çdo i, j në të njëjtën njësi. Për 9 × 9 ka 810 çifte të tilla.

---

## 4. Funksioni objektiv

Përkufizojmë numrin e konflikteve të një gridi G:

```
f(G) = numri i çifteve (i, j) në të njëjtën njësi me G[i] = G[j] ≠ 0
```

Qëllimi është:

```
gjej G të plotë (pa qeliza bosh) me f(G) = 0      ⇔   min f = 0 dhe 0 qeliza bosh
```

Në BFS-in tonë, f mbahet **gjithmonë 0**, sepse çdo fëmijë kontrollohet para se të krijohet. Prandaj qëllimi reduktohet në: *arrij thellësinë E*. Funksioni `validate_solution()` e kontrollon këtë në mënyrë të pavarur: grid i plotë, çdo njësi është permutacion i 1..n, dhe shifrat e dhëna janë ruajtur.

---

## 5. Landscape — madhësia e hapësirës së kërkimit

E = numri i qelizave bosh.

| Madhësia | Formula | Easy (E=43) | Medium (E=51) | Hard (E=57) |
|---|---|---|---|---|
| Plotësime naive | 9^E | 1.1 × 10^41 | 4.6 × 10^48 | 2.5 × 10^54 |
| Kufiri i pemës pa krasitje | Σ_{k=0}^{E} 9^k | 1.2 × 10^41 | 5.2 × 10^48 | 2.8 × 10^54 |
| Prodhimi i domeneve efektive në fillim | Π \|D(x_i)\| | 4.0 × 10^17 | 2.5 × 10^24 | 1.0 × 10^32 |
| Gjendje të gjeneruara realisht nga BFS (`first`) | e matur | 1 856 | 7 558 | 215 177 |
| Zgjidhje | — | 1 | 1 | 1 |

Disa numra referimi:

- Numri i gridëve të plotë të vlefshëm 9 × 9 është 6 670 903 752 021 072 936 960 ≈ 6.67 × 10^21 (Felgenhauer & Jarvis, 2005).
- Për 4 × 4 ka 288 gride të plota. Testi `test_empty4_has_288_solutions` e verifikon këtë me BFS.

**Interpretimi i peizazhit:**

- **Struktura:** peizazhi është një pemë me thellësi fikse E. Të gjitha gjethet e vlefshme (zgjidhjet) janë në fund, dhe në rastin e puzzle-ve me zgjidhje unike ka vetëm **një** gjethe të tillë.
- **Rrugët qorre:** shumica e degëve mbarojnë më herët, sepse një qelizë nuk ka asnjë shifër të ligjshme. Për Hard, 61 997 nga 215 176 gjendjet e zgjeruara ishin rrugë qorre.
- **Profili sipas thellësisë:** numri i gjendjeve për çdo thellësi nuk rritet në mënyrë monotone. Ai rritet kur qelizat e radhës kanë shumë opsione dhe bie kur kufizimet "kafshojnë". Për Hard, maksimumi ishte 40 713 gjendje në thellësinë 34, pastaj ra deri në 1 në thellësitë 49–57. Grafiku "States generated per depth" në UI e tregon këtë profil.

---

## 6. BFS me Backtracking

```
BFS(puzzle):
    frontier = FIFO queue me [puzzle]
    ndërsa frontier nuk është bosh:
        s = frontier.pop_front()                     # gjendja më e cekët
        (qeliza, shifrat) = zgjidh_qelizë(s)         # rregull i fiksuar
        nëse shifrat == ∅:  rrugë qorre → hidhet     # BACKTRACK
        për çdo d në shifrat (rend rritës):          # vetëm shifra të ligjshme
            fëmija = s me d në qelizë
            nëse fëmija është i plotë:  ZGJIDHJE (goal test kur gjenerohet)
            përndryshe:  frontier.push_back(fëmija)
    asnjë zgjidhje → NO_SOLUTION
```

**Ku është "backtracking"-u në BFS?** BFS nuk kthehet mbrapa në kuptimin rekursiv, sepse nuk ka stack thirrjesh. Ai përdor dy elementet thelbësore të metodës së backtracking-ut:

1. **Kontrolli i konsistencës para zgjerimit:** një shifër që shkel rregullat nuk shtohet kurrë, kështu që e gjithë nën-pema e saj prerët menjëherë.
2. **Braktisja e kandidatëve të pjesshëm:** kur një gjendje nuk ka asnjë vazhdim të ligjshëm (rrugë qorre), ajo hidhet dhe kërkimi vazhdon me gjendjen tjetër në radhë.

Ndryshimi i vetëm nga backtracking-u klasik (DFS) është **rendi**: radha FIFO e eksploron pemën nivel pas niveli. Programi lejon edhe `--algorithm dfs` (stack LIFO me të njëjtin funksion `expand`), por vetëm për krahasim.

**Statuset:**

| Status | Kuptimi |
|---|---|
| `SOLVED` | u gjet zgjidhje; me `--all` numërohen të gjitha zgjidhjet dhe vërtetohet uniciteti |
| `NO_SOLUTION` | e gjithë pema u eksplorua dhe nuk ka zgjidhje |
| `LIMIT_REACHED` | u arrit kufiri i nyjeve, i madhësisë së radhës ose i kohës; asgjë nuk vërtetohet |
| `INVALID_PUZZLE` | shifrat e dhëna shkelin rregullat |

---

## 7. Kompleksiteti

Shënojmë b = faktori maksimal i degëzimit (≤ n) dhe d = E.

| | BFS | DFS (krahasim) |
|---|---|---|
| Koha (rasti më i keq) | O(b^d) | O(b^d) |
| Memoria | O(b^d) — e gjithë radha e një niveli | O(b · d) — vetëm rruga aktuale |
| Kompletësia | po (pema është e fundme) | po |
| Gjen zgjidhjen e parë | vetëm pasi ka gjeneruar **të gjitha** nivelet më të cekëta | sapo arrin në fund të një dege të mirë |

Ka edhe një vëzhgim të rëndësishëm, që vërtetohet nga testi `test_bfs_levels_are_in_order`. Në Sudoku të gjitha zgjidhjet janë në të njëjtën thellësi E, prandaj BFS **nuk mund të ndalojë herët**: para se të gjejë zgjidhjen e parë, ai duhet të gjenerojë çdo gjendje të vlefshme në thellësitë 0 … E−1. Për puzzle-t me zgjidhje unike, BFS praktikisht bën kërkim të plotë.

Kur numërohen **të gjitha** zgjidhjet (`--all`), BFS dhe DFS eksplorojnë **saktësisht të njëjtën pemë**: kanë të njëjtin numër gjendjesh dhe të njëjtin profil sipas thellësisë (testi `test_bfs_and_dfs_agree`). Ndryshon vetëm memoria.

Kostoja për një zgjerim është O(n²) me rregullin `mrv` dhe O(peers) = O(n) me `first`.

---

## 8. Metodologjia e testimit

**Testet automatike** (`python sudoku_solver.py --test`, 19 teste):

- **Gjeometria:** çdo qelizë ka 20 / 12 / 7 fqinjë në 9×9 / 6×6 / 4×4. Leximi i gridit refuzon gjatësi të gabuar dhe shifra jashtë intervalit.
- **Validimi:** puzzle me shifra të përsëritura → `INVALID_PUZZLE`; zgjidhje e saktë → pa gabime; zgjidhje me shifra të ndërruara, jo e plotë, ose me shifër të dhënë të ndryshuar → gabim.
- **Nivelet:** Easy / Medium / Hard kanë 38 / 30 / 24 shifra të dhëna, zgjidhje unike dhe zgjidhen nga BFS. Ato përputhen me gjeneratorin (seed 1, 2, 2). Gridet e rastësishme janë të vlefshme për 4×4, 6×6 dhe 9×9, dhe puzzle-t e gjeneruara kanë zgjidhje unike.
- **Kërkimi:**
  - 4×4, 6×6 dhe 9×9 me zgjidhje unike;
  - grid bosh 4×4 → saktësisht 288 zgjidhje të ndryshme;
  - BFS = DFS për pemën e plotë;
  - BFS gjeneron të gjitha nivelet para zgjidhjes;
  - puzzle pa zgjidhje → `NO_SOLUTION`;
  - limiti raportohet si `LIMIT_REACHED`;
  - një grid tashmë i zgjidhur pranohet.

**Vizualizimi** (`python ui_sudoku.py --selftest`) krahason versionin hap-pas-hapi me `solve()` në 90 kombinime: puzzle × BFS/DFS × `first`/`mrv` × zgjidhja e parë/të gjitha, plus limitet. Të gjitha numëruesit dalin identikë.

**Matjet:** ekzekutimet me `--save` shkruajnë `results/*.txt` dhe një rresht në `results/runs.csv`. Opsioni `--memory` mat memorien maksimale me `tracemalloc`; ai e ngadalëson programin, prandaj koha e matur me të nuk krahasohet me kohët e tjera.

---

## 9. Rezultatet

> **Burimi i të dhënave:** të gjitha vlerat janë nga ekzekutime reale më 29.10.2026, me Python 3.10.12 (Linux), të ruajtura në `results/`. Numri i gjendjeve është deterministik dhe duhet të dalë i njëjtë në çdo kompjuter; koha ndryshon.

### 9.1 Tri nivelet me BFS (rregulli `first`, zgjidhja e parë)

| Niveli | Shifra | E | Status | Gjenerohen | Rrugë qorre | Radha max | Koha (s) | Memoria max* |
|---|---|---|---|---|---|---|---|---|
| Easy | 38 | 43 | SOLVED | 1 856 | 524 | 302 | 0.006 | 0.08 MB |
| Medium | 30 | 51 | SOLVED | 7 558 | 2 192 | 793 | 0.029 | 0.18 MB |
| Hard | 24 | 57 | SOLVED | 215 177 | 61 997 | 41 328 | 0.79 | 9.71 MB |

\* Memoria është matur me `--memory`. Për krahasim, DFS kërkoi 0.01 MB në të tri nivelet.

Zgjidhja e Hard, e validuar si VALID:

```
2 3 5 | 7 4 6 | 1 8 9
9 8 1 | 3 2 5 | 6 7 4
4 7 6 | 8 9 1 | 5 3 2
------+-------+------
7 5 4 | 6 8 9 | 2 1 3
8 6 9 | 1 3 2 | 4 5 7
3 1 2 | 5 7 4 | 9 6 8
------+-------+------
5 4 8 | 9 1 3 | 7 2 6
6 2 7 | 4 5 8 | 3 9 1
1 9 3 | 2 6 7 | 8 4 5
```

### 9.2 BFS kundrejt DFS dhe `first` kundrejt `mrv`

Kolona "Gjenerohen" tregon numrin e gjendjeve të gjeneruara; "radha max" është madhësia maksimale e radhës (BFS) ose e stack-ut (DFS).

| Puzzle | BFS first (të gjitha) | DFS first (të gjitha) | BFS first (e para) | DFS first (e para) | BFS mrv (të gjitha) |
|---|---|---|---|---|---|
| Easy | 1 856 / radha max 302 | 1 856 / 13 | 1 856 | 1 488 | 44 / 1 |
| Medium | 7 558 / 793 | 7 558 / 23 | 7 558 | 855 | 77 / 3 |
| Hard | 215 177 / 41 328 | 215 177 / 33 | 215 177 | 42 001 | 87 / 5 |
| AI Escargot | 18 885 / 1 716 | 18 885 / 20 | 18 885 | 8 987 | 2 232 / 93 |
| 17 shifra | LIMIT (5 M) / 1 628 479 | LIMIT (5 M) / 46 | LIMIT | LIMIT | 73 483 / 5 210 |
| Pa zgjidhje | NO_SOLUTION, 1 | NO_SOLUTION, 1 | — | — | NO_SOLUTION, 1 |

**Testi i kufirit të memories** (17 shifra, BFS `first`, pa limit nyjesh, radha ≤ 3 000 000):

| Gjendje të gjeneruara | Thellësia max | Memoria max | Koha | Status |
|---|---|---|---|---|
| 14 440 859 | 31 nga 64 | **557.6 MB** | 118 s | LIMIT_REACHED (radha kaloi 3 milionë) |

**Interpretimi:**

1. **BFS zgjidh të tri nivelet.** Përpjekja rritet shumë me nivelin: Easy → Hard kërkon ~116 herë më shumë gjendje dhe ~137 herë radhë më të madhe. Nivelet tona janë pra vërtet të renditura sipas vështirësisë për kërkimin.
2. **BFS "zgjidhja e parë" = BFS "të gjitha zgjidhjet"** për puzzle-t me zgjidhje unike, siç pritej nga seksioni 7. DFS gjen zgjidhjen më shpejt (p.sh. Hard: 42 001 gjendje kundrejt 215 177), sepse mund të arrijë thellësinë 57 pa gjeneruar gjithë nivelet.
3. **Problemi kryesor i BFS-it është memoria, jo koha.** Në Hard, radha arriti 41 328 gjendje, ndërsa stack-u i DFS-it vetëm 33. Te puzzle-i me 17 shifra, radha e BFS-it kaloi 3 milionë gjendje (558 MB) kur kërkimi kishte arritur vetëm thellësinë 31 nga 64. Kjo është një demonstrim konkret i kompleksitetit O(b^d) në memorie.
4. **Rregulli `mrv`** e zvogëlon pemën shumë (Hard: 87 gjendje në vend të 215 177), por ai është heuristikë që përdor informacion nga kufizimet. Ai nuk është pjesë e kërkimit të painformuar dhe paraqitet vetëm për krahasim.
5. **Puzzle-i pa zgjidhje** u identifikua menjëherë: qeliza e parë bosh nuk kishte asnjë shifër të ligjshme, kështu që rrënja ishte rrugë qorre. Ky është backtracking në formën më të thjeshtë.

---

## 10. Kufizimet dhe përfundimi

**Kufizimet:**

- Niveli i vështirësisë përcaktohet nga numri i shifrave të dhëna, që është tregues i përafërt. Dy puzzle me të njëjtin numër shifrash mund të kenë vështirësi shumë të ndryshme; për shembull, puzzle-i me 17 shifra është shumë më i vështirë për kërkimin se ai me 23 (AI Escargot).
- Kërkimi BFS i painformuar nuk shkallëzohet në puzzle me shumë pak shifra, për shkak të memories.
- Implementimi mbështet vetëm n ≤ 9.
- Kohët janë nga një kompjuter i vetëm.

**Përfundimi:** BFS me Backtracking, i implementuar me radhë FIFO dhe me krasitje të shifrave të paligjshme dhe të rrugëve qorre, i zgjidh saktë dhe në mënyrë të verifikuar nivelet Easy, Medium dhe Hard. Analiza dhe matjet tregojnë që, meqë të gjitha zgjidhjet e Sudoku janë në të njëjtën thellësi, BFS duhet të eksplorojë të gjithë pemën para zgjidhjes. Kostoja e tij kryesore është memoria, që rritet eksponencialisht. Kjo e bën DFS-in (backtracking-un klasik) më të përshtatshëm në praktikë për këtë problem.

---

## Referenca

- B. Felgenhauer, F. Jarvis, *Enumerating possible Sudoku grids* (2005) — 6 670 903 752 021 072 936 960 gride.
- Sudoku Space: http://www.sudoku-space.com/sudoku.php
- S. Russell, P. Norvig, *Artificial Intelligence: A Modern Approach* — kapitujt për kërkimin e painformuar dhe CSP.
