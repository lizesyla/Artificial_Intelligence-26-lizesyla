"""
Rotating Workforce Scheduling (RWS) as a search problem
=======================================================
A cyclic weekly plan: a table with n rows (one row = one week of work for one
employee) and 7 columns (Mon..Sun). Every cell is a shift (D = day, N = night)
or '-' (day off). Employee 1 works row 1 in week 1, row 2 in week 2, ... and
after row n starts again from row 1, so the plan is read as ONE cyclic
sequence of 7n days: row 1, row 2, ..., row n, row 1, ...

Constraints of the instances used here (small versions of the RWS benchmark
by Musliu et al.):
  * demand: on day j exactly demand[s][j] employees work shift s
  * forbidden sequences: e.g. N directly followed by D (no rest)
  * every block of consecutive working days has length in [work_min, work_max]
  * every block of consecutive days off has length in [off_min, off_max]
  * at most max_same[s] consecutive shifts of type s
  (block constraints are cyclic: the end of row n continues into row 1)

Search formulation (one day = one level of the tree):
State : the columns already decided, (col_0, ..., col_{d-1}); every column is a
        tuple with one shift code per employee row.
Start : () - nothing decided.        Goal: 7 columns and every constraint holds.
Action: decide the next day: which rows work D and which work N, exactly
        meeting the demand of that day -> C(n, dD) * C(n - dD, dN) choices.
        Only choices that do not already break a constraint are returned
        (backtracking check); the 7th column must make the whole cyclic plan valid.
Cost  : 1 per day.  All solutions are at depth 7.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Tuple

from search_core import Problem

DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


@dataclass
class RWSInstance:
    n: int                                   # employees = rows
    demand: Dict[str, List[int]]             # shift -> 7 numbers
    forbidden: List[Tuple[str, str]] = field(default_factory=lambda: [("N", "D")])
    work_min: int = 2
    work_max: int = 5
    off_min: int = 1
    off_max: int = 3
    max_same: Dict[str, int] = field(default_factory=dict)


INSTANCES = {
    "tiny": RWSInstance(3, {"D": [1] * 7, "N": [1] * 7}, work_min=2, work_max=5,
                        off_min=1, off_max=2),
    "small": RWSInstance(4, {"D": [1] * 7, "N": [1] * 7}, work_min=2, work_max=4,
                         off_min=2, off_max=3, max_same={"N": 3}),
    "weekend": RWSInstance(5, {"D": [2, 2, 2, 2, 2, 1, 1], "N": [1, 1, 1, 1, 1, 1, 1]},
                           work_min=2, work_max=5, off_min=2, off_max=4, max_same={"N": 3}),
    "impossible": RWSInstance(3, {"D": [1] * 7, "N": [1] * 7}, work_min=2, work_max=3,
                              off_min=3, off_max=4),
}


def runs(seq: str):
    """Maximal blocks of the same kind: [(kind, start, length)], kind 'W' or '-'."""
    out = []
    i = 0
    while i < len(seq):
        kind = "-" if seq[i] == "-" else "W"
        j = i
        while j < len(seq) and ("-" if seq[j] == "-" else "W") == kind:
            j += 1
        out.append((kind, i, j - i))
        i = j
    return out


def same_runs(seq: str):
    out = []
    i = 0
    while i < len(seq):
        j = i
        while j < len(seq) and seq[j] == seq[i]:
            j += 1
        out.append((seq[i], i, j - i))
        i = j
    return out


class Workforce(Problem):
    name = "workforce"

    def __init__(self, inst: RWSInstance):
        self.inst = inst
        self.initial = ()
        self.shifts = list(inst.demand)

    # ------------------------------------------------------------- helpers
    def rows(self, cols) -> List[str]:
        return ["".join(col[i] for col in cols) for i in range(self.inst.n)]

    def partial_ok(self, cols) -> bool:
        """Checks that can already be decided with the first len(cols) days."""
        I = self.inst
        d = len(cols)
        for row in self.rows(cols):
            for a, b in zip(row, row[1:]):
                if (a, b) in I.forbidden:
                    return False
            for kind, start, length in runs(row):
                lo, hi = (I.work_min, I.work_max) if kind == "W" else (I.off_min, I.off_max)
                if length > hi:
                    return False
                inside = start > 0 and start + length < d        # cannot grow any more
                if inside and length < lo:
                    return False
            for s, start, length in same_runs(row):
                if s in I.max_same and length > I.max_same[s]:
                    return False
        return True

    def violations(self, cols) -> List[str]:
        """Full check of a complete plan as ONE cyclic sequence."""
        I = self.inst
        errs = []
        if len(cols) != 7:
            return [f"{len(cols)} of 7 days decided"]
        for j, col in enumerate(cols):
            if len(col) != I.n:
                errs.append(f"day {j}: {len(col)} rows")
            for s in self.shifts:
                if col.count(s) != I.demand[s][j]:
                    errs.append(f"{DAYS[j]}: {col.count(s)} x {s}, demand {I.demand[s][j]}")
        seq = "".join(self.rows(cols))
        L = len(seq)
        for k in range(L):
            if (seq[k], seq[(k + 1) % L]) in I.forbidden:
                errs.append(f"forbidden {seq[k]}->{seq[(k + 1) % L]} at day {k}")
        # rotate so that the sequence starts at a block boundary, then check blocks
        kinds = ["-" if ch == "-" else "W" for ch in seq]
        if len(set(kinds)) == 1:
            errs.append("no change between work and days off")
        else:
            k0 = next(k for k in range(L) if kinds[k] != kinds[k - 1])
            rot = seq[k0:] + seq[:k0]
            for kind, start, length in runs(rot):
                lo, hi = (I.work_min, I.work_max) if kind == "W" else (I.off_min, I.off_max)
                if not lo <= length <= hi:
                    errs.append(f"{'work' if kind == 'W' else 'off'} block of {length} days")
        if len(set(seq)) > 1:
            k1 = next(k for k in range(L) if seq[k] != seq[k - 1])
            rot2 = seq[k1:] + seq[:k1]
            for s, start, length in same_runs(rot2):
                if s in I.max_same and length > I.max_same[s]:
                    errs.append(f"{length} x {s} in a row")
        return errs

    # ------------------------------------------------------------- problem API
    def day_choices(self, j):
        I = self.inst
        n = I.n
        out = []
        dD = I.demand.get("D", [0] * 7)[j]
        dN = I.demand.get("N", [0] * 7)[j]
        for drows in combinations(range(n), dD):
            rest = [r for r in range(n) if r not in drows]
            for nrows in combinations(rest, dN):
                col = ["-"] * n
                for r in drows:
                    col[r] = "D"
                for r in nrows:
                    col[r] = "N"
                out.append(tuple(col))
        return out

    def actions(self, cols):
        d = len(cols)
        if d == 7:
            return []
        acts = []
        for col in self.day_choices(d):
            new = cols + (col,)
            if not self.partial_ok(new):
                continue
            if d == 6 and self.violations(new):
                continue
            acts.append(col)
        return acts

    def result(self, cols, a):
        return cols + (a,)

    def is_goal(self, cols):
        return len(cols) == 7 and not self.violations(cols)

    def label(self, cols):
        rows = self.rows(cols) if cols else [""] * self.inst.n
        return "\n".join(r.ljust(7, ".") for r in rows)

    def action_label(self, col):
        parts = []
        for s in self.shifts:
            who = [str(i + 1) for i, v in enumerate(col) if v == s]
            parts.append(f"{s}{''.join(who)}")
        return " ".join(parts)

    def format_plan(self, cols) -> str:
        lines = ["Week  " + " ".join(f"{d:>2}" for d in DAYS)]
        for i, row in enumerate(self.rows(cols)):
            lines.append(f"{i + 1:>4}  " + " ".join(f"{ch:>2}" for ch in row))
        return "\n".join(lines)
