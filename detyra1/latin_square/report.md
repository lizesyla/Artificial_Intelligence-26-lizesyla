# Pjesa 3 — Latin Square me IDDFS dhe Backtracking

**Lënda:** Inteligjenca Artificiale — Uninformed Search Techniques
**Skedarët:**

| Skedari | Përmbajtja |
|---|---|
| `latin_square.py` | algoritmi IDDFS, validimi, 14 teste |
| `ui_latin.py` | vizualizimi me tkinter |
| `results/` | rezultatet e ekzekutimeve reale |

**Kërkesa e detyrës:** për një hyrje n, të printohet një matricë n × n me numrat 1..n, ku secili numër shfaqet saktësisht një herë në çdo rresht dhe në çdo kolonë. Zgjidhja duhet të gjendet me *Iterative Deepening Depth First Search (IDDFS) dhe Backtracking*.

## Si ekzekutohet

```
cd latin_square
python latin_square.py --test
python latin_square.py 5                    # hyrja e detyrës: n = 5
python latin_square.py 20                   # çdo n: mënyra zgjidhet automatikisht (seksioni 6.1)
python latin_square.py 7 --start-depth 0    # detyro IDDFS të pastër nga L = 0
python latin_square.py 6 --save
python latin_square.py 4 --no-symmetry --all --start-depth 16   # numëron të 576 katrorët e rendit 4
python latin_square.py --grid "1.../.2../..3./...4"             # plotëson një katror të pjesshëm
python latin_square.py 20 --start-depth 361 --random --seed 0   # vetëm iteracioni i fundit
python ui_latin.py
```

**Shembulli i detyrës** (n = 5). Në tekstin e detyrës janë shtypur vetëm 4 rreshta; rreshti i pestë që e plotëson katrorin është `1 2 3 4 5`:

```
5 1 2 3 4
4 5 1 2 3
3 4 5 1 2
2 3 4 5 1
1 2 3 4 5
```

Ky katror kalon validimin tonë (testi `test_assignment_example_is_latin`). Programi ynë printon për n = 5 një katror tjetër, por po aq të vlefshëm (seksioni 9). Për çdo n ≥ 2 ka shumë katrorë latinë, dhe detyra kërkon vetëm njërin prej tyre.

---

## 1. Modelimi i problemit

Problemi është **Constraint Satisfaction Problem (CSP)**: duhet të mbushen n² qeliza me vlera nga 1..n, pa përsëritje në rreshta dhe kolona. Si problem kërkimi, ai shihet si mbushje graduale e qelizave sipas renditjes së leximit (rresht pas rreshti).

Programi pranon edhe një **katror të pjesshëm** (opsioni `--grid`), ku disa qeliza janë të dhëna. Ky është problemi *Latin square completion*, që mund të mos ketë zgjidhje. Kështu testohet edhe rasti `NO_SOLUTION`.

**Thyerja e simetrive (vetëm për grid bosh, aktive si parazgjedhje):** fiksohen rreshti 1 = 1, 2, …, n dhe kolona 1 = 1, 2, …, n. Çdo katror latin mund të shndërrohet në këtë formë ("reduced Latin square") duke riemërtuar numrat dhe duke ndërruar rreshtat. Prandaj ky fiksim nuk e ndryshon përgjigjen e pyetjes "a ekziston katror n × n?", por e zvogëlon hapësirën n!(n−1)! herë. Me `--no-symmetry` ky fiksim çaktivizohet.

---

## 2. Reprezentimi: gjendja, veprimet, qëllimi

- **State:** grid n × n i pjesshëm, plus për çdo rresht dhe kolonë një bit-mask me numrat e përdorur. Kjo e bën kontrollin e kufizimeve O(1).
- **Initial state:** grid bosh, ose me qelizat e fiksuara nga simetria / të dhëna.
- **Action:** vendos një numër v në qelizën e radhës bosh (renditja e leximit), vetëm nëse v nuk është përdorur në rreshtin dhe kolonën e saj.
- **Goal test:** të gjitha qelizat janë mbushur. Meqë asnjë vlerë e paligjshme nuk vendoset, çdo grid i plotë i arritur është katror latin.
- **Thellësia e zgjidhjes:** E = numri i qelizave që mbush kërkimi. Me simetri, E = n² − (2n − 1) = (n − 1)²; pa simetri, E = n². **Të gjitha zgjidhjet janë në thellësinë E.**
- **Path cost:** 1 për çdo veprim. Të gjitha zgjidhjet kanë koston E, prandaj kostoja nuk i dallon zgjidhjet.

