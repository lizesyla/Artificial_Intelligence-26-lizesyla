# Pjesa 1 — Social Golfers Problem me DFS dhe Backtracking

**Lënda:** Inteligjenca Artificiale — Uninformed Search Techniques
**Gjuha e implementimit:** Python 3 (`social_golfers.py`)
**Algoritmi:** Depth-First Search (DFS) me Backtracking

---

## 1. Modelimi i problemit

Kemi **N = 32** golfistë që luajnë një herë në javë, të ndarë në **G = 8** grupe me nga **S = 4** golfistë (N = G · S). Kërkohet një orar (*schedule*) për **W** javë ku asnjë çift golfistësh nuk luan në të njëjtin grup më shumë se një herë.

Problemi njihet në literaturë si instanca **8-4-W** e *Social Golfer Problem* (CSPLib prob010). Ai mund të shikohet në dy mënyra:

- **Problem vendimi (decision problem):** për një W të dhënë, a ekziston një orar i vlefshëm me W javë? Këtë e zgjidh drejtpërdrejt DFS-i.
- **Problem optimizimi:** cili është W maksimal? Kjo kërkon dy gjëra të ndryshme: (a) të gjendet një orar me W javë, dhe (b) të vërtetohet që W + 1 javë janë të pamundura.

Implementimi është i parametrizuar: `--groups G --size S --weeks W`. Për testim fillojmë me instancën e vogël **8 golfistë, 2 grupe me 4** (8-2-4) dhe pastaj kalojmë te instanca e plotë 32-8-4.

**Supozimet:**

1. Të gjithë golfistët luajnë çdo javë (asnjë mungesë).
2. Golfistët shënohen me numrat 1…N; emrat nuk kanë rëndësi.
3. Një grup është bashkësi (*set*): rendi brenda grupit nuk ka rëndësi.
4. Rendi i grupeve brenda javës nuk ka rëndësi.
5. Rendi i javëve nuk ndikon në vlefshmërinë e orarit.

---

## 2. Gjendja fillestare, gjendja qëllim dhe hapësira e gjendjeve

Orari paraqitet si tabelë me **W · N vende bosh (*slots*)**: java 1 ka N vende të ndara në G grupe me S vende, pastaj java 2, etj.

- **State (gjendja):** një orar pjesërisht i plotësuar — vendet 0 … k−1 janë të mbushura, pjesa tjetër bosh. Thellësia e gjendjes është k.
- **Initial state (gjendja fillestare):** k = 0, të gjitha vendet bosh.
- **Action / operator:** vendos një golfist në vendin e radhës k (nëse nuk shkel kufizimet).
- **Goal state (gjendja qëllim):** k = W · N, pra të gjitha vendet janë mbushur dhe të gjitha kufizimet plotësohen.
- **State space:** të gjitha oraret e pjesshme të vlefshme që mund të arrihen nga gjendja fillestare. Thellësia maksimale e pemës është **d = W · N** (për 32-8-4 me W = 10 kjo është 320).

Shembull i një gjendjeje (W = 2, k = 10) për 8-2-4:

```
Java 1: [1 2 3 4] [5 6 7 8]
Java 2: [1 5 _ _] [_ _ _ _]
```

---

## 3. Variablat dhe domenet

Si problem me kufizime (CSP):

| Variabli | Kuptimi | Domeni |
|---|---|---|
| x(w, g, p) | golfisti në javën w, grupin g, pozicionin p | {1, …, N} |

me w ∈ {1..W}, g ∈ {1..G}, p ∈ {1..S}. Gjithsej ka **W · G · S = W · N** variabla.

Domeni efektiv gjatë kërkimit është më i vogël, sepse golfistët e përdorur tashmë në javën w përjashtohen. Në kod, variablat ndihmëse janë:

| Struktura në kod | Kuptimi |
|---|---|
| `schedule[w][g]` | lista e golfistëve në grupin g të javës w |
| `used[w]` | bit mask: cilët golfistë janë vendosur tashmë në javën w |
| `met[x]` | bit mask: me cilët golfistë ka luajtur x deri tani (*pair tracker*) |

---

## 4. Kufizimet (constraints)

