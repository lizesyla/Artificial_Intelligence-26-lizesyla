#!/usr/bin/env python3
"""
Latin Square - Iterative Deepening DFS (IDDFS) with Backtracking
================================================================

Course : Artificial Intelligence - Uninformed Search Techniques (Part 3)

Task: given n, print an n x n matrix with the numbers 1..n so that every
number appears exactly once in every row and every column.
(Optional extension: some cells can be given in advance - "Latin square
completion" - then the search must respect them.)

How the search works (short version)
-----------------------------------
STATE  : partially filled grid, cells filled in reading order.
ACTION : write a number in the next empty cell that is not yet used in its
         row or its column (BACKTRACKING check: illegal numbers are never placed;
         a cell with no legal number is a dead end -> go back).
DLS    : depth-limited DFS - never goes deeper than L filled cells.
IDDFS  : run DLS with L = 0, 1, 2, ... until a solution is found.
         If some DLS stopped because of the limit ("cutoff"), a deeper
         solution may exist -> L + 1.  If a DLS finishes WITHOUT any cutoff
         and without a solution, the whole tree was explored -> no solution.

Usage (run inside the latin_square/ folder)
-------------------------------------------
    python latin_square.py 5                      # the assignment: input n = 5
    python latin_square.py 20                     # any n: the mode is chosen automatically
    python latin_square.py 6 --save
    python latin_square.py 4 --no-symmetry --all  # count all 576 squares of order 4
    python latin_square.py 7 --start-depth 0 --time-limit 60   # force pure IDDFS
    python latin_square.py 20 --start-depth 361 --random --seed 0   # only the last DLS
    python latin_square.py --grid "1.../.2../..3./...4"   # complete a partial square
    python latin_square.py --experiment --save    # the tables used in report.md
    python latin_square.py --test
"""

from __future__ import annotations

import argparse
import csv
import io
import math
import os
import random
import sys
import time
import unittest
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

FOUND = "FOUND"
NO_SOLUTION = "NO_SOLUTION"
LIMIT_REACHED = "LIMIT_REACHED"
INVALID = "INVALID_INPUT"

# Number of Latin squares L(n) and reduced Latin squares R(n), n = 1..10
# (OEIS A002860 and A000315).  L(n) = n! * (n-1)! * R(n).
LATIN_COUNT = [1, 2, 12, 576, 161280, 812851200, 61479419904000,
               108776032459082956800, 5524751496156892842531225600,
               9982437658213039871725064756920320000]
REDUCED_COUNT = [1, 1, 1, 4, 56, 9408, 16942080, 535281401856, 377597570964258816,
                 7580721483160132811489280]


# =============================================================================
# 1. INPUT, OUTPUT, VALIDATION
# =============================================================================

def parse_grid(text: str) -> List[List[int]]:
    """Rows separated by '/' or new lines; '.' or 0 = empty; numbers separated by
    spaces when n > 9 (e.g. '10 . 3 / ...')."""
    rows = [r.strip() for r in text.replace("\n", "/").split("/") if r.strip()]
    n = len(rows)
    grid = []
    for r in rows:
        tokens = r.split() if " " in r else list(r)
        vals = [0 if t in (".", "0") else int(t) for t in tokens]
        if len(vals) != n:
            raise ValueError(f"every row needs {n} cells, got {len(vals)} in '{r}'")
        grid.append(vals)
    return grid


def format_grid(grid: List[List[int]]) -> str:
    w = len(str(len(grid)))
    return "\n".join(" ".join(f"{v:>{w}}" if v else "." * w for v in row) for row in grid)


def validate_partial(grid: List[List[int]]) -> List[str]:
    """Given numbers must be in 1..n and must not repeat in a row or column."""
    n = len(grid)
    errs = []
    for r, row in enumerate(grid):
        if len(row) != n:
            errs.append(f"row {r + 1} has {len(row)} cells, expected {n}")
    if errs:
        return errs
    for r in range(n):
        for c in range(n):
            if not 0 <= grid[r][c] <= n:
                errs.append(f"cell ({r + 1},{c + 1}): {grid[r][c]} not in 1..{n}")
    for k in range(n):
        row = [v for v in grid[k] if v]
        col = [grid[r][k] for r in range(n) if grid[r][k]]
        for name, vals in (("row", row), ("column", col)):
            dup = sorted({v for v in vals if vals.count(v) > 1})
            if dup:
                errs.append(f"{name} {k + 1}: repeated {dup}")
    return errs


