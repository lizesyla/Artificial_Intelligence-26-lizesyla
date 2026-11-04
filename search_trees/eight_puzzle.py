"""
8-Puzzle as a search problem
============================
State : tuple of 9 numbers read row by row, 0 = blank.  Example (1,2,3,4,0,6,7,5,8)
Goal  : (1,2,3,4,5,6,7,8,0)
Action: move the BLANK Up / Down / Left / Right (tried in this order)
Cost  : 1 per move
Only half of the 9! = 362,880 arrangements can reach the goal: 181,440 states.
A state is solvable iff its number of inversions (ignoring the blank) is even.
"""

from __future__ import annotations

from search_core import Problem

GOAL = (1, 2, 3, 4, 5, 6, 7, 8, 0)
MOVES = {"Up": -3, "Down": 3, "Left": -1, "Right": 1}

# start states (optimal solution length was computed with BFS, see the tests)
INSTANCES = {
    "easy": ("1 2 3 4 5 6 0 7 8", 2),
    "medium": ("1 3 6 4 5 2 0 7 8", 8),
    "hard": ("5 2 6 7 1 4 0 3 8", 16),
    "veryhard": ("7 2 5 4 0 8 6 3 1", 24),
    "hardest": ("8 6 7 2 5 4 3 0 1", 31),     # one of the two hardest 8-puzzle states
    "unsolvable": ("1 2 3 4 5 6 8 7 0", None),
}


def parse(text: str):
    vals = tuple(int(x) for x in text.replace(",", " ").split())
    if sorted(vals) != list(range(9)):
        raise ValueError("an 8-puzzle state needs the numbers 0..8 exactly once")
    return vals


def inversions(s) -> int:
    t = [x for x in s if x]
    return sum(1 for i in range(len(t)) for j in range(i + 1, len(t)) if t[i] > t[j])


def solvable(s) -> bool:
    return inversions(s) % 2 == inversions(GOAL) % 2


class EightPuzzle(Problem):
    name = "8-puzzle"

    def __init__(self, start, goal=GOAL):
        self.initial = tuple(start)
        self.goal = tuple(goal)

    def actions(self, s):
        b = s.index(0)
        r, c = divmod(b, 3)
        acts = []
        if r > 0:
            acts.append("Up")
        if r < 2:
            acts.append("Down")
        if c > 0:
            acts.append("Left")
        if c < 2:
            acts.append("Right")
        return acts

    def result(self, s, a):
        b = s.index(0)
        t = b + MOVES[a]
        lst = list(s)
        lst[b], lst[t] = lst[t], lst[b]
        return tuple(lst)

    def is_goal(self, s):
        return s == self.goal

    def label(self, s):
        return "\n".join(" ".join(str(x) if x else "_" for x in s[r * 3:r * 3 + 3]) for r in range(3))

    def action_label(self, a):
        return {"Up": "U", "Down": "D", "Left": "L", "Right": "R"}[a]


def distances_from_goal():
    """BFS over the whole reachable space (moves are reversible). Used by tests
    and the report to know the exact optimal depth of every state."""
    from collections import deque
    p = EightPuzzle(GOAL)
    dist = {GOAL: 0}
    q = deque([GOAL])
    while q:
        s = q.popleft()
        for a in p.actions(s):
            t = p.result(s, a)
            if t not in dist:
                dist[t] = dist[s] + 1
                q.append(t)
    return dist