- **C1 — Numri i grupeve:** çdo javë ka saktësisht G grupe.
- **C2 — Madhësia e grupit:** çdo grup ka saktësisht S golfistë.
- **C3 — Mbulimi (coverage):** çdo golfist shfaqet saktësisht një herë në çdo javë. Kjo do të thotë që grupet e një jave janë disjunkte dhe bashkimi i tyre është {1, …, N}.
- **C4 — Çiftet unike:** për çdo çift golfistësh {a, b}, numri i javëve ku a dhe b janë në të njëjtin grup është ≤ 1.

Gjatë DFS-it, C1, C2 dhe C3 plotësohen **nga ndërtimi**: çdo javë ka saktësisht N vende të ndara në G grupe me S, dhe një golfist i përdorur në javën w nuk ofrohet më si kandidat në atë javë. C4 kontrollohet në çdo vendosje:

```
kandidati c pranohet  ⇔  met[c] AND mask(grupi aktual) == 0
```

Funksioni `validate_schedule()` i kontrollon të katër kufizimet **në mënyrë të pavarur** nga solver-i, që gabimet e solver-it të mos fshihen. Ai kontrollon edhe numrin e javëve dhe që numrat e golfistëve janë në intervalin 1…N.

---

## 5. Funksioni objektiv

Për problemin e optimizimit:

```
maksimizo W
në kushtet C1–C4 për çdo javë 1..W
```

Për një W të fiksuar, DFS-i zgjidh një problem kënaqshmërie (*satisfiability*) që ka vetëm dy përgjigje: ekziston ose nuk ekziston. Opsioni `--find-max` ekzekuton DFS për W = 1, 2, 3, … dhe ndalon te W i parë që nuk gjendet.

**Kufiri i sipërm (upper bound).** Në çdo javë, një golfist takon S − 1 golfistë të rinj. Ai ka gjithsej N − 1 golfistë të tjerë për të takuar, prandaj:

```
W · (S − 1) ≤ N − 1   ⇒   W ≤ ⌊(N − 1)/(S − 1)⌋
```

Për 32-8-4: W ≤ ⌊31/3⌋ = **10**. (Numërimi i çifteve jep kufi më të dobët: C(32,2)/(8·C(4,2)) = 496/48 ≈ 10.33, pra prapë 10.) Ky kufi është **kusht i nevojshëm, jo i mjaftueshëm**. Për shembull, për 8-2-4 kufiri jep 2, por maksimumi i vërtetë është 1 (shih seksionin 9).

**Çfarë dihet nga literatura:** për 32-8-4 ekziston një orar me 10 javë. Atë e ndërtoi në mënyrë eksplicite Alejandro Aguado në vitin 2004, me konstruksion matematikor dhe jo me kërkim të painformuar. Meqë 10 është edhe kufiri i sipërm, maksimumi është **10**. Ky fakt vjen nga literatura (Wikipedia, "Social golfer problem"; CSPLib prob010) dhe **nuk** është vërtetuar nga programi ynë.

---

## 6. Hapësira e kërkimit dhe search landscape

Duhet të dallojmë tre nivele numërimi. Shënojmë P = numri i ndarjeve javore.

**(a) Numri i grupeve të mundshme** (nënbashkësi me S nga N):

```
C(N, S) = C(32, 4) = 35 960
```

**(b) Numri i ndarjeve javore** (N golfistë në G grupe të parenditura me S):

```
P = N! / ( (S!)^G · G! ) = 32! / ( (4!)^8 · 8! )
  = 59 287 247 761 257 140 625 ≈ 5.93 × 10^19
```

Faktori (S!)^G heq renditjet brenda grupeve, dhe G! heq renditjet e grupeve. Kontroll: për 4 golfistë në 2×2, P = 3; për 8-2-4, P = 35; për 9-3-3, P = 280. Formula verifikohet me numërim të plotë në testin `test_partition_count_by_enumeration`.

**(c) Numri i orareve me W javë** (pa kufizimin C4):

| Supozim | Formula | W = 5 | W = 10 |
|---|---|---|---|
| Javët të renditura, mund të përsëriten | P^W | ≈ 7.3 × 10^98 | ≈ 5.4 × 10^197 |
| Javët të ndryshme, pa renditje | C(P, W) | ≈ 6.1 × 10^96 | ≈ 1.5 × 10^191 |