---

## 3. Variablat, domenet dhe kufizimet

| Elementi | Përkufizimi |
|---|---|
| Variablat | x_{r,c} për çdo qelizë jo të fiksuar (E variabla) |
| Domeni | D(x_{r,c}) = {1, …, n} |
| Domeni efektiv | {1..n} pa numrat që janë tashmë në rreshtin r dhe kolonën c |
| Kufizimet | AllDifferent(rreshti r) për r = 1..n; AllDifferent(kolona c) për c = 1..n; qelizat e dhëna nuk ndryshohen |

Gjithsej ka 2n kufizime AllDifferent, ose n² (n − 1) kufizime binare x ≠ y.

---

## 4. Funksioni objektiv

Përkufizojmë numrin e konflikteve:

```
f(G) = Σ_rreshta (numri i çifteve me vlerë të njëjtë) + Σ_kolona (numri i çifteve me vlerë të njëjtë)
```

Qëllimi është:

```
gjej G të plotë me f(G) = 0
```

Në kërkimin tonë, f mbetet gjithmonë 0, sepse çdo vlerë kontrollohet para vendosjes. Qëllimi reduktohet në "arrij thellësinë E". Funksioni `validate_latin()` e verifikon zgjidhjen në mënyrë të pavarur: çdo rresht dhe çdo kolonë është permutacion i 1..n, dhe qelizat e dhëna janë ruajtur.

---

## 5. Landscape — hapësira e kërkimit

| n | Plotësime naive n^(n²) | L(n) = numri i katrorëve latinë | R(n) = katrorë të reduktuar | E me simetri |
|---|---|---|---|---|
| 3 | 1.97 × 10^4 | 12 | 1 | 4 |
| 4 | 4.29 × 10^9 | 576 | 4 | 9 |
| 5 | 2.98 × 10^17 | 161 280 | 56 | 16 |
| 6 | 1.03 × 10^28 | 812 851 200 | 9 408 | 25 |
| 7 | 2.56 × 10^41 | 6.15 × 10^13 | 16 942 080 | 36 |
| 8 | 6.28 × 10^57 | 1.09 × 10^20 | 535 281 401 856 | 49 |
| 10 | 10^100 | 9.98 × 10^36 | 7.58 × 10^24 | 81 |

Vërejtje për tabelën:

- Vlerat e L(n) dhe R(n) janë nga OEIS (A002860, A000315), me lidhjen L(n) = n! · (n − 1)! · R(n). Testi `test_formula_L_equals_n_fact_nm1_fact_R` e verifikon këtë lidhje për n = 1..10.
- Programi i **numëron vetë** të gjithë katrorët për n ≤ 4 (576 për n = 4) dhe katrorët e reduktuar për n ≤ 6 (9 408 për n = 6). Këto numërime janë në testet automatike.
- Për ta krahasuar me kufirin e pemës pa krasitje Σ n^k: për n = 7 kufiri është 3.1 × 10^30 nyje.

**Peizazhi:**

- Nuk ka shkallë "më mirë / më keq" gjatë rrugës, sepse çdo gjendje është ose konsistente ose jo. Të gjitha gjethet-zgjidhje janë në të njëjtin nivel E.
- Ka **shumë** zgjidhje (n ≥ 2), kështu që një DFS i thjeshtë zakonisht gjen njërën shpejt.
- Kur rreshtat e fundit mbushen, kufizimet e kolonave "kafshojnë": shumë degë përfundojnë si rrugë qorre afër fundit të çdo rreshti.

---

## 6. IDDFS me Backtracking

```
IDDFS():
    për L = L0, L0 + step, L0 + 2·step, ...:
        cutoff = DLS(gjendja fillestare, thellësia 0, limiti L)
        nëse u gjet zgjidhje:  kthe zgjidhjen
        nëse cutoff == 0:      NO_SOLUTION   # pema u eksplorua plotësisht

DLS(k, L):                                   # DFS me limit thellësie
    nëse k == E:  ZGJIDHJE
    nëse k == L:  cutoff += 1; kthehu         # limiti → mos shko më thellë
    vlerat = numrat e ligjshëm për qelizën k
    nëse vlerat == ∅:  rrugë qorre; kthehu    # BACKTRACK
    për çdo v në vlerat:
        vendos v
        DLS(k + 1, L)
        hiq v                                 # BACKTRACK (zhbëj)
```

