#!/usr/bin/env python3
"""
Social Golfers Problem - DFS with Backtracking
==============================================

Course : Artificial Intelligence - Uninformed Search Techniques (Part 1)
Problem: N = G * S golfers play once a week in G groups of S golfers.
         Find a schedule of W weeks such that no pair of golfers plays
         in the same group more than once.

Full instance : G = 8 groups, S = 4 golfers/group -> N = 32 golfers.
Small instance: G = 2 groups, S = 4 golfers/group -> N = 8 golfers.

How the search works (short version)
-----------------------------------
The schedule is a table of W * N empty "slots":
    week 1: group 1 [_ _ _ _]  group 2 [_ _ _ _] ...
    week 2: group 1 [_ _ _ _]  ...
DFS fills the slots one at a time, left to right. For each slot it tries the
candidate golfers in a fixed order. If a golfer breaks a constraint it is
skipped; if no golfer fits, DFS undoes the last assignment (BACKTRACKING)
and tries the next candidate there.

Usage (run from inside the social_golfers/ folder)
--------------------------------------------------
    python social_golfers.py --test                          # automated tests
    python social_golfers.py --groups 2 --size 4 --weeks 1   # small instance
    python social_golfers.py --groups 8 --size 4 --weeks 5   # full instance
    python social_golfers.py --groups 8 --size 4 --find-max --time-limit 60
    add  --save  to write the output into results/

Golfers are numbered 1..N.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
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

# A schedule is: list of weeks -> list of groups -> list of golfer numbers.
Schedule = List[List[List[int]]]

FOUND = "FOUND"                  # a valid schedule with W weeks was found
NO_SOLUTION = "NO_SOLUTION"      # the WHOLE search tree was explored: W weeks impossible
LIMIT_REACHED = "LIMIT_REACHED"  # stopped by node/time limit: result unknown


# =============================================================================
# 1. CONFIGURATION
# =============================================================================

@dataclass
class Config:
    groups: int = 8                    # G
    group_size: int = 4                # S
    weeks: int = 5                     # W (target number of weeks)
    max_nodes: Optional[int] = 10_000_000   # search limit: max assignments tried
    time_limit: Optional[float] = 60.0      # search limit: seconds
    symmetry_breaking: bool = True     # see SocialGolfersDFS docstring
    value_order: str = "ascending"     # "ascending" or "random" (order of children)
    seed: int = 0                      # used only when value_order == "random"

    @property
    def golfers(self) -> int:          # N = G * S
        return self.groups * self.group_size

    def check(self) -> None:
        if self.groups < 1:
            raise ValueError("groups must be >= 1")
        if self.group_size < 2:
            raise ValueError("group_size must be >= 2 (pairs must exist)")
        if self.weeks < 1:
            raise ValueError("weeks must be >= 1")
        if self.value_order not in ("ascending", "random"):
            raise ValueError("value_order must be 'ascending' or 'random'")


# =============================================================================
# 2. MATHEMATICS OF THE SEARCH SPACE
# =============================================================================

def upper_bound_weeks(groups: int, group_size: int) -> int:
    """Each week a golfer meets (S-1) NEW golfers; there are only N-1 others.
    So W * (S-1) <= N-1  ->  W <= floor((N-1)/(S-1)).  (Necessary, not sufficient.)"""
    n = groups * group_size
    return (n - 1) // (group_size - 1)


def count_possible_groups(groups: int, group_size: int) -> int:
    """Number of different groups (subsets of size S out of N): C(N, S)."""
    return math.comb(groups * group_size, group_size)


def count_week_partitions(groups: int, group_size: int) -> int:
    """Number of ways to split N golfers into G unordered groups of size S:
    N! / ( (S!)^G * G! )."""
    n = groups * group_size
    return math.factorial(n) // (math.factorial(group_size) ** groups * math.factorial(groups))


def count_schedules(groups: int, group_size: int, weeks: int) -> int:
    """Number of W-week schedules with NO pair constraint (ordered weeks,
    weeks may repeat): P^W where P = number of weekly partitions."""
    return count_week_partitions(groups, group_size) ** weeks


def sci(x: int) -> str:
    """Format a (possibly huge) integer in scientific notation without float overflow."""
    s = str(x)
    if len(s) <= 6:
        return s
    return f"{s[0]}.{s[1:4]}e{len(s) - 1}"


# =============================================================================
# 3. VALIDATION (independent of the solver)
# =============================================================================

def validate_schedule(schedule: Schedule, groups: int, group_size: int,
                      weeks: Optional[int] = None) -> List[str]:
    """Check a schedule against every constraint. Returns a list of error
    messages; an EMPTY list means the schedule is valid."""
    errors: List[str] = []
    n = groups * group_size
    everybody = set(range(1, n + 1))

    if weeks is not None and len(schedule) != weeks:
        errors.append(f"expected {weeks} weeks, got {len(schedule)}")

    first_meeting = {}  # (a, b) -> week number where the pair first met

    for w, week in enumerate(schedule, start=1):
        # C1: correct number of groups
        if len(week) != groups:
            errors.append(f"week {w}: expected {groups} groups, got {len(week)}")

        seen_this_week = []
        for g, group in enumerate(week, start=1):
            # C2: correct group size
            if len(group) != group_size:
                errors.append(f"week {w}, group {g}: expected size {group_size}, got {len(group)}")
            for x in group:
                if not isinstance(x, int) or not 1 <= x <= n:
                    errors.append(f"week {w}, group {g}: invalid golfer {x!r}")
            seen_this_week.extend(group)

        # C3: every golfer exactly once in the week
        counts = {}
        for x in seen_this_week:
            counts[x] = counts.get(x, 0) + 1
        duplicates = sorted(x for x, c in counts.items() if c > 1 and isinstance(x, int))
        missing = sorted(everybody - set(counts))
        if duplicates:
            errors.append(f"week {w}: golfers appear more than once: {duplicates}")
        if missing:
            errors.append(f"week {w}: golfers missing: {missing}")

        # C4: no pair meets twice (across all weeks)
        for g, group in enumerate(week, start=1):
            members = sorted(set(x for x in group if isinstance(x, int)))
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    pair = (members[i], members[j])
                    if pair in first_meeting:
                        errors.append(f"pair {pair} repeated: week {first_meeting[pair]} "
                                      f"and week {w}")
                    else:
                        first_meeting[pair] = w
    return errors


def is_valid_schedule(schedule: Schedule, groups: int, group_size: int,
                      weeks: Optional[int] = None) -> bool:
    return not validate_schedule(schedule, groups, group_size, weeks)


# =============================================================================
# 4. DFS WITH BACKTRACKING
# =============================================================================

class _LimitReached(Exception):
    """Raised internally when the node or time limit is hit."""


@dataclass
class SearchResult:
    status: str
    schedule: Optional[Schedule]
    nodes: int            # number of states generated (golfer assignments made)
    backtracks: int       # number of assignments undone
    elapsed: float        # seconds
    config: Config
    max_depth: int = 0    # deepest slot reached (= filled slots)
    best_weeks: int = 0   # most complete weeks seen during the search


class SocialGolfersDFS:
    """Depth-First Search with chronological backtracking.

    STATE  : a partially filled schedule (slots 0..k-1 filled).
    ACTION : put a golfer into the next empty slot k.
    GOAL   : all W * N slots filled and all constraints satisfied.

    Constraint check on every assignment (this is the 'backtracking' test):
      (a) the golfer is not already used in this week,
      (b) the golfer has NOT met any golfer already in this group in a
          previous week (pair tracking with bit masks).
    Group size and 'everyone exactly once per week' hold by construction:
    every week has exactly N slots split into G groups of S.

    Pair tracking: met[x] is an integer whose bit y is 1 if x and y have
    already been in the same group. Checking a candidate c against the
    current group is one AND operation: met[c] & group_mask == 0.

    Symmetry breaking (optional, ON by default). It only REMOVES branches
    that are mirror copies of other branches; it never removes a real
    solution and it does not change the DFS strategy:
      S1 the order of golfers inside a group does not matter
         -> golfers inside a group are placed in increasing order;
      S2 the order of groups inside a week does not matter
         -> each group starts with the smallest golfer still free that week;
      S3 golfer names are arbitrary -> week 1 is fixed to
         {1..S}, {S+1..2S}, ...  (any solution can be renamed into this);
      S4 the order of weeks (2..W) does not matter -> the partner of
         golfer 1 in week w must be larger than in week w-1.
    Without these rules the same schedule would be visited up to
    (S!)^G * G! times per week (plus N! and W! renamings).
    """

    def __init__(self, config: Config):
        config.check()
        self.cfg = config
        self.N = config.golfers
        self.G = config.groups
        self.S = config.group_size
        self.W = config.weeks
        self.total_slots = self.W * self.N
        self.rng = random.Random(config.seed)

        self.schedule: Schedule = [[[] for _ in range(self.G)] for _ in range(self.W)]
        self.met = [0] * (self.N + 1)         # pair tracker (bit masks), index 1..N
        self.used = [0] * self.W              # bit mask of golfers used in each week

        self.nodes = 0
        self.backtracks = 0
        self.max_depth = 0
        self._start = 0.0

    # ---- helpers -------------------------------------------------------
    def _check_limits(self) -> None:
        if self.cfg.max_nodes is not None and self.nodes >= self.cfg.max_nodes:
            raise _LimitReached
        if (self.cfg.time_limit is not None and (self.nodes & 1023) == 0
                and time.perf_counter() - self._start > self.cfg.time_limit):
            raise _LimitReached

    def _candidates(self, w: int, gi: int, j: int, k: int) -> List[int]:
        """Children of the current state, in the order DFS will try them."""
        group = self.schedule[w][gi]
        free = [x for x in range(1, self.N + 1) if not (self.used[w] >> x) & 1]

        if self.cfg.symmetry_breaking:
            if w == 0:                                   # S3: week 1 is fixed
                return [k + 1]
            if j == 0:                                   # S2: group starts with smallest free
                return free[:1]
            free = [x for x in free if x > group[-1]]    # S1: increasing inside group
            if gi == 0 and j == 1 and w >= 2:            # S4: order the weeks
                prev = self.schedule[w - 1][0][1]
                free = [x for x in free if x > prev]

        if self.cfg.value_order == "random":
            self.rng.shuffle(free)
        return free

    def _consistent(self, x: int, w: int, gi: int) -> bool:
        mask = 0
        for y in self.schedule[w][gi]:
            mask |= 1 << y
        return (self.met[x] & mask) == 0

    def _assign(self, x: int, w: int, gi: int) -> None:
        for y in self.schedule[w][gi]:
            self.met[x] |= 1 << y
            self.met[y] |= 1 << x
        self.schedule[w][gi].append(x)
        self.used[w] |= 1 << x

    def _unassign(self, x: int, w: int, gi: int) -> None:
        self.schedule[w][gi].pop()
        self.used[w] &= ~(1 << x)
        # Safe to clear: in a consistent state every pair has met at most once,
        # so this bit was set exactly by the matching _assign.
        for y in self.schedule[w][gi]:
            self.met[x] &= ~(1 << y)
            self.met[y] &= ~(1 << x)

    # ---- the recursive DFS ---------------------------------------------
    def _dfs(self, k: int) -> bool:
        if k > self.max_depth:
            self.max_depth = k
        if k == self.total_slots:                # goal test
            return True
        w, pos = divmod(k, self.N)
        gi, j = divmod(pos, self.S)

        for x in self._candidates(w, gi, j, k):
            if not self._consistent(x, w, gi):   # constraint check -> prune
                continue
            self.nodes += 1
            self._check_limits()
            self._assign(x, w, gi)
            if self._dfs(k + 1):                 # go DEEPER first
                return True
            self._unassign(x, w, gi)             # BACKTRACK
            self.backtracks += 1
        return False                             # dead end -> caller backtracks

    def solve(self) -> SearchResult:
        sys.setrecursionlimit(max(10_000, self.total_slots + 1_000))
        self._start = time.perf_counter()
        try:
            status = FOUND if self._dfs(0) else NO_SOLUTION
        except _LimitReached:
            status = LIMIT_REACHED
        elapsed = time.perf_counter() - self._start
        sched = None
        if status == FOUND:
            sched = [[sorted(g) for g in week] for week in self.schedule]
        return SearchResult(status, sched, self.nodes, self.backtracks, elapsed,
                            self.cfg, self.max_depth, self.max_depth // self.N)


def solve(groups: int, group_size: int, weeks: int, **kwargs) -> SearchResult:
    return SocialGolfersDFS(Config(groups=groups, group_size=group_size,
                                   weeks=weeks, **kwargs)).solve()


def find_max_weeks(groups: int, group_size: int, **kwargs) -> List[SearchResult]:
    """Run a separate DFS for W = 1, 2, 3, ... and stop at the first W that
    is not FOUND (or after the upper bound). Interpretation:
      - last FOUND = best number of weeks obtained;
      - if the next W ended with NO_SOLUTION, the maximum is PROVEN;
      - if it ended with LIMIT_REACHED, the maximum is UNKNOWN;
      - if FOUND reaches upper_bound_weeks, the maximum is proven by the bound."""
    results = []
    # W > upper bound is impossible by counting, so we never search it.
    for w in range(1, upper_bound_weeks(groups, group_size) + 1):
        r = solve(groups, group_size, w, **kwargs)
        results.append(r)
        if r.status != FOUND:
            break
    return results


# =============================================================================
# 5. OUTPUT
# =============================================================================

def format_schedule(schedule: Schedule) -> str:
    width = len(str(max(max(g) for g in schedule[0])))
    lines = []
    for w, week in enumerate(schedule, start=1):
        groups = "  ".join("[" + " ".join(f"{x:>{width}}" for x in g) + "]" for g in week)
        lines.append(f"Week {w:>2}: {groups}")
    return "\n".join(lines)


def print_problem_info(groups: int, group_size: int, weeks: Optional[int]) -> None:
    n = groups * group_size
    print(f"Instance          : N={n} golfers, G={groups} groups, S={group_size} per group")
    print(f"Pairs total       : C({n},2) = {math.comb(n, 2)}, "
          f"new pairs per week = G*C(S,2) = {groups * math.comb(group_size, 2)}")
    print(f"Upper bound       : floor((N-1)/(S-1)) = {upper_bound_weeks(groups, group_size)} weeks")
    print(f"Possible groups   : C(N,S) = {count_possible_groups(groups, group_size)}")
    p = count_week_partitions(groups, group_size)
    print(f"Weekly partitions : N!/((S!)^G G!) = {p} (~{sci(p)})")
    if weeks:
        print(f"{weeks}-week schedules (no pair constraint): P^W ~ "
              f"{sci(count_schedules(groups, group_size, weeks))}")


def print_result(r: SearchResult) -> None:
    c = r.config
    print(f"\nTarget weeks      : {c.weeks}")
    print(f"Symmetry breaking : {c.symmetry_breaking}   value order: {c.value_order}"
          + (f" (seed {c.seed})" if c.value_order == "random" else ""))
    print(f"Limits            : max_nodes={c.max_nodes}, time_limit={c.time_limit}s")
    print(f"Status            : {r.status}")
    print(f"Nodes generated   : {r.nodes:,}")
    print(f"Backtracks        : {r.backtracks:,}")
    print(f"Max depth (slots) : {r.max_depth} of {c.weeks * c.golfers}  "
          f"(complete weeks reached: {r.best_weeks})")
    print(f"Time              : {r.elapsed:.4f} s")
    ub = upper_bound_weeks(c.groups, c.group_size)
    if c.weeks > ub:
        print(f"NOTE: W={c.weeks} exceeds the counting bound {ub}; it is impossible "
              f"mathematically, whatever the search reports.")
    if r.status == FOUND:
        print("\nSchedule:\n" + format_schedule(r.schedule))
        errs = validate_schedule(r.schedule, c.groups, c.group_size, c.weeks)
        print("\nIndependent validation: " + ("VALID" if not errs else "INVALID " + str(errs)))
        print(f"NOTE: this shows that {c.weeks} weeks are POSSIBLE. It does not by itself "
              f"prove that {c.weeks} is the maximum.")
    elif r.status == NO_SOLUTION:
        print(f"\nThe complete search tree was explored: NO valid {c.weeks}-week "
              f"schedule exists (proof by exhaustive search).")
    else:
        print(f"\nSearch stopped by the limit before finishing. Nothing is proven: a "
              f"{c.weeks}-week schedule may or may not exist. Increase --max-nodes / "
              f"--time-limit or lower --weeks.")


def print_find_max(results: List[SearchResult]) -> None:
    c = results[0].config
    ub = upper_bound_weeks(c.groups, c.group_size)
    print(f"\n{'W':>3} {'status':<14} {'nodes':>14} {'backtracks':>14} {'time (s)':>10}")
    for r in results:
        print(f"{r.config.weeks:>3} {r.status:<14} {r.nodes:>14,} {r.backtracks:>14,} "
              f"{r.elapsed:>10.4f}")
    found = [r for r in results if r.status == FOUND]
    best = found[-1].config.weeks if found else 0
    last = results[-1]
    print(f"\nBest number of weeks found by DFS: {best}")
    if found and best >= ub:
        print(f"Conclusion: {best} = upper bound -> {best} is the PROVEN maximum.")
    elif last.status == NO_SOLUTION:
        print(f"Conclusion: {last.config.weeks} weeks proven impossible -> "
              f"maximum = {best} (PROVEN).")
    else:
        print(f"Conclusion: the search for {last.config.weeks} weeks hit the limit -> "
              f"maximum is at least {best}, but NOT proven (upper bound {ub}).")
    if found:
        print("\nBest schedule:\n" + format_schedule(found[-1].schedule))


def save_output(text: str, tag: str, rows: List[SearchResult]) -> str:
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, f"{tag}_{stamp}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    csv_path = os.path.join(folder, "runs.csv")
    new = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        if new:
            wr.writerow(["timestamp", "golfers", "groups", "size", "weeks", "symmetry",
                         "order", "seed", "max_nodes", "time_limit", "status", "nodes",
                         "backtracks", "seconds", "python"])
        for r in rows:
            c = r.config
            wr.writerow([stamp, c.golfers, c.groups, c.group_size, c.weeks,
                         c.symmetry_breaking, c.value_order, c.seed, c.max_nodes,
                         c.time_limit, r.status, r.nodes, r.backtracks,
                         f"{r.elapsed:.4f}", sys.version.split()[0]])
    for r in rows:
        if r.status == FOUND:
            c = r.config
            jpath = os.path.join(folder, f"schedule_{c.golfers}-{c.groups}-{c.group_size}"
                                         f"_W{c.weeks}_{stamp}.json")
            with open(jpath, "w", encoding="utf-8") as f:
                json.dump(r.schedule, f)
    return path


# =============================================================================
# 6. AUTOMATED TESTS   (python social_golfers.py --test)
# =============================================================================

class TestValidation(unittest.TestCase):
    # 4 golfers, 2 groups of 2: all 3 possible weeks, every pair exactly once
    VALID_4 = [[[1, 2], [3, 4]], [[1, 3], [2, 4]], [[1, 4], [2, 3]]]

    def test_valid_schedule(self):
        self.assertEqual(validate_schedule(self.VALID_4, 2, 2, 3), [])

    def test_repeated_pair(self):
        bad = [[[1, 2], [3, 4]], [[1, 2], [3, 4]]]
        errs = validate_schedule(bad, 2, 2)
        self.assertTrue(any("repeated" in e for e in errs))

    def test_missing_and_duplicate_golfer(self):
        bad = [[[1, 2], [3, 3]]]
        errs = " ".join(validate_schedule(bad, 2, 2))
        self.assertIn("more than once", errs)
        self.assertIn("missing", errs)

    def test_wrong_group_size(self):
        bad = [[[1, 2, 3], [4]]]
        self.assertTrue(any("expected size" in e for e in validate_schedule(bad, 2, 2)))

    def test_wrong_number_of_groups(self):
        bad = [[[1, 2], [3, 4], []]]
        self.assertTrue(any("groups" in e for e in validate_schedule(bad, 2, 2)))

    def test_invalid_golfer_number(self):
        bad = [[[1, 2], [3, 9]]]
        self.assertTrue(any("invalid golfer" in e for e in validate_schedule(bad, 2, 2)))

    def test_wrong_number_of_weeks(self):
        self.assertTrue(validate_schedule(self.VALID_4, 2, 2, weeks=4))

    def test_valid_32_golfer_week(self):
        week = [list(range(4 * i + 1, 4 * i + 5)) for i in range(8)]
        self.assertEqual(validate_schedule([week], 8, 4, 1), [])


class TestMath(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(count_possible_groups(8, 4), 35960)          # C(32,4)
        self.assertEqual(count_week_partitions(2, 2), 3)              # 4 golfers
        self.assertEqual(count_week_partitions(2, 4), 35)             # 8!/(4!^2 2!)
        self.assertEqual(count_week_partitions(3, 3), 280)            # 9 golfers
        self.assertEqual(count_week_partitions(8, 4), 59287247761257140625)
        self.assertEqual(upper_bound_weeks(8, 4), 10)
        self.assertEqual(upper_bound_weeks(2, 4), 2)

    def test_partition_count_by_enumeration(self):
        # brute-force check of the formula on a tiny instance (6 golfers, 3x2)
        import itertools
        seen = set()
        for perm in itertools.permutations(range(1, 7)):
            seen.add(frozenset(frozenset(perm[i:i + 2]) for i in range(0, 6, 2)))
        self.assertEqual(len(seen), count_week_partitions(3, 2))      # 15


class TestSolver(unittest.TestCase):
    def check_found(self, g, s, w, **kw):
        r = solve(g, s, w, **kw)
        self.assertEqual(r.status, FOUND)
        self.assertEqual(validate_schedule(r.schedule, g, s, w), [])
        return r

    def test_small_8_golfers_one_week(self):
        self.check_found(2, 4, 1)

    def test_small_8_golfers_two_weeks_impossible(self):
        # 2 groups of 4: after week 1 any new group of 4 would contain two
        # golfers from the same old group -> 2 weeks are impossible.
        self.assertEqual(solve(2, 4, 2).status, NO_SOLUTION)
        self.assertEqual(solve(2, 4, 2, symmetry_breaking=False).status, NO_SOLUTION)

    def test_4_golfers_max_3(self):
        self.check_found(2, 2, 3)
        self.assertEqual(solve(2, 2, 4).status, NO_SOLUTION)

    def test_9_golfers_kirkman_4_weeks(self):
        self.check_found(3, 3, 4)
        self.assertEqual(solve(3, 3, 5).status, NO_SOLUTION)

    def test_without_symmetry_breaking_same_answer(self):
        self.check_found(3, 3, 4, symmetry_breaking=False)

    def test_random_order_still_valid(self):
        for seed in range(3):
            self.check_found(3, 3, 3, symmetry_breaking=False,
                             value_order="random", seed=seed)

    def test_full_instance_one_week(self):
        self.check_found(8, 4, 1)

    def test_limit_is_reported(self):
        r = solve(8, 4, 10, max_nodes=1000, time_limit=None)
        self.assertEqual(r.status, LIMIT_REACHED)
        self.assertIsNone(r.schedule)

    def test_find_max_small_is_proven(self):
        res = find_max_weeks(2, 4)
        self.assertEqual([r.status for r in res], [FOUND, NO_SOLUTION])

    def test_bad_config(self):
        with self.assertRaises(ValueError):
            Config(groups=2, group_size=1).check()


def run_tests() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


# =============================================================================
# 7. COMMAND LINE
# =============================================================================

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Social Golfers Problem - DFS with Backtracking")
    p.add_argument("--groups", type=int, default=8, help="G, groups per week (default 8)")
    p.add_argument("--size", type=int, default=4, help="S, golfers per group (default 4)")
    p.add_argument("--weeks", type=int, default=5, help="W, target weeks (default 5)")
    p.add_argument("--max-nodes", type=int, default=10_000_000,
                   help="node limit, 0 = unlimited (default 10,000,000)")
    p.add_argument("--time-limit", type=float, default=60.0,
                   help="seconds per search, 0 = unlimited (default 60)")
    p.add_argument("--no-symmetry", action="store_true", help="disable symmetry breaking")
    p.add_argument("--random", action="store_true", help="random order of children")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--find-max", action="store_true", help="try W = 1, 2, ... until failure")
    p.add_argument("--save", action="store_true", help="save output into results/")
    p.add_argument("--test", action="store_true", help="run the automated tests")
    a = p.parse_args(argv)

    if a.test:
        return run_tests()

    kw = dict(max_nodes=a.max_nodes or None, time_limit=a.time_limit or None,
              symmetry_breaking=not a.no_symmetry,
              value_order="random" if a.random else "ascending", seed=a.seed)

    buf = io.StringIO()
    with redirect_stdout(buf):
        print("=" * 72)
        print("SOCIAL GOLFERS PROBLEM - DFS WITH BACKTRACKING")
        print(f"Run at {datetime.now():%Y-%m-%d %H:%M:%S}, Python {sys.version.split()[0]}")
        print("=" * 72)
        print_problem_info(a.groups, a.size, None if a.find_max else a.weeks)
        if a.find_max:
            rows = find_max_weeks(a.groups, a.size, **kw)
            print_find_max(rows)
        else:
            rows = [solve(a.groups, a.size, a.weeks, **kw)]
            print_result(rows[0])
    text = buf.getvalue()
    print(text, end="")

    if a.save:
        tag = (f"{a.groups * a.size}-{a.groups}-{a.size}_"
               + ("findmax" if a.find_max else f"W{a.weeks}")
               + ("_nosym" if a.no_symmetry else "")
               + (f"_rand{a.seed}" if a.random else ""))
        print(f"\nSaved to {save_output(text, tag, rows)} (and results/runs.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
