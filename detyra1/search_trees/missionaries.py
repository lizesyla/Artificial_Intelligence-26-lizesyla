"""
Missionaries and Cannibals as a search problem
==============================================
M missionaries and C cannibals are on the LEFT bank with a boat for at most
K people. Everybody must reach the RIGHT bank. On either bank, if there is at
least one missionary there, the cannibals must not outnumber the missionaries.
The boat cannot cross empty.

State : (m, c, b) = missionaries on the left, cannibals on the left,
        b = 1 if the boat is on the left, 0 if on the right.
Start : (M, C, 1)        Goal: (0, 0, 0)
Action: (dm, dc) = people in the boat, 1 <= dm + dc <= K, dm >= dc or dm == 0
        (the boat itself must also be safe). Applied left->right if b = 1,
        right->left if b = 0.
Cost  : 1 per crossing.
"""

from __future__ import annotations

from search_core import Problem

INSTANCES = {
    "classic": (3, 3, 2),        # 11 crossings (known optimum)
    "boat3": (3, 3, 3),
    "five": (5, 5, 3),
    "impossible": (4, 4, 2),     # known to have no solution
}


class Missionaries(Problem):
    name = "missionaries"

    def __init__(self, M=3, C=3, K=2):
        self.M, self.C, self.K = M, C, K
        self.initial = (M, C, 1)
        self.goal = (0, 0, 0)
        # all boat loads, fewer people first, missionaries first
        self.loads = [(dm, n - dm) for n in range(1, K + 1) for dm in range(n, -1, -1)
                      if dm == 0 or dm >= n - dm]

    def safe(self, m, c) -> bool:
        if not (0 <= m <= self.M and 0 <= c <= self.C):
            return False
        left_ok = m == 0 or m >= c
        right_ok = (self.M - m) == 0 or (self.M - m) >= (self.C - c)
        return left_ok and right_ok

    def actions(self, s):
        m, c, b = s
        sign = -1 if b == 1 else 1
        return [(dm, dc) for dm, dc in self.loads if self.safe(m + sign * dm, c + sign * dc)]

    def result(self, s, a):
        m, c, b = s
        dm, dc = a
        sign = -1 if b == 1 else 1
        return (m + sign * dm, c + sign * dc, 1 - b)

    def is_goal(self, s):
        return s == self.goal

    def label(self, s):
        m, c, b = s
        left = "M" * m + "C" * c or "-"
        right = "M" * (self.M - m) + "C" * (self.C - c) or "-"
        return f"{left} {'B' if b else ' '}|{' ' if b else 'B'} {right}"

    def action_label(self, a):
        dm, dc = a
        return ("M" * dm + "C" * dc)

    def all_valid_states(self):
        return [(m, c, b) for m in range(self.M + 1) for c in range(self.C + 1) for b in (0, 1)
                if self.safe(m, c)]