- **Backtracking:** asnjë numër i paligjshëm nuk vendoset; kur një qelizë nuk ka asnjë numër të ligjshëm, kërkimi kthehet një hap mbrapa dhe provon vlerën tjetër.
- **Iterative deepening:** DLS përsëritet me limit gjithnjë e më të madh.
- **Kriteri i ndalimit për mungesë zgjidhjeje:** nëse një DLS mbaron pa asnjë cutoff, atëherë ai ka eksploruar të gjithë pemën, dhe mungesa e zgjidhjes është e vërtetuar.

**Parametrat (`Config`):**

| Parametri | Kuptimi |
|---|---|
| `start_depth` L0 | limiti i parë (0 sipas parazgjedhjes) |
| `step` | sa rritet L në çdo iteracion (1 sipas parazgjedhjes) |
| `value_order` | `ascending` (parazgjedhja) ose `random` me `seed` — vetëm rendi i fëmijëve |
| `symmetry_breaking` | fiksimi i rreshtit dhe kolonës 1 |
| `max_nodes`, `time_limit` | kufijtë e kërkimit, që raportohen si `LIMIT_REACHED` |

Me renditje të rastësishme, i njëjti seed përdoret në çdo iteracion, kështu që çdo DLS e sheh pemën në të njëjtin rend.

### 6.1 Zgjedhja automatike e mënyrës (komanda `python latin_square.py n`)

Që programi të printojë katror për **çdo** n të dhënë, komanda pa opsione e zgjedh vetë mënyrën e nisjes, bazuar në matjet e seksionit 9:

| Kushti | Limiti i parë L0 | Rendi i fëmijëve | Arsyeja |
|---|---|---|---|
| E ≤ 25 (n ≤ 6) | 0 — IDDFS i plotë | rritës | iteracionet e para janë të përballueshme (n = 6: 2.8 s) |
| E > 25, n < 15 | E — vetëm iteracioni i fundit | rritës | për n = 7, IDDFS nga L = 0 nuk mbaroi as për 150 s |
| E > 25, n ≥ 15 | E | i rastësishëm, seed 0 | renditja rritëse "thrash"-on për n ≥ 15 |

Vërejtje për këtë zgjedhje:

- Programi e printon mënyrën e zgjedhur dhe arsyen në rreshtin `Mode`.
- Algoritmi mbetet IDDFS me backtracking: kur L0 = E, IDDFS ekzekuton vetëm iteracionin e tij të fundit, i cili është DLS me limit E.
- Opsionet `--start-depth` dhe `--order` e anashkalojnë zgjedhjen automatike. Për shembull, `--start-depth 0` detyron IDDFS të pastër për çdo n.
- Testet `test_auto_mode` dhe `test_cli_prints_square_for_large_n` e verifikojnë këtë sjellje.
- Në matjet tona, kjo mënyrë printoi katror të vlefshëm për n = 7, 14, 20 dhe 30. Për n = 40, renditja e rastësishme me seed 0, 1 dhe 2 nuk gjeti zgjidhje brenda 20 s (seksioni 10).

---

## 7. Kompleksiteti

Shënojmë b = faktori i degëzimit (≤ n) dhe d = E.

- **Koha:** IDDFS gjeneron Σ_{L=0}^{d} N(L) nyje, ku N(L) është madhësia e pemës deri në thellësinë L. Në rastin më të keq kjo është O(b^d).
  - Për një pemë uniforme, përsëritja kushton vetëm rreth b/(b − 1) herë më shumë se iteracioni i fundit.
  - **Në Latin Square kjo nuk vlen**, dhe ky është rezultati kryesor i kësaj pjese: zgjidhjet janë vetëm në thellësinë E. Prandaj **çdo iteracion me L < E duhet të eksplorojë plotësisht** pemën deri në L dhe nuk gjen asgjë. Vetëm iteracioni i fundit (L = E) është DFS i zakonshëm, i cili ndalon te zgjidhja e parë.
  - Pasojat: kostoja e iteracioneve të para rritet si numri i katrorëve latinë të pjesshëm, ndërsa iteracioni i fundit kushton shumë pak.
- **Memoria:** O(d) = O(n²) për rrugën aktuale, plus O(n) maska. Kjo është përparësia e IDDFS-it ndaj BFS-it.
- **Kompletësia:** po, sepse pema është e fundme. IDDFS gjen ose një zgjidhje, ose vërteton `NO_SOLUTION` (një DLS pa cutoff).
- **Optimaliteti:** IDDFS gjen zgjidhjen më të cekët. Këtu të gjitha zgjidhjet kanë të njëjtën thellësi, prandaj kjo veti nuk sjell përfitim.