def validate_latin(square: List[List[int]], n: Optional[int] = None,
                   givens: Optional[List[List[int]]] = None) -> List[str]:
    """Complete check of a Latin square (independent of the search)."""
    errs = []
    if n is None:
        n = len(square)
    if len(square) != n or any(len(row) != n for row in square):
        return [f"not an {n} x {n} grid"]
    target = set(range(1, n + 1))
    for k in range(n):
        if set(square[k]) != target:
            errs.append(f"row {k + 1} is not a permutation of 1..{n}")
        if {square[r][k] for r in range(n)} != target:
            errs.append(f"column {k + 1} is not a permutation of 1..{n}")
    if givens:
        for r in range(n):
            for c in range(n):
                if givens[r][c] and givens[r][c] != square[r][c]:
                    errs.append(f"given at ({r + 1},{c + 1}) changed")
    return errs


# =============================================================================
# 2. SEARCH SPACE NUMBERS
# =============================================================================

def landscape(n: int, empty: int) -> dict:
    d = {"naive": n ** (n * n), "tree_bound": sum(n ** k for k in range(empty + 1)),
         "permutation_rows": math.factorial(n) ** n}
    if n <= 10:
        d["latin"] = LATIN_COUNT[n - 1]
        d["reduced"] = REDUCED_COUNT[n - 1]
    return d


def sci(x: int) -> str:
    s = str(x)
    return s if len(s) <= 7 else f"{s[0]}.{s[1:3]}e{len(s) - 1}"


# =============================================================================
# 3. IDDFS WITH BACKTRACKING
# =============================================================================

@dataclass
class Config:
    n: int = 5
    givens: Optional[List[List[int]]] = None
    symmetry_breaking: bool = True   # only for an EMPTY grid: fix row 1 and column 1
    start_depth: int = 0             # first depth limit L
    step: int = 1                    # L increases by this much
    find_all: bool = False           # count all solutions in the last iteration
    value_order: str = "ascending"   # "ascending" or "random" (order of the children)
    seed: int = 0                    # for value_order == "random"
    max_solutions: int = 1_000_000
    max_nodes: Optional[int] = 20_000_000
    time_limit: Optional[float] = 60.0


@dataclass
class Iteration:
    limit: int
    nodes: int = 0          # states generated in this iteration
    cutoffs: int = 0        # times the depth limit stopped the search
    dead_ends: int = 0      # states whose next cell had no legal number
    max_depth: int = 0
    seconds: float = 0.0


@dataclass
class Result:
    status: str
    solution: Optional[List[List[int]]] = None
    solutions: int = 0
    iterations: List[Iteration] = field(default_factory=list)
    nodes: int = 0          # total over all iterations (root counted once per iteration)
    elapsed: float = 0.0
    empty: int = 0          # depth of every solution
    fixed_by_symmetry: int = 0
    message: str = ""


class _Stop(Exception):
    pass