Kufizimi C4 e zvogëlon shumë numrin e orareve të vlefshme, por nuk ka formulë të njohur të mbyllur për to.

**Pema e DFS-it.** Pa simetri, faktori i degëzimit në vendin k është ≤ numri i golfistëve të lirë të javës (≤ N), dhe thellësia është W · N. Një javë pa kufizime gjeneron deri në N! = 32! ≈ 2.6 × 10^35 rrugë. Ky numër është (S!)^G · G! ≈ 4.4 × 10^15 herë më i madh se P, sepse e njëjta javë ndërtohet në shumë renditje.

**Thyerja e simetrive (symmetry breaking).** Përdorim katër rregulla. Secila heq vetëm degë që janë kopje pasqyrë të degëve të tjera, prandaj asnjë zgjidhje reale nuk humbet:

| Rregulli | Simetria që hiqet | Implementimi |
|---|---|---|
| S1 | rendi brenda grupit | golfistët në grup vendosen në rend rritës |
| S2 | rendi i grupeve në javë | çdo grup fillon me golfistin më të vogël të lirë |
| S3 | emrat e golfistëve (N!) | java 1 fiksohet: {1..4}, {5..8}, …, {29..32} |
| S4 | rendi i javëve 2..W | partneri i golfistit 1 rritet nga java në javë |

Me S1 dhe S2, çdo ndarje javore ndërtohet saktësisht një herë. Prandaj numri i javëve të plota që mund të ndërtohen në çdo nivel është ≤ P, dhe jo ≤ N!.

**Peizazhi (landscape).** Për një problem kënaqshmërie, peizazhi nuk ka "lartësi" të vazhdueshme: një gjendje ose shkel kufizimet ose jo. Karakteristikat kryesore janë:

- **Plato të gjera:** shumë orare të pjesshme të vlefshme duken njësoj "të mira" për një kërkim të painformuar.
- **Rrugë qorre të thella (deep dead ends):** një prefiks i vlefshëm me k javë mund të jetë i pamundur për t'u zgjeruar. Kjo shihet vetëm shumë nivele më poshtë. Shembulli konkret i gjetur nga programi ynë: me renditje rritëse, DFS-i ndërton 5 javë ku golfistët 1–16 kanë takuar vetëm njëri-tjetrin, dhe golfistët 17–32 vetëm njëri-tjetrin. Në javën 6, çdo grup do të duhej të kishte ≤ 1 golfist nga secila gjysmë, pra madhësia e grupit do të ishte ≤ 2 < 4. Pra prefiksi është i pashpëtueshëm, por DFS-i kronologjik e provon këtë duke rikthyer pafund në nivelet e javëve 5 dhe 6 (*thrashing*).
- **Dendësia e zgjidhjeve bie shpejt me W:** për W të vogla ka shumë zgjidhje, ndaj DFS-i gjen njërën pothuajse pa backtracking. Afër W = 10 zgjidhjet janë shumë të rralla.

---

## 7. DFS me Backtracking

DFS-i zgjeron gjithmonë nyjen më të thellë. Implementimi është rekursiv, ku stack-u i rekursionit Python është stack-u LIFO i DFS-it:

```
dfs(k):
    nëse k == W·N:  kthe SUKSES                       # goal test
    (w, g, p) = vendi k
    për çdo kandidat x (në rend fiks, ose të përzier me seed):
        nëse x shkel C4 me grupin aktual:  vazhdo     # pruning
        vendos x                                       # shko më thellë
        nëse dfs(k+1):  kthe SUKSES
        hiq x                                          # BACKTRACK
    kthe DËSHTIM                                       # rrugë qorre
```

**Si funksionon *pair tracker*-i.** `met[x]` është një numër i plotë ku biti y = 1 nëse x dhe y kanë qenë bashkë në grup. Kontrolli i C4 kërkon vetëm një veprim AND. Kur vendosim x, ndezim bitet për çiftet e reja; kur bëjmë backtrack, i fikim. Fikja është e sigurt sepse, në një gjendje të vlefshme, çdo çift është takuar të shumtën një herë.