---

## 8. Metodologjia e testimit

**Testet automatike** (`python latin_square.py --test`, 14 teste):

1. **Validimi:**
   - shembulli i detyrës është katror latin;
   - katrorët e prishur, me më pak rreshta ose me përsëritje, refuzohen;
   - leximi i gridit funksionon;
   - qelizat e dhëna të përsëritura ose jashtë intervalit refuzohen.
2. **IDDFS:**
   - për n = 1..6 gjendet katror i vlefshëm, limitet janë saktësisht 0, 1, …, E, dhe çdo iteracion para të fundit ka cutoff;
   - numërimi i plotë jep L(n) për n ≤ 4 dhe R(n) për n ≤ 6;
   - IDDFS dhe një DLS i vetëm me L = E japin të njëjtën zgjidhje dhe të njëjtin numër nyjesh në iteracionin e fundit;
   - plotësimi i një katrori të pjesshëm funksionon;
   - rasti pa zgjidhje (`12./..3/...`) jep `NO_SOLUTION`;
   - hyrja e pavlefshme jep `INVALID_INPUT`;
   - limiti raportohet si `LIMIT_REACHED`;
   - n = 12 dhe n = 20 (me renditje të rastësishme) zgjidhen me fillim nga L = E;
   - renditja e rastësishme funksionon.

**Vizualizimi:** `python ui_latin.py --selftest` krahason, në 20 konfigurime, çdo iteracion të versionit hap-pas-hapi me `solve()` (nyje, cutoff-e, rrugë qorre, thellësia maksimale, zgjidhja). Të gjitha dalin identike.

---

## 9. Rezultatet

> **Burimi i të dhënave:** ekzekutime reale më 29.10.2026, me Python 3.10.12 (Linux), të ruajtura në `results/` dhe `results/runs.csv`. Numri i nyjeve është deterministik; koha varet nga kompjuteri.

### 9.1 Hyrja e detyrës, n = 5 (IDDFS nga L = 0, me simetri)

Output-i i programit:

```
1 2 3 4 5
2 1 4 5 3
3 4 5 1 2
4 5 2 3 1
5 3 1 2 4
Independent validation: VALID
```

| L | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | **16** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nyje | 0 | 4 | 13 | 27 | 38 | 63 | 124 | 200 | 246 | 322 | 432 | 568 | 624 | 680 | 736 | 792 | **28** |
| cutoff | 1 | 4 | 9 | 14 | 11 | 25 | 61 | 76 | 46 | 76 | 110 | 136 | 56 | 56 | 56 | 56 | 0 |

Gjithsej janë gjeneruar 4 897 nyje, prej të cilave vetëm 28 në iteracionin që gjeti zgjidhjen. Koha ishte 0.01 s.

### 9.2 IDDFS nga L = 0 sipas n

| n | Simetri | E | Status | Iteracione | Nyje gjithsej | Nyje në iteracionin e fundit | Koha (s) |
|---|---|---|---|---|---|---|---|
| 1 | po | 0 | FOUND | 1 | 0 | 0 | 0.000 |
| 2 | po | 1 | FOUND | 2 | 1 | 1 | 0.000 |
| 3 | po | 4 | FOUND | 5 | 14 | 5 | 0.000 |
| 4 | po | 9 | FOUND | 10 | 151 | 9 | 0.001 |
| 5 | po | 16 | FOUND | 17 | 4 897 | 28 | 0.010 |
| 6 | po | 25 | FOUND | 26 | 1 194 051 | 51 | 2.77 |
| 7 | po | 36 | LIMIT (150 s) | 22 (deri L = 21) | 47 415 296 | — | 150 |
| 4 | jo | 16 | FOUND | 17 | 24 844 | 16 | 0.06 |
| 5 | jo | 25 | FOUND | 26 | 13 505 897 | 37 | 31.4 |

Për n = 7, iteracioni me L = 20 vetëm gjeneroi 17.8 milionë nyje (54 s), dhe kërkimi u ndal në L = 21 nga 36. Asnjë katror nuk u gjet brenda 150 s.

### 9.3 Vetëm iteracioni i fundit (L0 = E, d.m.th. një DLS i vetëm = DFS me backtracking)

