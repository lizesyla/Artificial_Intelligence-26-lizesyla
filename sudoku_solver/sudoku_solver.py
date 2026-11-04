#!/usr/bin/env python3
"""
Sudoku Solver - BFS with Backtracking
=====================================

Course : Artificial Intelligence - Uninformed Search Techniques (Part 2)

Board: n x n grid (n = box_rows * box_cols, e.g. 4 = 2x2, 6 = 2x3, 9 = 3x3).
Each row, column and box must contain the digits 1..n exactly once.

How the search works (short version)
-----------------------------------
STATE  : a partially filled grid.
ACTION : choose ONE empty cell (always by the same fixed rule) and write a
         digit that does not already appear in its row, column or box.
BFS    : states are kept in a FIFO queue, so the search tree is explored
         level by level: first all grids with 1 new digit, then all grids
         with 2 new digits, ...
BACKTRACKING part: a digit that breaks a constraint is never placed
         (the branch is cut immediately), and a state whose chosen cell has
         no legal digit is a DEAD END - it is dropped and the search goes on
         with the next state in the queue.

For comparison the same expansion can be run with a LIFO stack (--algorithm dfs);
that is classic depth-first backtracking. BFS is the required algorithm.

Usage (run inside the sudoku_solver/ folder)
--------------------------------------------
    python sudoku_solver.py --test
    python sudoku_solver.py --list
    python sudoku_solver.py --level easy          # the three required levels
    python sudoku_solver.py --level medium --all
    python sudoku_solver.py --level hard --save
    python sudoku_solver.py --generate hard --seed 7   # a new random puzzle
    python sudoku_solver.py --puzzle easy4
    python sudoku_solver.py --puzzle wiki9 --save
    python sudoku_solver.py --puzzle escargot9 --order mrv --save
    python sudoku_solver.py --puzzle wiki9 --algorithm dfs
    python sudoku_solver.py --grid "1.3...4..2..3.1." --box 2x2
    python sudoku_solver.py --benchmark --save
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
import tracemalloc
import unittest
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

SOLVED = "SOLVED"                # at least one solution found
NO_SOLUTION = "NO_SOLUTION"      # whole tree explored, no solution exists
LIMIT_REACHED = "LIMIT_REACHED"  # node / frontier / time limit hit -> unknown
INVALID = "INVALID_PUZZLE"       # givens already break a rule


# =============================================================================
# 1. PUZZLES (all checked by the tests)
# =============================================================================

PUZZLES: Dict[str, Tuple[str, str, str]] = {
    # name: (box "RxC", grid, description)
    # --- the three levels required by the assignment (9x9, unique solution) ---
    "easy": ("3x3", "..6.......8.7..4..72...6.81.421593...7....1.9..9....42835.6...426791.83591...52..",
             "EASY 9x9, 38 givens (generate('easy', seed=1))"),
    "medium": ("3x3", "...7......8....6.4....91.3...468.2.......2...3125....8...9...2...746.3.1193..78.6",
               "MEDIUM 9x9, 30 givens (generate('medium', seed=2))"),
    "hard": ("3x3", "...7......8....6.4....91.....468.........2...31......8...9...2...746.3.1193...8..",
             "HARD 9x9, 24 givens (generate('hard', seed=2))"),
    # --- extra puzzles for testing and comparison ---
    "easy4": ("2x2", ".32.4..1....24..", "4x4, 6 givens, unique solution"),
    "empty4": ("2x2", "." * 16, "4x4 empty grid (288 solutions)"),
    "easy6": ("2x3", "1...5...6......6.4.3..15..1...5...41", "6x6, 12 givens, unique solution"),
    "hard6": ("2x3", ".2.4.6.5....2.......4.3......4..13..", "6x6, 10 givens, unique solution"),
    "wiki9": ("3x3", "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79",
              "9x9, 30 givens (Wikipedia example)"),
    "escargot9": ("3x3", "1....7.9..3..2...8..96..5....53..9...1..8...26....4...3......1..4......7..7...3..",
                  "9x9, 23 givens ('AI Escargot', A. Inkala)"),
    "clue17": ("3x3", "..............3.85..1.2.......5.7.....4...1...9.......5......73..2.1........4...9",
               "9x9, 17 givens (hard for brute force)"),
    "nosol9": ("3x3", "12345678." + "........9" + "." * 63,
               "9x9, consistent givens but NO solution"),
    "invalid9": ("3x3", "11" + "." * 79, "9x9, two 1s in row 1 (invalid)"),
}


# =============================================================================
# 2. BOARD GEOMETRY AND PARSING
# =============================================================================

class Board:
    """Geometry of an n x n Sudoku: which cells are 'peers' of each cell."""

    def __init__(self, box_rows: int, box_cols: int):
        self.br, self.bc = box_rows, box_cols
        self.n = n = box_rows * box_cols
        if not 1 <= n <= 9:
            raise ValueError("this implementation supports n <= 9 (digits 1..9)")
        self.cells = n * n
        self.row = [i // n for i in range(self.cells)]
        self.col = [i % n for i in range(self.cells)]
        self.box = [(r // box_rows) * (n // box_cols) + c // box_cols
                    for r, c in zip(self.row, self.col)]
        self.units = ([[i for i in range(self.cells) if self.row[i] == k] for k in range(n)]
                      + [[i for i in range(self.cells) if self.col[i] == k] for k in range(n)]
                      + [[i for i in range(self.cells) if self.box[i] == k] for k in range(n)])
        self.peers = [sorted({j for u in self.units if i in u for j in u} - {i})
                      for i in range(self.cells)]
        self.all_digits = set(range(1, n + 1))


def parse_box(text: str) -> Tuple[int, int]:
    r, c = text.lower().split("x")
    return int(r), int(c)


def parse_grid(text: str, board: Board) -> bytes:
    """'.' or '0' = empty. Whitespace and '|', '-', '+' are ignored."""
    chars = [ch for ch in text if ch not in " \t\r\n|-+"]
    if len(chars) != board.cells:
        raise ValueError(f"grid needs {board.cells} cells, got {len(chars)}")
    out = []
    for ch in chars:
        if ch in ".0":
            out.append(0)
        elif ch.isdigit() and 1 <= int(ch) <= board.n:
            out.append(int(ch))
        else:
            raise ValueError(f"invalid character {ch!r} for a {board.n}x{board.n} grid")
    return bytes(out)


def format_grid(state: bytes, board: Board, givens: Optional[bytes] = None) -> str:
    n, br, bc = board.n, board.br, board.bc
    lines = []
    sep = "+" + "+".join(["-" * (2 * bc + 1)] * (n // bc)) + "+"
    for r in range(n):
        if r % br == 0:
            lines.append(sep)
        row = "|"
        for c in range(n):
            v = state[r * n + c]
            row += " " + (str(v) if v else ".")
            if (c + 1) % bc == 0:
                row += " |"
        lines.append(row)
    lines.append(sep)
    return "\n".join(lines)


def to_string(state: bytes) -> str:
    return "".join(str(v) if v else "." for v in state)


# =============================================================================
# 3. VALIDATION (independent of the search)
# =============================================================================

def validate_puzzle(puzzle: bytes, board: Board) -> List[str]:
    """Givens must not repeat in any row, column or box."""
    errors = []
    if len(puzzle) != board.cells:
        return [f"expected {board.cells} cells, got {len(puzzle)}"]
    names = ["row", "column", "box"]
    for k, unit in enumerate(board.units):
        vals = [puzzle[i] for i in unit if puzzle[i]]
        dup = sorted({v for v in vals if vals.count(v) > 1})
        if dup:
            errors.append(f"{names[k // board.n]} {k % board.n + 1}: repeated digits {dup}")
    for i, v in enumerate(puzzle):
        if v > board.n:
            errors.append(f"cell {i}: digit {v} out of range")
    return errors


def validate_solution(solution: bytes, puzzle: bytes, board: Board) -> List[str]:
    """A solution must be complete, every unit a permutation of 1..n, and keep the givens."""
    errors = []
    if len(solution) != board.cells:
        return [f"expected {board.cells} cells, got {len(solution)}"]
    if 0 in solution:
        errors.append(f"{solution.count(0)} empty cells")
    names = ["row", "column", "box"]
    for k, unit in enumerate(board.units):
        vals = {solution[i] for i in unit}
        if vals != board.all_digits:
            errors.append(f"{names[k // board.n]} {k % board.n + 1} is not a permutation of 1..{board.n}")
    for i, (p, s) in enumerate(zip(puzzle, solution)):
        if p and p != s:
            errors.append(f"given at cell {i} changed from {p} to {s}")
    return errors


# =============================================================================
# 4. SUCCESSOR FUNCTION (shared by BFS, DFS and the visualizer)
# =============================================================================

def legal_digits(state: bytes, i: int, board: Board) -> List[int]:
    used = {state[p] for p in board.peers[i]}
    return [d for d in range(1, board.n + 1) if d not in used]


def choose_cell(state: bytes, board: Board, order: str) -> Tuple[int, List[int]]:
    """Return (cell, legal digits) for the cell that will be expanded, or (-1, []) if full.
    order = "first": first empty cell in reading order (fixed, uninformed).
    order = "mrv"  : empty cell with the fewest legal digits (variable-ordering heuristic)."""
    if order == "first":
        i = state.find(0)
        return (i, legal_digits(state, i, board)) if i >= 0 else (-1, [])
    best, best_d = -1, []
    for i, v in enumerate(state):
        if v == 0:
            d = legal_digits(state, i, board)
            if best < 0 or len(d) < len(best_d):
                best, best_d = i, d
                if not d:
                    break
    return best, best_d


def expand(state: bytes, board: Board, order: str):
    """Children of a state. Illegal digits are never generated (pruning).
    Returns (cell, digits, children). Empty 'children' with cell >= 0 = dead end."""
    cell, digits = choose_cell(state, board, order)
    children = []
    for d in digits:
        child = bytearray(state)
        child[cell] = d
        children.append(bytes(child))
    return cell, digits, children


# =============================================================================
# 5. THE SEARCH
# =============================================================================

@dataclass
class Config:
    algorithm: str = "bfs"             # "bfs" (required) or "dfs" (comparison)
    order: str = "first"               # "first" or "mrv"
    find_all: bool = False             # count all solutions (proves uniqueness)
    max_solutions: int = 1000
    max_nodes: Optional[int] = 5_000_000
    max_frontier: Optional[int] = 2_000_000   # memory guard
    time_limit: Optional[float] = 120.0
    trace_memory: bool = False          # measure real peak memory with tracemalloc (slower)


@dataclass
class Result:
    status: str
    solutions: List[bytes]
    generated: int = 0          # states created (root included)
    expanded: int = 0           # states taken out of the queue and expanded
    dead_ends: int = 0          # expanded states with no legal child
    max_frontier: int = 0       # largest queue/stack size seen
    max_depth: int = 0          # most digits added on one path
    empty_cells: int = 0        # depth of every solution
    level_sizes: List[int] = field(default_factory=list)   # states generated per depth
    elapsed: float = 0.0
    peak_memory: Optional[int] = None  # bytes (only with trace_memory)
    first_solution_after: Optional[int] = None   # generated count when 1st solution appeared
    stop_reason: str = ""


def solve(puzzle: bytes, board: Board, cfg: Config = Config()) -> Result:
    if cfg.algorithm not in ("bfs", "dfs") or cfg.order not in ("first", "mrv"):
        raise ValueError("algorithm must be bfs/dfs and order first/mrv")
    errs = validate_puzzle(puzzle, board)
    if errs:
        return Result(INVALID, [], stop_reason="; ".join(errs))

    if cfg.trace_memory:
        tracemalloc.start()
    start = time.perf_counter()
    empty = puzzle.count(0)
    res = Result(NO_SOLUTION, [], empty_cells=empty, level_sizes=[0] * (empty + 1))
    res.generated, res.level_sizes[0] = 1, 1

    if empty == 0:
        res.status, res.solutions, res.first_solution_after = SOLVED, [puzzle], 1
    else:
        try:
            if cfg.algorithm == "bfs":
                _bfs(puzzle, board, cfg, res, start, empty)
            else:
                _dfs(puzzle, board, cfg, res, start, empty)
        except _Stop as s:
            res.stop_reason = str(s)
            res.status = LIMIT_REACHED
        else:
            if res.solutions:
                res.status = SOLVED
    res.elapsed = time.perf_counter() - start
    if cfg.trace_memory:
        res.peak_memory = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    if res.status == LIMIT_REACHED and res.solutions:
        # a solution was found, but the search to count all of them stopped
        res.status = SOLVED
    return res


class _Stop(Exception):
    pass


def _check(cfg: Config, res: Result, frontier: int, start: float) -> None:
    if cfg.max_nodes is not None and res.generated >= cfg.max_nodes:
        raise _Stop(f"node limit {cfg.max_nodes:,}")
    if cfg.max_frontier is not None and frontier > cfg.max_frontier:
        raise _Stop(f"frontier limit {cfg.max_frontier:,} (memory guard)")
    if cfg.time_limit is not None and (res.generated & 4095) == 0 \
            and time.perf_counter() - start > cfg.time_limit:
        raise _Stop(f"time limit {cfg.time_limit}s")


def _record_solution(child: bytes, cfg: Config, res: Result) -> bool:
    """Returns True when the search should stop."""
    res.solutions.append(child)
    if res.first_solution_after is None:
        res.first_solution_after = res.generated
    if not cfg.find_all or len(res.solutions) >= cfg.max_solutions:
        return True
    return False


def _bfs(puzzle, board, cfg, res, start, empty):
    """Breadth-first: process the tree one LEVEL at a time (= FIFO queue order)."""
    level = [puzzle]                      # the frontier (FIFO queue), current depth
    depth = 0
    while level:
        nxt = []                          # states of depth + 1, in FIFO order
        for idx, state in enumerate(level):
            res.expanded += 1
            cell, digits, children = expand(state, board, cfg.order)
            if not children:
                res.dead_ends += 1        # backtrack: this branch is dropped
            for child in children:
                res.generated += 1
                res.level_sizes[depth + 1] += 1
                res.max_depth = max(res.max_depth, depth + 1)
                if depth + 1 == empty:    # goal test when generated
                    if _record_solution(child, cfg, res):
                        return
                else:
                    nxt.append(child)
                frontier = len(level) - idx - 1 + len(nxt)
                if frontier > res.max_frontier:
                    res.max_frontier = frontier
                _check(cfg, res, frontier, start)
        level = nxt
        depth += 1


def _dfs(puzzle, board, cfg, res, start, empty):
    """Depth-first (LIFO stack): classic backtracking, for comparison only."""
    stack = [(puzzle, 0)]
    while stack:
        state, depth = stack.pop()
        res.expanded += 1
        cell, digits, children = expand(state, board, cfg.order)
        if not children:
            res.dead_ends += 1
        for child in reversed(children):   # so the smallest digit is tried first
            res.generated += 1
            res.level_sizes[depth + 1] += 1
            res.max_depth = max(res.max_depth, depth + 1)
            if depth + 1 == empty:
                if _record_solution(child, cfg, res):
                    return
            else:
                stack.append((child, depth + 1))
            if len(stack) > res.max_frontier:
                res.max_frontier = len(stack)
            _check(cfg, res, len(stack), start)


# =============================================================================
# 6. OUTPUT AND SAVING
# =============================================================================

def describe_status(res: Result, cfg: Config) -> str:
    if res.status == INVALID:
        return "The puzzle itself breaks a rule: " + res.stop_reason
    if res.status == SOLVED:
        s = f"Solved. Solutions found: {len(res.solutions)}"
        if cfg.find_all:
            if res.stop_reason:
                s += f" (search for more stopped: {res.stop_reason}; uniqueness NOT proven)"
            elif len(res.solutions) >= cfg.max_solutions:
                s += f" (stopped at max_solutions = {cfg.max_solutions})"
            else:
                s += " (complete tree explored: this is the exact number of solutions)"
        else:
            s += " (stopped at the first one; uniqueness not checked - use --all)"
        return s
    if res.status == NO_SOLUTION:
        return "The complete search tree was explored: the puzzle has NO solution."
    return f"Stopped by a limit ({res.stop_reason}). Nothing is proven about this puzzle."


def print_run(name: str, puzzle: bytes, board: Board, cfg: Config, res: Result) -> None:
    print(f"Puzzle            : {name} ({board.n}x{board.n}, boxes {board.br}x{board.bc}), "
          f"givens = {board.cells - puzzle.count(0)}, empty = {puzzle.count(0)}")
    print(format_grid(puzzle, board))
    print(f"Algorithm         : {cfg.algorithm.upper()}   cell order: {cfg.order}   "
          f"find all: {cfg.find_all}")
    print(f"Limits            : max_nodes={cfg.max_nodes}, max_frontier={cfg.max_frontier}, "
          f"time_limit={cfg.time_limit}s")
    print(f"Status            : {res.status}")
    print(f"Explanation       : {describe_status(res, cfg)}")
    print(f"States generated  : {res.generated:,}")
    print(f"States expanded   : {res.expanded:,}")
    print(f"Dead ends         : {res.dead_ends:,}")
    print(f"Max frontier size : {res.max_frontier:,}")
    print(f"Max depth         : {res.max_depth} of {res.empty_cells}")
    if res.first_solution_after:
        print(f"1st solution after: {res.first_solution_after:,} generated states")
    print(f"Time              : {res.elapsed:.4f} s")
    if res.peak_memory is not None:
        print(f"Peak memory       : {res.peak_memory / 1e6:.2f} MB (tracemalloc)")
    if res.level_sizes and res.status != INVALID:
        print("States per depth  : " + " ".join(str(x) for x in res.level_sizes))
    if res.solutions:
        print("\nSolution:")
        print(format_grid(res.solutions[0], board))
        errs = validate_solution(res.solutions[0], puzzle, board)
        print("Independent validation: " + ("VALID" if not errs else "INVALID " + str(errs)))


def results_dir() -> str:
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(d, exist_ok=True)
    return d


def save_run(text: str, tag: str, rows) -> str:
    folder = results_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, f"{tag}_{stamp}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    csv_path = os.path.join(folder, "runs.csv")
    new = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "puzzle", "size", "empty", "algorithm", "order", "find_all",
                        "status", "solutions", "generated", "expanded", "dead_ends",
                        "max_frontier", "max_depth", "seconds", "peak_MB", "stop_reason",
                        "python"])
        for name, board, puzzle, cfg, res in rows:
            w.writerow([stamp, name, board.n, puzzle.count(0), cfg.algorithm, cfg.order,
                        cfg.find_all, res.status, len(res.solutions), res.generated,
                        res.expanded, res.dead_ends, res.max_frontier, res.max_depth,
                        f"{res.elapsed:.4f}",
                        "" if res.peak_memory is None else f"{res.peak_memory / 1e6:.2f}",
                        res.stop_reason, sys.version.split()[0]])
    return path


# =============================================================================
# 6b. DIFFICULTY LEVELS AND PUZZLE GENERATOR
# =============================================================================
# The assignment asks for three levels: Easy, Medium, Hard. Here a level is
# defined by the number of givens (fewer givens = more empty cells = deeper
# and wider search tree). The generator is only a tool to CREATE puzzles;
# the search that is studied is solve() with BFS.

LEVEL_GIVENS = {"easy": 38, "medium": 30, "hard": 24}


def random_solution(board: Board, rng) -> bytes:
    """A random complete grid: start from a valid pattern and apply moves that
    keep it valid (shuffle rows inside a band, the bands, columns inside a
    stack, the stacks, and rename the digits)."""
    n, br, bc = board.n, board.br, board.bc

    def pattern(r, c):
        return (bc * (r % br) + r // br + c) % n

    bands = list(range(n // br))
    rng.shuffle(bands)
    rows = [b * br + r for b in bands for r in rng.sample(range(br), br)]
    stacks = list(range(n // bc))
    rng.shuffle(stacks)
    cols = [t * bc + c for t in stacks for c in rng.sample(range(bc), bc)]
    digits = rng.sample(range(1, n + 1), n)
    return bytes(digits[pattern(r, c)] for r in rows for c in cols)


def count_solutions(puzzle: bytes, board: Board, limit: int = 2) -> int:
    cfg = Config("dfs", "mrv", find_all=True, max_solutions=limit, max_nodes=None,
                 max_frontier=None, time_limit=None)
    return len(solve(puzzle, board, cfg).solutions)


def generate(level: str, board: Board, seed: int = 0) -> bytes:
    """Remove digits from a random full grid, in random order, as long as the
    puzzle keeps exactly ONE solution, until the target number of givens."""
    import random
    rng = random.Random(seed)
    target = round(LEVEL_GIVENS[level] * board.cells / 81)
    p = bytearray(random_solution(board, rng))
    cells = list(range(board.cells))
    rng.shuffle(cells)
    for i in cells:
        if board.cells - p.count(0) <= target:
            break
        keep = p[i]
        p[i] = 0
        if count_solutions(bytes(p), board) != 1:
            p[i] = keep           # removing this digit would allow 2+ solutions
    return bytes(p)


# =============================================================================
# 7. AUTOMATED TESTS   (python sudoku_solver.py --test)
# =============================================================================

def _load(name):
    box, grid, _ = PUZZLES[name]
    board = Board(*parse_box(box))
    return board, parse_grid(grid, board)


class TestBoardAndValidation(unittest.TestCase):
    def test_peers(self):
        b = Board(3, 3)
        self.assertTrue(all(len(p) == 20 for p in b.peers))
        self.assertTrue(all(len(p) == 7 for p in Board(2, 2).peers))
        self.assertTrue(all(len(p) == 12 for p in Board(2, 3).peers))

    def test_parse(self):
        b = Board(2, 2)
        self.assertEqual(parse_grid("1.3.\n0000 | 2..4 ....", b)[:4], bytes([1, 0, 3, 0]))
        with self.assertRaises(ValueError):
            parse_grid("123", b)
        with self.assertRaises(ValueError):
            parse_grid("5" + "." * 15, b)          # 5 not allowed in 4x4

    def test_invalid_puzzle_detected(self):
        b, p = _load("invalid9")
        self.assertTrue(validate_puzzle(p, b))
        self.assertEqual(solve(p, b).status, INVALID)

    def test_valid_solution(self):
        b = Board(2, 2)
        sol = parse_grid("1234341221434321", b)
        self.assertEqual(validate_solution(sol, parse_grid("1..." + "." * 12, b), b), [])

    def test_bad_solutions(self):
        b = Board(2, 2)
        good = parse_grid("1234341221434321", b)
        swapped = parse_grid("2134341221434321", b)          # breaks column 1/2 and box
        self.assertTrue(validate_solution(swapped, bytes(16), b))
        self.assertTrue(validate_solution(good[:-1] + b"\x00", bytes(16), b))   # incomplete
        given = parse_grid("4" + "." * 15, b)
        self.assertTrue(any("given" in e for e in validate_solution(good, given, b)))


class TestLevels(unittest.TestCase):
    def test_builtin_levels_unique_and_solved_by_bfs(self):
        givens = []
        for lv in ("easy", "medium", "hard"):
            b, p = _load(lv)
            givens.append(b.cells - p.count(0))
            self.assertEqual(count_solutions(p, b), 1)
            r = solve(p, b, Config("bfs", "first"))
            self.assertEqual(r.status, SOLVED)
            self.assertEqual(validate_solution(r.solutions[0], p, b), [])
        self.assertEqual(givens, [38, 30, 24])

    def test_builtin_levels_match_generator(self):
        b = Board(3, 3)
        for lv, seed in (("easy", 1), ("medium", 2), ("hard", 2)):
            self.assertEqual(to_string(generate(lv, b, seed)), PUZZLES[lv][1])

    def test_random_solution_is_valid(self):
        import random
        for br, bc in ((2, 2), (2, 3), (3, 3)):
            b = Board(br, bc)
            for seed in range(5):
                sol = random_solution(b, random.Random(seed))
                self.assertEqual(validate_solution(sol, bytes(b.cells), b), [])

    def test_generated_puzzles_unique(self):
        b = Board(3, 3)
        for lv in ("easy", "medium"):
            p = generate(lv, b, seed=11)
            self.assertEqual(count_solutions(p, b), 1)
            self.assertLessEqual(b.cells - p.count(0), LEVEL_GIVENS[lv] + 2)


class TestSearch(unittest.TestCase):
    def assert_solved(self, name, **kw):
        b, p = _load(name)
        r = solve(p, b, Config(**kw))
        self.assertEqual(r.status, SOLVED, (name, kw, r.stop_reason))
        for s in r.solutions:
            self.assertEqual(validate_solution(s, p, b), [])
        return r

    def test_easy4_bfs(self):
        r = self.assert_solved("easy4", find_all=True)
        self.assertEqual(len(r.solutions), 1)

    def test_6x6_unique_bfs(self):
        for name in ("easy6", "hard6"):
            self.assertEqual(len(self.assert_solved(name, find_all=True).solutions), 1)

    def test_wiki9_unique_bfs(self):
        r = self.assert_solved("wiki9", find_all=True)
        self.assertEqual(len(r.solutions), 1)

    def test_empty4_has_288_solutions(self):
        r = self.assert_solved("empty4", find_all=True)
        self.assertEqual(len(r.solutions), 288)
        self.assertEqual(len(set(r.solutions)), 288)

    def test_bfs_and_dfs_agree(self):
        for name in ("easy4", "easy6", "hard6", "wiki9", "empty4"):
            for order in ("first", "mrv"):
                b, p = _load(name)
                rb = solve(p, b, Config("bfs", order, find_all=True))
                rd = solve(p, b, Config("dfs", order, find_all=True))
                self.assertEqual(sorted(rb.solutions), sorted(rd.solutions))
                # with find_all, both explore the SAME tree -> same node counts
                self.assertEqual(rb.generated, rd.generated)
                self.assertEqual(rb.level_sizes, rd.level_sizes)

    def test_bfs_levels_are_in_order(self):
        # BFS finds the first solution only after generating every shallower level
        b, p = _load("wiki9")
        r = solve(p, b, Config("bfs", "first"))
        self.assertGreaterEqual(r.first_solution_after, sum(r.level_sizes[:-1]))

    def test_no_solution(self):
        b, p = _load("nosol9")
        self.assertEqual(validate_puzzle(p, b), [])
        r = solve(p, b, Config("bfs", "mrv"))
        self.assertEqual(r.status, NO_SOLUTION)

    def test_hard_with_mrv(self):
        self.assert_solved("escargot9", order="mrv", find_all=True)

    def test_limit_reported(self):
        b, p = _load("clue17")
        r = solve(p, b, Config("bfs", "first", max_nodes=2000, time_limit=None))
        self.assertEqual(r.status, LIMIT_REACHED)
        self.assertFalse(r.solutions)

    def test_already_solved(self):
        b = Board(2, 2)
        sol = parse_grid("1234341221434321", b)
        self.assertEqual(solve(sol, b).status, SOLVED)


def run_tests() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


# =============================================================================
# 8. COMMAND LINE
# =============================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sudoku - BFS with Backtracking")
    ap.add_argument("--level", choices=["easy", "medium", "hard"],
                    help="solve the built-in puzzle of this level")
    ap.add_argument("--generate", choices=["easy", "medium", "hard"],
                    help="generate a NEW puzzle of this level (use --seed)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--puzzle", default="easy", help="built-in puzzle name (see --list)")
    ap.add_argument("--grid", help="your own puzzle as a string ('.' or 0 = empty)")
    ap.add_argument("--file", help="read the puzzle from a text file")
    ap.add_argument("--box", default="3x3", help="box shape for --grid/--file, e.g. 2x2, 2x3, 3x3")
    ap.add_argument("--algorithm", choices=["bfs", "dfs"], default="bfs")
    ap.add_argument("--order", choices=["first", "mrv"], default="first")
    ap.add_argument("--all", action="store_true", help="count all solutions")
    ap.add_argument("--max-nodes", type=int, default=5_000_000, help="0 = unlimited")
    ap.add_argument("--max-frontier", type=int, default=2_000_000, help="0 = unlimited")
    ap.add_argument("--time-limit", type=float, default=120.0, help="0 = unlimited")
    ap.add_argument("--memory", action="store_true", help="measure peak memory (slower)")
    ap.add_argument("--benchmark", action="store_true", help="run all built-in puzzles")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--save", action="store_true", help="save output into results/")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args(argv)

    if a.test:
        return run_tests()
    if a.list:
        for k, (box, g, d) in PUZZLES.items():
            print(f"{k:<10} {box}  {d}")
        return 0

    base = dict(max_nodes=a.max_nodes or None, max_frontier=a.max_frontier or None,
                time_limit=a.time_limit or None, trace_memory=a.memory)
    jobs = []
    if a.benchmark:
        for name in ("easy", "medium", "hard", "easy4", "easy6", "hard6", "wiki9",
                     "escargot9", "clue17", "nosol9"):
            box, g, _ = PUZZLES[name]
            board = Board(*parse_box(box))
            for alg, order, fa in (("bfs", "first", True), ("dfs", "first", True),
                                   ("bfs", "mrv", True), ("dfs", "mrv", True),
                                   ("bfs", "first", False), ("dfs", "first", False)):
                jobs.append((name, board, parse_grid(g, board),
                             Config(alg, order, find_all=fa, **base)))
    else:
        if a.generate:
            board = Board(*parse_box(a.box))
            text = to_string(generate(a.generate, board, a.seed))
            name = f"gen_{a.generate}_seed{a.seed}"
        elif a.grid or a.file:
            board = Board(*parse_box(a.box))
            text = a.grid if a.grid else open(a.file, encoding="utf-8").read()
            name = "custom" if a.grid else os.path.splitext(os.path.basename(a.file))[0]
        else:
            if a.level:
                a.puzzle = a.level
            if a.puzzle not in PUZZLES:
                print(f"unknown puzzle {a.puzzle!r}; use --list")
                return 2
            box, text, _ = PUZZLES[a.puzzle]
            board, name = Board(*parse_box(box)), a.puzzle
        jobs.append((name, board, parse_grid(text, board),
                     Config(a.algorithm, a.order, find_all=a.all, **base)))

    buf = io.StringIO()
    rows = []
    with redirect_stdout(buf):
        print("=" * 72)
        print("SUDOKU - BFS WITH BACKTRACKING")
        print(f"Run at {datetime.now():%Y-%m-%d %H:%M:%S}, Python {sys.version.split()[0]}")
        print("=" * 72)
        for name, board, puzzle, cfg in jobs:
            res = solve(puzzle, board, cfg)
            rows.append((name, board, puzzle, cfg, res))
            if a.benchmark:
                print(f"{name:<10} {cfg.algorithm.upper()} {cfg.order:<5} "
                      f"{'all  ' if cfg.find_all else 'first'} {res.status:<14} "
                      f"sol={len(res.solutions):<4} gen={res.generated:>10,} "
                      f"dead={res.dead_ends:>9,} maxQ={res.max_frontier:>9,} "
                      f"t={res.elapsed:8.3f}s {res.stop_reason}")
            else:
                print_run(name, puzzle, board, cfg, res)
    text = buf.getvalue()
    print(text, end="")
    if a.save:
        tag = "benchmark" if a.benchmark else (
            f"{jobs[0][0]}_{a.algorithm}_{a.order}" + ("_all" if a.all else ""))
        print(f"\nSaved to {save_run(text, tag, rows)} (and results/runs.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