**Kriteret e ndalimit dhe raportimi.** Kërkimi ka tri përfundime të mundshme:

| Status | Kuptimi |
|---|---|
| `FOUND` | u gjet një orar me W javë; ai validohet më pas në mënyrë të pavarur |
| `NO_SOLUTION` | e gjithë pema u eksplorua: **u vërtetua** që W javë janë të pamundura |
| `LIMIT_REACHED` | u arrit `--max-nodes` ose `--time-limit`: **asgjë nuk vërtetohet** |

**Optimizimet dhe pse nuk e ndryshojnë strategjinë.** Përdorim tri optimizime:

1. Bit masks për kontrollin e çifteve, që e bën kontrollin më të shpejtë pa ndryshuar pemën.
2. Symmetry breaking (S1–S4), që heq vetëm degë ekuivalente.
3. Opsionin `--random --seed`, që ndryshon vetëm rendin e fëmijëve. Rendi i fëmijëve nuk ndryshon strategjinë: është prapë DFS i plotë dhe i rregullt, sepse çdo nyje vizitohet të shumtën një herë dhe pema kalohet e gjitha nëse nuk ka limit.

Nuk përdoret asnjë heuristikë, greedy, restart apo local search. Rregullat e simetrisë mund të çaktivizohen me `--no-symmetry` për krahasim.

---

## 8. Metodologjia e testimit

**Teste automatike** (`python social_golfers.py --test`, 20 teste me `unittest`):

- **Validimi — orare të vlefshme:** 4 golfistë me 3 javë (çdo çift saktësisht një herë); një javë e vlefshme me 32 golfistë.
- **Validimi — orare të pavlefshme:** çift i përsëritur, golfist që mungon ose përsëritet në javë, grup me madhësi të gabuar, numër i gabuar grupesh, numër golfisti jashtë intervalit, numër i gabuar javësh.
- **Matematika:** C(32,4) = 35 960; P për 4, 8, 9 dhe 32 golfistë; kufiri i sipërm; formula e P verifikohet me numërim të plotë për 6 golfistë (P = 15).
- **Solver-i:** çdo orar i gjetur kalon nëpër `validate_schedule()`. Instancat me përgjigje të njohur janë: 8-2-4 (1 javë po, 2 jo), 4-2-2 (3 po, 4 jo), 9-3-3 Kirkman (4 po, 5 jo), si edhe 32-8-4 me 1 javë. Testohet edhe raportimi i `LIMIT_REACHED` dhe që opsionet `--no-symmetry` dhe `--random` japin orare të vlefshme.

**Eksperimentet:** çdo ekzekutim me `--save` shkruan tre lloje skedarësh në `results/`:

- `results/<instanca>_<koha>.txt` — output-i i plotë;
- `results/runs.csv` — një rresht për çdo kërkim (status, nodes, backtracks, sekonda, versioni i Python);
- `results/schedule_..._W<k>_<koha>.json` — orari i gjetur, i cili mund të ri-validohet.

**Metrikat:**

- **nodes** = numri i vendosjeve të pranuara, pra gjendjet e gjeneruara;
- **backtracks** = numri i vendosjeve të hequra;
- **max depth** = vendi më i thellë i arritur;
- **koha** matet me `time.perf_counter()`.

Numri i nyjeve është deterministik për një konfigurim dhe seed të dhënë. Koha varet nga kompjuteri.

### 8.1 Ndërfaqja grafike (`ui_golfers.py`)

Për ta parë kërkimin hap pas hapi, projekti ka edhe një ndërfaqe grafike me `tkinter` (`python ui_golfers.py`). Ajo **nuk** ka algoritëm të veçantë. Klasa `SteppingDFS` trashëgon `SocialGolfersDFS` dhe e shkruan `_dfs()` rekursiv si cikël me stack eksplicit, që ndalon pas çdo ngjarjeje: *assign*, *reject*, *dead end* dhe *backtrack*.

Komanda `python ui_golfers.py --selftest` verifikon që versioni vizual dhe solver-i japin **saktësisht** të njëjtin status, numër nyjesh, numër backtracks dhe të njëjtin orar në 11 raste. Këto përfshijnë 8-2-4 pa simetri (1 722 400 nyje), 32-8-4 me W = 6 dhe seed 0 (8 293 nyje), si edhe një rast me limit.

