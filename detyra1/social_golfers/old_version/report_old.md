# Social Golfers Problem - Part 1: Uninformed Search Techniques

## University AI Project Report

**Problem:** 32 golfers, 8 groups per week, 4 golfers per group. Find maximum weeks without repeated pairs.

---

## 1. Modelimi i Problemit (Problem Modeling)

### 1.1 Perkufizimi Formal (Formal Definition)

**Social Golfers Problem** eshte një problem kombinatorik i njohur ne kerkimin artificial. Baza e tij:

- **N** = 32 (numri i golfisteve)
- **G** = 8 (numri i grupeve ne jave)
- **S** = 4 (numri i golfisteve ne secilen grube)
- **Kushti**: N = G x S = 8 x 4 = 32 (konfigurim valid)

**Pyetja thelbeseore:** Sa jave (W) mund te rendeshin golfistet ne grupe, pa qe asnjë çift golfisti te luaje ne te njejtin grube dy here?

Ky problem quhet gjithashtu "Kirkman's Schoolgirl Problem" i pergjithësuar ose "Social Golfers Problem".

### 1.2 Reprezentimi i Gjendjes (State Representation)

Një **state** (gjendje) është një schedule (rendisje) se si golfistët janë të grupuar në një javë:

```
State = [week_1, week_2, ..., week_k]
```

Ku secila javë është një liste e grupeve:
```
week_i = [group_1, group_2, ..., group_G]
```

Dhe secila grube është një set (set) golfiste:
```
group_j = {golfer_a, golfer_b, golfer_c, golfer_d}
```

**Shembull:**
- Java 1: [{1,2,3,4}, {5,6,7,8}, ..., {29,30,31,32}]
- Java 2: [{1,5,9,13}, {2,6,10,14}, ..., {20,24,28,32}]

### 1.3 Variablat (Variables)

Ne algoritmin DFS me Backtracking (Depth-First Search):

| Variabli | Pershkrimi | Vlera |
|----------|------------|-------|
| `week_idx` | Indeksi i jave aktuale | 0 deri ne W-1 |
| `group_idx` | Indeksi i grupeve ne java aktuale | 0 deri ne G-1 |
| `current_week_groups` | Grupet qe jane te renditura ne javën aktuale | Lista e grupeve |
| `remaining_in_week` | Golfistët e mbetur per te renditur ne javën aktuale | Set golfiste |
| `schedule` | Jarat e plota qe kane teshamë | Lista e jave |
| `pair_tracker` | Ndërregullojnë çifteve të përsëritura | PairTracker objekt |

### 1.4 Domeni (Domain)

Per secilen grube te ri ne një javë:

- **Domeni**: Te gjitha kombinimet e mundshme S golfiste nga golfistët e mbetur
- **Madhësia e domanit**: C(remaining_golfers, golfers_per_group) kombinime

Per shembull, nëse kemi 28 golfiste te mbetur dhe dua grube me 4:
- C(28, 4) = 20,475 kombinime te mundshme per saktën grube

Per javën e tërë, ne duhet te gjejmë një **partition** (ndarje) e plotë e 32 golfisteve ne 8 grupe te 4-te.

### 1.5 Kufizimet (Constraints)

Ka te tre kufizime kryesore:

#### 1.5.1 Coverage Constraint (Kufizimi I Perputjes)

> Çdo golfiste duhet te jete ne saktësisht një grube ne secilen javë.

Kjo do te thote:
- Bashkimi i te gjitha grupeve ne një javë duhet te jete bashkia e te gjithë golfisteve: U(grupet) = {1,2,...,32}
- Asnjë golfiste s'velon ne me shume se një grube ne te njejtin javë

#### 1.5.2 Pair Uniqueness Constraint (Kufizimi i Unicitetit te Çifteve)

> Nuk ka çift golfiste qe te persëriten ne te njejtin grube dy here.

Per çdo çift (i, j) ku i < j:
- Numri i javave ku i dhe j luajnë toka ne te njejtin grube <= 1

Ne implementimin tone, kjo rregullohet nga `PairTracker` klasa e cila ruajne:
```
pair_history[(i, j)] = set of weeks where i and j played together
```
Dhe kushti është: `len(pair_history[(i, j)]) <= 1` per çdo çift.

#### 1.5.3 Disjoint Groups Constraint (Kufizimi i Grupeve te Ndara)

> Grupet brenda një javë duhet te jene disjunkte dhe njësoj te perfused.

- Pueqimi i dy grupeve të ndryshme ne te njejtin javë duhet te jete i zbrazët: grube_i ∩ grube_j = ∅ per i ≠ j
- Bashkimi i te gjitha grupeve ne një javë duhet te jene te gjithë golfistët

### 1.6 Supozimet (Assumptions)

1. **Te gjithë golfistët janë te disponueshëm çdo javë** - Asnjë golfiste s'vlen
2. **Grupet janë sete, jo secvenca** - Renditja brenda grupeve nuk ka rëndësi ({1,2,3,4} = {4,3,2,1})
3. **Javat janë ne renditje lineare** - Java 1, java 2, java 3, ...
4. **Asnjë golfiste s'vlen ne me shume se një grube ne te njejtin javë**
5. **Golfistët identifikohen me numra** - Nga 1 deri ne N

---

## 2. Funksioni Objektiv (Objective Function)