class LatinIDDFS:
    """Cells are filled in reading order. Depth k = k numbers placed by the search."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        n = self.n = cfg.n
        if n < 1:
            raise ValueError("n must be >= 1")
        g = cfg.givens if cfg.givens is not None else [[0] * n for _ in range(n)]
        if len(g) != n:
            raise ValueError("grid size does not match n")
        self.givens = [row[:] for row in g]
        self.empty_input = all(v == 0 for row in g for v in row)
        self.grid = [row[:] for row in g]
        self.fixed = 0
        if cfg.symmetry_breaking and self.empty_input:
            # Any Latin square can be turned into one with row 1 = column 1 = 1..n
            # by renaming numbers and permuting rows, so this loses no answer
            # to "does an n x n Latin square exist?".
            for c in range(n):
                self.grid[0][c] = c + 1
            for r in range(n):
                self.grid[r][0] = r + 1
            self.fixed = 2 * n - 1
        self.row_used = [0] * n
        self.col_used = [0] * n
        for r in range(n):
            for c in range(n):
                v = self.grid[r][c]
                if v:
                    self.row_used[r] |= 1 << v
                    self.col_used[c] |= 1 << v
        self.cells = [(r, c) for r in range(n) for c in range(n) if self.grid[r][c] == 0]
        self.E = len(self.cells)

    # ---- one depth-limited search -----------------------------------------
    def legal(self, k: int) -> List[int]:
        r, c = self.cells[k]
        used = self.row_used[r] | self.col_used[c]
        vals = [v for v in range(1, self.n + 1) if not (used >> v) & 1]
        if self.cfg.value_order == "random":
            self.rng.shuffle(vals)
        return vals

    def place(self, k: int, v: int) -> None:
        r, c = self.cells[k]
        self.grid[r][c] = v
        self.row_used[r] |= 1 << v
        self.col_used[c] |= 1 << v

    def remove(self, k: int, v: int) -> None:
        r, c = self.cells[k]
        self.grid[r][c] = 0
        self.row_used[r] &= ~(1 << v)
        self.col_used[c] &= ~(1 << v)

    def _dls(self, k: int, limit: int, it: Iteration) -> bool:
        """Returns True when the search must stop (solution found and not find_all)."""
        if k > it.max_depth:
            it.max_depth = k
        if k == self.E:                         # goal: every cell filled
            self.res.solutions += 1
            if self.res.solution is None:
                self.res.solution = [row[:] for row in self.grid]
            return not self.cfg.find_all or self.res.solutions >= self.cfg.max_solutions
        if k == limit:                          # depth limit reached -> cutoff
            it.cutoffs += 1
            return False
        values = self.legal(k)
        if not values:
            it.dead_ends += 1                   # backtrack
            return False
        for v in values:
            it.nodes += 1
            self.total += 1
            self._limits()
            self.place(k, v)
            stop = self._dls(k + 1, limit, it)
            self.remove(k, v)                   # BACKTRACK (undo)
            if stop:
                return True
        return False

    def _limits(self):
        c = self.cfg
        if c.max_nodes is not None and self.total >= c.max_nodes:
            raise _Stop(f"node limit {c.max_nodes:,}")
        if c.time_limit is not None and (self.total & 4095) == 0 \
                and time.perf_counter() - self.start > c.time_limit:
            raise _Stop(f"time limit {c.time_limit}s")

    # ---- iterative deepening -----------------------------------------------
    def solve(self) -> Result:
        sys.setrecursionlimit(max(10_000, self.E + 1_000))
        errs = validate_partial(self.givens)
        if errs:
            return Result(INVALID, message="; ".join(errs))
        self.res = res = Result(NO_SOLUTION, empty=self.E, fixed_by_symmetry=self.fixed)
        self.total = 0
        self.start = time.perf_counter()
        limit = max(0, self.cfg.start_depth)
        try:
            while True:
                it = Iteration(limit)
                res.iterations.append(it)
                # same seed in every iteration -> every DLS sees the same tree order
                self.rng = random.Random(self.cfg.seed)
                t0 = time.perf_counter()
                self._dls(0, limit, it)
                it.seconds = time.perf_counter() - t0
                if res.solutions:
                    res.status = FOUND
                    break
                if it.cutoffs == 0:            # whole tree explored, nothing found
                    res.status = NO_SOLUTION
                    break
                limit += max(1, self.cfg.step)
        except _Stop as s:
            it.seconds = time.perf_counter() - t0
            res.message = str(s)
            res.status = FOUND if res.solutions else LIMIT_REACHED
        res.nodes = self.total
        res.elapsed = time.perf_counter() - self.start
        return res


def solve(cfg: Config) -> Result:
    return LatinIDDFS(cfg).solve()


# Automatic choice used by the command line when --start-depth / --order are
# not given. Pure IDDFS from L = 0 is only practical while the goal depth is
# small, because every iteration with L < E explores its whole tree without
# finding anything (see report.md, sections 7 and 9).
AUTO_MAX_EMPTY_FOR_IDDFS = 25      # = n 6 with symmetry breaking (finished in ~3 s)
AUTO_RANDOM_FROM_N = 15            # ascending order thrashes from n = 15 on


def auto_mode(n: int, givens=None, symmetry_breaking: bool = True):
    """Returns (start_depth, value_order, explanation)."""
    E = LatinIDDFS(Config(n=n, givens=givens, symmetry_breaking=symmetry_breaking)).E
    if E <= AUTO_MAX_EMPTY_FOR_IDDFS:
        return 0, "ascending", (f"pure IDDFS: depth limits L = 0, 1, ..., {E} "
                                f"(goal depth E = {E})")
    order = "random" if n >= AUTO_RANDOM_FROM_N else "ascending"
    return E, order, (
        f"goal depth E = {E} is too deep for IDDFS from L = 0 (every iteration with L < E "
        f"must explore its whole tree; n = 7 did not finish in 150 s). IDDFS is started "
        f"directly at L = E, so only the last depth-limited DFS with backtracking runs"
        + (", with random order of the children (seed 0), because ascending order "
           "thrashes for n >= 15" if order == "random" else "")
        + ". Use --start-depth 0 to force pure IDDFS.")


# =============================================================================
# 4. OUTPUT AND SAVING
# =============================================================================

def explain(res: Result, cfg: Config) -> str:
    if res.status == INVALID:
        return "Invalid input: " + res.message
    if res.status == FOUND:
        s = f"Found a Latin square at depth {res.empty} (iteration with limit {res.iterations[-1].limit})."
        if cfg.find_all:
            s += f" Solutions counted in the last iteration: {res.solutions}" + (
                f" (stopped early: {res.message})" if res.message else " (exact count)")
        return s
    if res.status == NO_SOLUTION:
        return ("A depth-limited search finished without any cutoff and without a solution: "
                "the complete tree was explored, NO solution exists.")
    return f"Stopped by a limit ({res.message}). Nothing is proven."


def print_run(cfg: Config, res: Result) -> None:
    n = cfg.n
    print(f"Input n           : {n}" + ("" if cfg.givens is None else " (with given cells)"))
    if cfg.givens is not None:
        print(format_grid(cfg.givens))
    if res.status == INVALID:
        print("Status            : " + res.status + "\n" + explain(res, cfg))
        return
    lands = landscape(n, res.empty)
    print(f"Cells             : {n * n}, fixed by symmetry breaking: {res.fixed_by_symmetry}, "
          f"filled by search (goal depth) E = {res.empty}")
    print(f"Naive n^(n^2)     : {sci(lands['naive'])}   tree bound sum n^k: {sci(lands['tree_bound'])}")
    if "latin" in lands:
        print(f"Latin squares L(n): {lands['latin']:,}   reduced R(n): {lands['reduced']:,}")
    print(f"IDDFS             : start depth {cfg.start_depth}, step {cfg.step}, "
          f"value order {cfg.value_order}" + (f" (seed {cfg.seed})" if cfg.value_order == "random" else "") + ", "
          f"find all: {cfg.find_all}, limits: nodes={cfg.max_nodes}, time={cfg.time_limit}s")
    print(f"\n{'limit L':>8} {'nodes':>14} {'cutoffs':>12} {'dead ends':>12} {'max depth':>10} {'time (s)':>10}")
    for it in res.iterations:
        print(f"{it.limit:>8} {it.nodes:>14,} {it.cutoffs:>12,} {it.dead_ends:>12,} "
              f"{it.max_depth:>10} {it.seconds:>10.4f}")
    last = res.iterations[-1].nodes if res.iterations else 0
    print(f"\nStatus            : {res.status}")
    print(f"Explanation       : {explain(res, cfg)}")
    print(f"Nodes, all iter.  : {res.nodes:,}   (last iteration alone: {last:,}; "
          f"overhead of the earlier iterations: {res.nodes - last:,})")
    print(f"Time              : {res.elapsed:.4f} s")
    if res.solution:
        print("\nLatin square:\n" + format_grid(res.solution))
        errs = validate_latin(res.solution, n, cfg.givens)
        print("Independent validation: " + ("VALID" if not errs else "INVALID " + str(errs)))


def save_run(text: str, tag: str, rows) -> str:
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, f"{tag}_{stamp}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    cpath = os.path.join(folder, "runs.csv")
    new = not os.path.exists(cpath)
    with open(cpath, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "n", "givens", "symmetry", "order", "seed", "start_depth", "step", "find_all",
                        "status", "solutions", "iterations", "last_limit", "nodes_total",
                        "nodes_last_iteration", "seconds", "message", "python"])
        for cfg, res in rows:
            w.writerow([stamp, cfg.n, cfg.givens is not None, cfg.symmetry_breaking,
                        cfg.value_order, cfg.seed,
                        cfg.start_depth, cfg.step, cfg.find_all, res.status, res.solutions,
                        len(res.iterations), res.iterations[-1].limit if res.iterations else "",
                        res.nodes, res.iterations[-1].nodes if res.iterations else "",
                        f"{res.elapsed:.4f}", res.message, sys.version.split()[0]])
    return path


# =============================================================================
# 5. AUTOMATED TESTS
# =============================================================================

EXAMPLE_5 = [[5, 1, 2, 3, 4], [4, 5, 1, 2, 3], [3, 4, 5, 1, 2], [2, 3, 4, 5, 1], [1, 2, 3, 4, 5]]


class TestValidation(unittest.TestCase):
    def test_assignment_example_is_latin(self):
        self.assertEqual(validate_latin(EXAMPLE_5), [])

    def test_bad_squares(self):
        bad = [r[:] for r in EXAMPLE_5]
        bad[0][0], bad[0][1] = bad[0][1], bad[0][0]          # breaks two columns
        self.assertTrue(validate_latin(bad))
        self.assertTrue(validate_latin(EXAMPLE_5[:4]))        # only 4 rows
        self.assertTrue(validate_latin([[1, 1], [2, 2]]))

    def test_parse_and_partial(self):
        g = parse_grid("1.3/.../...")
        self.assertEqual(g[0], [1, 0, 3])
        self.assertTrue(validate_partial(parse_grid("11./.../...")))
        self.assertTrue(validate_partial(parse_grid("4../.../...")))
        with self.assertRaises(ValueError):
            parse_grid("12/123")


class TestIDDFS(unittest.TestCase):
    def check(self, **kw):
        cfg = Config(**kw)
        r = solve(cfg)
        self.assertEqual(r.status, FOUND, r.message)
        self.assertEqual(validate_latin(r.solution, cfg.n, cfg.givens), [])
        return r

    def test_small_n_found(self):
        for n in range(1, 7):
            r = self.check(n=n)
            limits = [it.limit for it in r.iterations]
            self.assertEqual(limits, list(range(0, r.empty + 1)))   # 0, 1, ..., E
            for it in r.iterations[:-1]:
                self.assertGreater(it.cutoffs, 0)     # every earlier DLS was cut off

    def test_counts_all_latin_squares(self):
        for n in range(1, 5):
            r = self.check(n=n, symmetry_breaking=False, find_all=True, start_depth=n * n)
            self.assertEqual(r.solutions, LATIN_COUNT[n - 1])

    def test_counts_reduced_squares(self):
        for n in range(1, 7):
            r = self.check(n=n, find_all=True, start_depth=(n - 1) ** 2)
            self.assertEqual(r.solutions, REDUCED_COUNT[n - 1])

    def test_formula_L_equals_n_fact_nm1_fact_R(self):
        for n in range(1, 11):
            self.assertEqual(LATIN_COUNT[n - 1],
                             math.factorial(n) * math.factorial(n - 1) * REDUCED_COUNT[n - 1])

    def test_iddfs_same_answer_as_single_dls(self):
        # IDDFS's last iteration is a DFS with limit E: same first solution
        for n in (3, 4, 5):
            a = self.check(n=n)
            b = self.check(n=n, start_depth=n * n)
            self.assertEqual(a.solution, b.solution)
            self.assertEqual(a.iterations[-1].nodes, b.iterations[-1].nodes)

    def test_completion_with_givens(self):
        g = parse_grid("1.../.2../..3./...4")
        self.check(n=4, givens=g)

    def test_no_solution_detected(self):
        # 1 2 . / . . 3 / . . . : cell (1,3) must be 3, but column 3 has 3 -> impossible
        g = parse_grid("12./..3/...")
        r = solve(Config(n=3, givens=g))
        self.assertEqual(r.status, NO_SOLUTION)

    def test_invalid_input(self):
        self.assertEqual(solve(Config(n=2, givens=[[1, 1], [0, 0]])).status, INVALID)

    def test_limit_reported(self):
        r = solve(Config(n=8, max_nodes=5_000, time_limit=None))
        self.assertEqual(r.status, LIMIT_REACHED)
        self.assertIsNone(r.solution)

    def test_larger_n_with_dfs_start(self):
        self.check(n=12, start_depth=11 * 11)

    def test_auto_mode(self):
        self.assertEqual(auto_mode(5)[:2], (0, "ascending"))          # pure IDDFS
        self.assertEqual(auto_mode(6)[:2], (0, "ascending"))
        self.assertEqual(auto_mode(7)[:2], (36, "ascending"))         # last iteration only
        self.assertEqual(auto_mode(20)[:2], (361, "random"))
        for n in (7, 10, 20):
            start, order, _ = auto_mode(n)
            self.check(n=n, start_depth=start, value_order=order, time_limit=30)

    def test_cli_prints_square_for_large_n(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["20"])
        self.assertIn("Independent validation: VALID", buf.getvalue())

    def test_random_order(self):
        for seed in range(3):
            r = self.check(n=6, value_order="random", seed=seed)
            self.assertEqual(len(r.iterations), r.empty + 1)
        self.check(n=20, start_depth=19 * 19, value_order="random", seed=0)


def run_tests() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


# =============================================================================
# 6. COMMAND LINE
# =============================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Latin square - IDDFS with Backtracking")
    ap.add_argument("n", nargs="?", type=int, default=5, help="order of the square")
    ap.add_argument("--grid", help="partial square to complete, rows separated by '/'")
    ap.add_argument("--no-symmetry", action="store_true",
                    help="do not fix the first row/column (empty grid only)")
    ap.add_argument("--start-depth", type=int, default=None,
                    help="first depth limit; default: automatic (0 for small n)")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--all", action="store_true", help="count all solutions (last iteration)")
    ap.add_argument("--order", choices=["auto", "ascending", "random"], default="auto",
                    help="order of the children (default: automatic)")
    ap.add_argument("--random", action="store_true", help="same as --order random")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-nodes", type=int, default=20_000_000, help="0 = unlimited")
    ap.add_argument("--time-limit", type=float, default=60.0, help="0 = unlimited")
    ap.add_argument("--experiment", action="store_true", help="run the report experiments")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args(argv)
    if a.test:
        return run_tests()

    lim = dict(max_nodes=a.max_nodes or None, time_limit=a.time_limit or None)
    cfgs = []
    if a.experiment:
        for n in range(1, 8):                                   # IDDFS from depth 0
            cfgs.append(Config(n=n, **lim))
        for n in (4, 5):                                        # without symmetry breaking
            cfgs.append(Config(n=n, symmetry_breaking=False, **lim))
        for n in (5, 6, 7, 8, 10, 12, 13, 14, 15, 20):          # only the last iteration
            cfgs.append(Config(n=n, start_depth=(n - 1) ** 2, **lim))
        for n in (15, 20, 30):                                  # last iteration, random order
            for seed in range(3):
                cfgs.append(Config(n=n, start_depth=(n - 1) ** 2, value_order="random",
                                   seed=seed, **lim))
    else:
        givens = parse_grid(a.grid) if a.grid else None
        n = len(givens) if givens else a.n
        if a.random:
            a.order = "random"
        auto_start, auto_order, note = auto_mode(n, givens, not a.no_symmetry)
        start = auto_start if a.start_depth is None else a.start_depth
        order = auto_order if a.order == "auto" else a.order
        if a.start_depth is not None or a.order != "auto":
            note = "chosen on the command line"
        mode_note = f"Mode              : start depth {start}, {order} order - {note}"
        cfgs.append(Config(n=n, givens=givens, symmetry_breaking=not a.no_symmetry,
                           start_depth=start, step=a.step, find_all=a.all,
                           value_order=order, seed=a.seed, **lim))

    buf = io.StringIO()
    rows = []
    with redirect_stdout(buf):
        print("=" * 72)
        print("LATIN SQUARE - IDDFS WITH BACKTRACKING")
        print(f"Run at {datetime.now():%Y-%m-%d %H:%M:%S}, Python {sys.version.split()[0]}")
        print("=" * 72)
        for cfg in cfgs:
            res = solve(cfg)
            rows.append((cfg, res))
            if a.experiment:
                last = res.iterations[-1] if res.iterations else None
                order = "asc" if cfg.value_order == "ascending" else f"rnd{cfg.seed}"
                print(f"n={cfg.n:<3} sym={str(cfg.symmetry_breaking):<5} {order:<5} start={cfg.start_depth:<4} "
                      f"E={res.empty:<4} {res.status:<14} iterations={len(res.iterations):<4} "
                      f"nodes total={res.nodes:>12,}  last iter={last.nodes if last else 0:>12,} "
                      f"t={res.elapsed:8.3f}s {res.message}")
            else:
                print(mode_note)
                print_run(cfg, res)
                print()
    text = buf.getvalue()
    print(text, end="")
    if a.save:
        tag = "experiment" if a.experiment else f"n{cfgs[0].n}" + (
            "_grid" if cfgs[0].givens else "") + ("_nosym" if a.no_symmetry else "") + (
            f"_start{cfgs[0].start_depth}" if cfgs[0].start_depth else "") + (
            f"_rand{cfgs[0].seed}" if cfgs[0].value_order == "random" else "")
        print(f"Saved to {save_run(text, tag, rows)} (and results/runs.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
