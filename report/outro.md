
---

## Pjesa 5 — Krahasimi i pjesëve dhe përfundimi i përgjithshëm

### 5.1 Përmbledhje e rezultateve kryesore

| Pjesa | Algoritmi | Rezultati kryesor (i matur) | Kufizimi kryesor |
|---|---|---|---|
| Social Golfers 32-8-4 | DFS + backtracking, thyerje simetrish | 5 javë gjenden menjëherë me renditje rritëse; 6 javë me renditje të rastësishme (seed 0, 8 293 nyje) | 7+ javë nuk u gjetën brenda limitit; maksimumi i njohur nga literatura (10) **nuk** vërtetohet nga programi |
| Sudoku | BFS + backtracking | Easy / Medium / Hard: 1 856 / 7 558 / 215 177 gjendje; radha max 302 / 793 / 41 328 | memoria: puzzle-i me 17 shifra arriti 3 milionë gjendje në radhë (558 MB) në thellësinë 31 nga 64 |
| Latin Square | IDDFS + backtracking | n ≤ 6 me IDDFS të plotë (n = 6: 1 194 051 nyje, prej të cilave 51 në iteracionin e fundit); për n ≥ 7 nis direkt në L = E dhe printon katror deri në n = 30 | IDDFS nga L = 0 nuk mbaroi për n = 7 brenda 150 s |
| Search Trees | BFS, DFS, DLS, IDDFS, UCS | 8-puzzle optimal deri në 31 lëvizje (BFS); M&C 11 kalime; RWS plan i vlefshëm pas 26 nyjeve (DFS) | DFS jo optimal (64 328 lëvizje për 8-puzzle easy); tree search pa kontroll përsëritjesh nuk mbaron |

### 5.2 Çfarë mësojmë nga krahasimi

1. **Thellësia e zgjidhjes përcakton algoritmin e përshtatshëm.**
   - Te Social Golfers, Sudoku, Latin Square dhe Rotating Workforce, **të gjitha zgjidhjet janë në të njëjtën thellësi të njohur**: numri i qelizave ose ditëve që duhet të mbushen.
   - Në këtë rast, BFS dhe IDDFS nuk sjellin përfitim. BFS duhet të ndërtojë të gjitha nivelet më të cekëta, kështu që memoria rritet eksponencialisht. IDDFS përsërit kërkime të plota që nuk mund të gjejnë zgjidhje.
   - DFS me backtracking zbret drejt e në fund dhe ndalon te zgjidhja e parë. Prandaj është zgjedhja praktike për këto probleme.
2. **Kur thellësia e zgjidhjes nuk dihet dhe duhet rruga më e shkurtër** (8-puzzle, Missionaries and Cannibals), situata përmbyset: BFS, UCS dhe IDDFS janë optimale, ndërsa DFS gjen rrugë shumë të gjata.
3. **Backtracking-u (kontrolli i kufizimeve para çdo hapi) e zvogëlon pemën me shumë rende madhësie.**
   - Sudoku Hard: nga 9^57 ≈ 2.5 × 10^54 plotësime të mundshme mbeten 215 177 gjendje.
   - Rotating Workforce `weekend`: nga 9.7 × 10^9 plane mbeten 287 160 gjendje në nivelin më të gjerë.
4. **Thyerja e simetrive** (Social Golfers, Latin Square) heq degë ekuivalente pa humbur zgjidhje. Shembuj: 13 nyje në vend të 1 722 400 për golfistët 8-2-4; 4 897 nyje në vend të 13 505 897 për Latin Square me n = 5.
5. **Gjendjet e përsëritura duhet të trajtohen** kur hapësira ka cikle:
   - Missionaries and Cannibals: graph search kërkoi 29 nyje, ndërsa tree search 11 878;
   - DFS si tree search nuk mbaron fare;
   - vetëm graph search mbi hapësirë të fundme mund të vërtetojë që **nuk ka zgjidhje**.
6. **Gjetja e një zgjidhjeje nuk vërteton optimalitetin.** Kudo kemi dalluar tri përfundime: "u gjet" (`FOUND`), "u vërtetua që nuk ekziston" (`NO_SOLUTION`, pas eksplorimit të plotë) dhe "nuk dihet" (`LIMIT_REACHED`).

### 5.3 Përfundim i përgjithshëm

Të katër problemet u modeluan si probleme kërkimi, me gjendje, veprime, kufizime dhe funksion objektiv të qartë. U implementuan algoritmet e kërkuara: DFS, BFS dhe IDDFS me backtracking, si dhe pesë algoritme për pemët e kërkimit. Programet u verifikuan me teste automatike dhe me validim të pavarur të çdo zgjidhjeje.

Rezultatet tregojnë si forcën ashtu edhe kufijtë e kërkimit të painformuar:

- problemet e vogla dhe të mesme zgjidhen saktë dhe shpejt;
- për instancat e mëdha (Social Golfers me 7–10 javë, Sudoku me 17 shifra, Latin Square me IDDFS të plotë për n ≥ 7), rritja eksponenciale e hapësirës e bën të nevojshme përdorimin e informacionit shtesë (heuristika, propagim kufizimesh) ose të konstruksioneve matematikore.