### 2.1 Formulimi

**Qellimi**: Maximizoni numrin e javeve W te shenuara plotësisht.

```
Maximize: W
```

**Kushtet (Subject to)**:

Per çdo javë w ne [0, W-1]:
1. Ndarja e te gjithë golfisteve N ne G grupe me S golfiste secila
2. Te gjitha çifteve co-ocurrencies ne te gjitha jatat <= 1

### 2.2 Dektetimi i Perkthimit te Kufizimeve (Constraint Violation Detection)

Një schedule (rendisje) është **valid** nëse:
1. Per çdo javë: çdo golfiste shfaqet saktësisht një here
2. Per çdo çift golfiste: ata shfaqen toka ne te njejtin grube ne me shume se një javë

**Implementimi i kontrollit:**

Funksioni `validate_schedule()` kontrollon:
- Nëse secila javë ka te gjithë golfistët (coverage)
- Nëse secila grube ka saktësisht S golfiste
- Nëse grupa ne te njejtin javë janë disjunkte
- Nëse ka çdo çift që persëritur (pair uniqueness)

Funksioni `has_repeated_pairs()` kthye listen e çifteve të përsëritura:
```python
repeats = [(g1, g2, [jaret e persëritura])]
```

---

## 3. Peizina e Kerkimit (Search Landscape)

### 3.1 Madhësia e Hapesirës së Kerkimit (Search Space Size)

Hapesira e kerkimit është **te rëndësishme**. Le të llogarisim:

#### Per NJË Jave:

Numri i menyrave per te ndarë 32 golfiste ne 8 grupe me 4:

```
Number of partitions = N! / (S!)^G / G!
                     = 32! / (4!)^8 / 8!
                     = 32! / (24^8 x 40,320)
                     ~ 1.2 x 10^22
```

Kjo do te thote: **~12 sextillion** (12 x 10^21) konfigurime te mundshme per vetëm një javë!

#### Per W Jave:

Ne menyre naive:
```
Total combinations = (1.2 x 10^22)^W
```

Per W = 5 jave, këtë do te thote:
```
(1.2 x 10^22)^5 ~ 2.5 x 10^110 combinations
```

Kjo është me e madhe se numri i atomave ne universin e vagjueshem!

Me kufizimet e çifteve, hapesira e vlefshme është shume me e vogel, por gjenetikimi i ndonjë secvente vlefshme është ende NP-hard ne pergjitësi.

### 3.2 Kufizimet Praktike

- Hapesira e kerkimit rritet **eksponencialisht** me numrin e javeve
- DFS mund te jetë e nevojshme te zgjidhësh shume schedule të pakompleta para se te gjendet një e plotë
- Per W jave, backtracking mund te jetë e nevojshme te kthjellësish pjesë të medha te hapesirës së kerkimit
- Një **timeout** ose kufi i kerkimit është praktik per demonstrim

### 3.3 Pse Ky Problem Është Kompjuterikisht E Kosteushe

1. **Eksplozion kombinatorik**: O(C(N,S)^G) per javë
2. **Propagimi i kufizimeve është kompleks** - kerkohet çift per çift per javë
3. **Nuk ka drejtim te qarte per te udhëhuar kerkimins** (uninformed search)
4. **Backtracking mund te kthjellësish pjesë të medha te hapesirës së kerkimit**

---

## 4. Kufijtë e Njohur (Known Bounds)

### 4.1 Kufiri Upper Bound

Per 32 golfiste ne grupe me 4:

- Çdo javë krijon: G x C(S,2) = 8 x 6 = 48 çifte te reja
- Total çifte te mundshme: C(32,2) = 496
- **Upper bound**: 496 / 48 ~ 10.33 jave

Kjo do te thote teoretikisht mund te kete **max 10 jave** bazuar vetëm ne numërimin e çifteve.

### 4.2 Realiteti

- **Maksimumi i njohur praktikisht** është mes 10-11 jave
- Problem është i vështirë kombinatorik
- DFS merret me vështirë per W > 5-6 jave per shkak te kostosë kerkimis

### 4.3 Rëndësia e Kufizimit

**Ju lutem vëmendje:** Gjetja e një schedule per N jave **nuk prova se N është optimal**.
- Vetëm toke se N jave është arritë te arrihet
- Maksimumi i vërtetë mund te jetë me i larta (nese DFS-u nuk e gjet)
- Ose ky mund te jetë teshamë optimal

Per te **prova optimalitetin**, duhet te tregoni se:
1. N jave mund te rendeshin (te gjete efektivisht)
2. N+1 jave **nuk mund** te rendeshin (per shkak te kufizimeve)

Ky dyja kërkohet nga kerkimi i plotë i hapesirës së kerkimit (ose një provë matematikore).

---

## 5. DFS me Backtracking (DFS with Backtracking)

### 5.1 Si Funksionon Algoritmi

Algoritmi DFS me Backtracking funksionon ne këto hapa:

1. **Fillimi**: Po jeni ne javën 0, grube 0, pa asnjë golfiste te renditur

2. **Zgjedhja e grupeve**: Per secilen grube, gjeni te gjitha kombinimet e mundshme S golfiste nga te mbeturit

3. **Kontrolla e kufizimeve**: Per çdo kombinim te mundshëm:
   - Kontroll