Çfarë tregon dritarja:

- **Orari (grid):**
  - një rresht për çdo javë dhe një kuti për çdo grup;
  - ngjyra e golfistit është ngjyra e grupit të tij në javën 1, kështu që duket si përzihen golfistët nga java në javë;
  - korniza e verdhë tregon vendin që DFS-i po mbush;
  - numri i kuq është kandidati i refuzuar;
  - korniza portokalli tregon golfistin e hequr nga backtracking.
- **Matrica e çifteve (pair tracker):** qeliza (a, b) ngjyroset me javën kur a dhe b kanë luajtur bashkë. Çifti që shkaktoi refuzimin e fundit shfaqet me të kuqe.
- **Numëruesit:** nodes, backtracks, kandidatë të refuzuar, thellësia, javë të plota, çifte të përdorura dhe kufiri i sipërm.
- **Log-u:** shpjegon me fjalë çdo hap të DFS-it.

Ndërfaqja e bën të dukshme rrugën qorre të seksionit 6. Me renditje rritëse për 32-8-4 dhe W = 6, matrica ka dy blloqe 16 × 16 plotësisht të mbushura, pra golfistët 1–16 dhe 17–32 kanë takuar vetëm njëri-tjetrin. Ndërkohë, DFS-i rikthehet vazhdimisht në javët 5–6.

Koha e matur në UI përjashton vizatimin dhe pauzat, por është prapë më e ngadaltë se solver-i. Për matjet zyrtare përdoret `social_golfers.py`.

---

## 9. Rezultatet dhe interpretimi

> **Burimi i të dhënave:** këto janë rezultate **të ekzekutimit real**, të marra më 24.10.2026 me Python 3.10.12 në Linux. Ato janë të ruajtura në `results/runs.csv`. Kur ekzekuton programin në kompjuterin tënd, numri i nyjeve për rastet `FOUND`/`NO_SOLUTION` duhet të jetë i njëjtë, ndërsa kohët do të ndryshojnë. Për rastet `LIMIT_REACHED`, edhe numri i nyjeve varet nga shpejtësia e kompjuterit.

### 9.1 Instancat e vogla dhe efekti i simetrisë

| Instanca | W | Simetri | Status | Nodes | Koha (s) |
|---|---|---|---|---|---|
| 8-2-4 | 1 | po | FOUND | 8 | 0.0000 |
| 8-2-4 | 2 | po | NO_SOLUTION | 13 | 0.0001 |
| 8-2-4 | 2 | jo | NO_SOLUTION | 1 722 400 | 7.44 |
| 9-3-3 | 4 | po | FOUND | 37 | 0.0002 |
| 9-3-3 | 5 | po | NO_SOLUTION | 958 | 0.0039 |
| 9-3-3 | 5 | jo | LIMIT_REACHED (30 s) | 7 663 616 | 30.0 |
| 16-4-4 | 5 | po | FOUND | 80 | 0.0004 |

**Interpretimi:**

- **8-2-4: maksimumi = 1 javë, i vërtetuar.** Për 2 javë, DFS-i eksploroi gjithë pemën dhe nuk gjeti zgjidhje. Arsyeja matematikore: pas javës 1, çdo grup i ri me 4 do të përmbante të paktën 2 golfistë nga i njëjti grup i vjetër (parimi i Dirichlet-it). Shembulli tregon që kufiri ⌊7/3⌋ = 2 nuk arrihet gjithmonë.
- **9-3-3: maksimumi = 4.** Kjo është e vërtetuar sepse 4 = kufiri i sipërm.
- **Efekti i simetrisë:** për të vërtetuar të njëjtin fakt, DFS-i pa simetri kërkoi 1 722 400 nyje (8-2-4) në vend të 13, dhe për 9-3-3 me 5 javë nuk mbaroi as për 30 s.
- **16-4-4:** u gjetën 5 javë, që është kufiri ⌊15/3⌋.

### 9.2 Instanca e plotë 32-8-4

Komanda e përdorur:

```
python social_golfers.py --groups 8 --size 4 --find-max --time-limit 60 --max-nodes 0
```