| n | Rendi i fëmijëve | Status | Nyje | Koha (s) |
|---|---|---|---|---|
| 5 / 6 / 7 / 8 | rritës | FOUND | 28 / 51 / 118 / 49 | < 0.001 |
| 10 / 12 / 13 | rritës | FOUND | 1 445 / 9 467 / 55 145 | 0.004 / 0.04 / 0.16 |
| 14 | rritës | FOUND | 1 518 731 | 4.56 |
| 15, 20 | rritës | LIMIT (20 s) | > 5 milionë | 20 |
| 15 | i rastësishëm, seed 0 / 1 / 2 | FOUND | 315 / 329 / 528 | < 0.003 |
| 20 | i rastësishëm, seed 0 / 1 / 2 | FOUND | 1 510 / 5 494 / 2 224 | < 0.03 |
| 30 | i rastësishëm, seed 0 / 1 / 2 | FOUND | 109 455 / 38 693 / 1 331 169 | 0.57 / 0.20 / 7.20 |

**Interpretimi:**

1. **IDDFS e zgjidh detyrën** për n = 1..6 duke nisur nga L = 0, dhe katrori i printuar validohet në mënyrë të pavarur.
2. **Kostoja e IDDFS-it është pothuajse e gjitha në iteracionet që nuk mund të gjejnë zgjidhje.** Për n = 6, 1 194 000 nga 1 194 051 nyjet (99.996 %) u gjeneruan në iteracionet L < 25. Iteracioni i fundit kërkoi vetëm 51 nyje. Kjo konfirmon analizën e seksionit 7: kur të gjitha zgjidhjet janë në thellësi të njohur E, thellimi gradual nuk sjell asnjë përfitim.
3. **Rritja është shpërthyese:** 151 → 4 897 → 1 194 051 nyje për n = 4, 5, 6. Për n = 7 kërkimi nuk mbaroi as për 150 s. Thyerja e simetrive ndihmon shumë: n = 5 pa simetri kërkoi 13.5 milionë nyje në vend të 4 897.
4. **Me L0 = E, IDDFS-i bëhet DFS me backtracking** dhe zgjidh n shumë më të mëdha. Edhe këtu, rendi rritës i vlerave krijon "thrashing": n = 14 kërkoi 1.5 milionë nyje dhe n = 15 nuk u zgjidh për 20 s. Me rend të rastësishëm të fëmijëve (prapë kërkim i painformuar), n = 20 zgjidhet me disa mijëra nyje dhe n = 30 me 39 mijë deri në 1.3 milionë, në varësi të seed-it.
5. **Për krahasim:** ekziston konstruksion i drejtpërdrejtë pa kërkim, katrori ciklik a_{r,c} = ((r + c) mod n) + 1, siç është edhe shembulli i detyrës. Ai tregon që zgjidhja ekziston për çdo n. Detyra kërkon kërkim, prandaj ky konstruksion përmendet vetëm si referencë dhe nuk përdoret në program.

---

## 10. Kufizimet dhe përfundimi

**Kufizimet:**

- IDDFS nga L = 0 është praktik vetëm për n ≤ 6, sepse iteracionet e para janë shterruese (*exhaustive*). Prandaj komanda pa opsione, për n ≥ 7, e nis IDDFS-in direkt në L = E (seksioni 6.1).
- Për n shumë të mëdha (n = 40 në provat tona) edhe DLS-i i fundit mund ta kalojë limitin e kohës; atëherë programi raporton `LIMIT_REACHED` në vend që të shpikë një rezultat.
- DFS-i kronologjik me rend rritës ngec për n ≥ 15. Rendi i rastësishëm ndihmon, por nuk garanton kohë të vogël (seed 2 për n = 30 kërkoi 1.3 milionë nyje).
- Rezultatet me seed janë vetëm disa mostra, jo një shpërndarje statistikore.
- Kohët janë nga një kompjuter i vetëm.

**Përfundimi:** IDDFS me Backtracking u implementua saktë: me DLS rekursiv, kontroll konsistence para çdo vendosjeje, raportim të cutoff-eve dhe të rrugëve qorre, dhe ndalim të vërtetuar kur nuk ka zgjidhje. Programi printon katror latin të validuar për hyrjen n. Analiza teorike dhe matjet tregojnë që IDDFS ruan memorie të vogël (O(n²)), por për këtë problem iteracionet e para janë thjesht kosto shtesë, sepse thellësia e zgjidhjes dihet paraprakisht. Prandaj, në praktikë, versioni efikas është DLS-i i fundit, pra DFS me backtracking.

---

## Referenca

- OEIS A002860 (numri i katrorëve latinë) dhe A000315 (katrorë latinë të reduktuar).
- S. Russell, P. Norvig, *Artificial Intelligence: A Modern Approach*, seksioni për Iterative Deepening Search.