Ky është kërkim me renditje rritëse:

| W | Status | Nodes | Backtracks | Koha (s) |
|---|---|---|---|---|
| 1 | FOUND | 32 | 0 | 0.0002 |
| 2 | FOUND | 64 | 0 | 0.0004 |
| 3 | FOUND | 96 | 0 | 0.0005 |
| 4 | FOUND | 128 | 0 | 0.0007 |
| 5 | FOUND | 160 | 0 | 0.0009 |
| 6 | LIMIT_REACHED (60 s) | 9 973 760 | 9 973 609 | 60.0 |

Kërkimi me renditje të përzier të fëmijëve (`--random --seed s`, prapë DFS):

| W | Seed | Limit | Status | Nodes | Thellësia max (javë të plota) |
|---|---|---|---|---|---|
| 6 | 0 | 25 s | **FOUND** | 8 293 | 6 |
| 6 | 1 | 25 s | LIMIT_REACHED | 4 273 152 | 4 |
| 6 | 2 | 25 s | LIMIT_REACHED | 4 407 296 | 4 |
| 6 | 3 | 25 s | LIMIT_REACHED | 4 219 904 | 5 |
| 6 | 4 | 25 s | LIMIT_REACHED | 4 155 392 | 5 |
| 7 | 0 | 60 s | LIMIT_REACHED | 9 306 112 | 6 |
| 7 | 1 | 60 s | LIMIT_REACHED | 10 418 176 | 4 |

Orari me 6 javë (seed 0), i validuar nga `validate_schedule()` pa asnjë gabim:

```
Java 1: [ 1  2  3  4] [ 5  6  7  8] [ 9 10 11 12] [13 14 15 16] [17 18 19 20] [21 22 23 24] [25 26 27 28] [29 30 31 32]
Java 2: [ 1  5 10 18] [ 2 20 28 29] [ 3 16 25 32] [ 4 24 26 30] [ 6 14 17 31] [ 7 12 13 21] [ 8 11 19 22] [ 9 15 23 27]
Java 3: [ 1 17 26 29] [ 2 10 15 31] [ 3 22 27 30] [ 4  9 16 18] [ 5 14 19 21] [ 6 12 20 23] [ 7 11 28 32] [ 8 13 24 25]
Java 4: [ 1 19 28 30] [ 2 21 26 32] [ 3 18 24 29] [ 4 10 22 25] [ 5 13 23 31] [ 6 11 16 27] [ 7  9 14 20] [ 8 12 15 17]
Java 5: [ 1 20 24 27] [ 2 14 18 23] [ 3 12 19 26] [ 4  5 11 29] [ 6 13 22 32] [ 7 15 25 30] [ 8  9 28 31] [10 16 17 21]
Java 6: [ 1 21 25 31] [ 2  7 19 27] [ 3 10 23 28] [ 4  8 14 32] [ 5  9 17 24] [ 6 15 18 26] [11 13 20 30] [12 16 22 29]
```

**Interpretimi:**

1. DFS-i ynë **gjeti orare të vlefshme me 1–6 javë** për 32 golfistë. Kjo tregon vetëm që 6 javë janë **të mundshme**. Nuk tregon që 6 është maksimumi; në fakt dihet nga literatura që maksimumi është 10.
2. Për W = 6 me renditje rritëse dhe për W = 7, kërkimi u ndal nga limiti. Status `LIMIT_REACHED` **nuk** do të thotë që zgjidhja nuk ekziston.
3. Kërkimi me renditje rritëse ngec për shkak të rrugës qorre të përshkruar në seksionin 6: prefiksi me 5 javë është i pashpëtueshëm, por DFS-i kronologjik e eksploron atë nyje pas nyje.
4. Rendi i fëmijëve ndikon shumë në kohën e DFS-it: seed 0 gjeti 6 javë për 0.06 s, ndërsa seed-et 1–4 nuk i gjetën për 25 s. Kjo është tipike për kërkimin e painformuar.
5. Programi **nuk** vërtetoi maksimumin për 32-8-4. Përfundimi korrekt është: *maksimumi ≥ 6 (nga programi), ≤ 10 (nga kufiri), dhe = 10 sipas literaturës*.

---

## 10. Kompleksiteti kohor dhe hapësinor

Shënojmë **b** = faktori i degëzimit (≤ N) dhe **d** = W · N = thellësia e pemës.

- **Koha, rasti më i keq:** O(b^d) nyje, pra O(N^{W·N}). Me simetri, numri i javëve të plota të ndërtuara në çdo nivel është ≤ P, kështu që kufiri bëhet afërsisht O(P^{W−1}), pasi java 1 është e fiksuar. Kjo mbetet eksponenciale në W.
- **Kosto për nyje:** O(N) për listën e kandidatëve dhe O(S) për kontrollin e çifteve me bit masks.
- **Hapësira:** DFS ruan vetëm rrugën aktuale:
  - stack-u i rekursionit ka thellësi O(W · N);
  - orari ka W · N numra;
  - `met[]` ka N maska me N bit secila, pra O(N²) bit.

  Gjithsej O(W · N + N²). Për 32-8-4 me W = 10, kjo do të thotë rreth 320 nivele rekursioni, që është shumë pak memorie. Kjo është përparësia kryesore e DFS-it ndaj BFS-it, i cili do të duhej të ruante një nivel të tërë të pemës.
- **Kompletësia:** DFS-i është i plotë për këtë problem, sepse pema është e fundme (thellësia e kufizuar) dhe asnjë zgjidhje nuk hiqet nga simetria. Pra, pa limit, ai ose gjen zgjidhje ose vërteton `NO_SOLUTION`. Në praktikë, për 32-8-4 me W ≥ 6, limiti i kohës arrihet shumë më herët.
- **Optimaliteti:** "optimal" këtu nuk ka kuptim për një W të fiksuar, sepse çdo zgjidhje është e barabartë me të tjerat. Për W maksimal, optimaliteti vërtetohet vetëm me `NO_SOLUTION` për W + 1 ose me arritjen e kufirit të sipërm.

---

## 11. Kufizimet dhe përfundimi

**Kufizimet:**

- DFS-i kronologjik bën backtrack vetëm një nivel në një kohë. Ai nuk e "kupton" që shkaku i dështimit ndodhet shumë javë më lart, prandaj ka *thrashing* në rrugë qorre të thella.
- Programi gjen ≤ 6 javë për 32-8-4 brenda kufijve të kohës që provuam. 10 javët e njohura janë gjetur me konstruksione matematikore ose me metoda më të avancuara (constraint propagation, local search), të cilat dalin jashtë kërkimit të painformuar.
- Rezultatet me `--random` varen nga seed-i. Një ekzekutim i vetëm nuk është përfaqësues për të gjithë seed-et.
- Kohët janë matur në një kompjuter të vetëm. Ato duhet të rimaten në mjedisin e studentit.
- Symmetry breaking (S3, S4) është i saktë për problemin e plotë, por e bën orarin e gjetur të duket "i normalizuar": java 1 është gjithmonë {1..4}, {5..8}, ….

**Përfundimi:**

Implementuam DFS me Backtracking për Social Golfers Problem, me kontroll të kufizimeve në çdo hap, *pair tracking* me bit masks, thyerje të simetrive që nuk humbet zgjidhje, kufij kërkimi dhe raportim të ndershëm të tri statuseve. Testet automatike verifikojnë si validimin ashtu edhe solver-in në instanca me përgjigje të njohur. Për instancat e vogla, DFS-i **vërteton** maksimumin (8-2-4 → 1, 9-3-3 → 4). Për instancën e plotë 32-8-4, DFS-i gjen orare të vlefshme deri në **6 javë**, por **nuk** arrin të vërtetojë maksimumin. Kjo tregon qartë kufizimin kryesor të kërkimit të painformuar: hapësira rritet si P^W me P ≈ 5.93 × 10^19, dhe pa informacion shtesë ose propagim kufizimesh, DFS-i nuk mund ta mbulojë atë në kohë praktike.

---

## Referenca

- Wikipedia, "Social golfer problem": https://en.wikipedia.org/wiki/Social_golfer_problem
- CSPLib, Problem 010 — Social Golfers Problem: https://www.csplib.org/Problems/prob010/
- M. Triska, "The Social Golfer Problem": https://www.metalevel.at/sgp/
