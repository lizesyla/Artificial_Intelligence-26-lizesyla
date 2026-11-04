"""
search_core.py - generic uninformed search that BUILDS AND RECORDS the search tree
=================================================================================

Used by the three problems of Part 4 (8-Puzzle, Missionaries and Cannibals,
Rotating Workforce Scheduling).

A problem only has to say:
    initial           the initial state
    actions(s)        the actions that can be applied in state s
    result(s, a)      the state after applying a in s
    is_goal(s)        goal test
    step_cost(s,a,t)  cost of one step (default 1)
    label(s)          a short text used when the tree is printed / drawn

Algorithms: BFS, DFS, DLS, IDDFS, UCS (all uninformed).
Repeated states: "graph" (never generate a state twice), "path" (no state twice
on the same root-to-node path), "none" (pure tree search).

The search is written as a generator of events, so that the command line
program and the visualizer use exactly the same code:
    ("iteration", L)                    IDDFS starts a new depth limit
    ("expand", node, children, pruned)  a node is expanded
    ("cutoff", node)                    depth limit reached (DLS / IDDFS)
    ("goal", node)
    ("end", result)
"""

from __future__ import annotations

import heapq
import itertools
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

FOUND = "FOUND"
NO_SOLUTION = "NO_SOLUTION"      # the whole (finite) space was explored
LIMIT_REACHED = "LIMIT_REACHED"  # node/time limit hit -> nothing proven
CUTOFF = "CUTOFF"                # DLS only: no solution within the depth limit

ALGORITHMS = ("bfs", "dfs", "dls", "iddfs", "ucs")


class Problem:
    name = "problem"
    initial: Any = None

    def actions(self, s):
        raise NotImplementedError

    def result(self, s, a):
        raise NotImplementedError

    def is_goal(self, s) -> bool:
        raise NotImplementedError

    def step_cost(self, s, a, t) -> float:
        return 1

    def label(self, s) -> str:
        return str(s)

    def action_label(self, a) -> str:
        return str(a)


@dataclass(eq=False)          # nodes are compared by identity, not by content
class Node:
    id: int
    state: Any
    parent: Optional["Node"]
    action: Any
    depth: int
    g: float
    order_generated: int
    order_expanded: Optional[int] = None
    status: str = "frontier"     # frontier / expanded / goal / duplicate / cutoff / deadend
    children: List["Node"] = field(default_factory=list)

    def path(self) -> List["Node"]:
        n, out = self, []
        while n is not None:
            out.append(n)
            n = n.parent
        return out[::-1]

    def on_path(self, state) -> bool:
        n = self
        while n is not None:
            if n.state == state:
                return True
            n = n.parent
        return False


@dataclass
class Config:
    algorithm: str = "bfs"
    repeated: str = "graph"           # graph / path / none
    depth_limit: Optional[int] = None  # for dls (required) and as a safety cap for dfs
    max_depth: int = 60               # IDDFS stops increasing L after this
    max_nodes: Optional[int] = 2_000_000
    time_limit: Optional[float] = 60.0
    record_limit: int = 20_000        # how many nodes are kept for drawing the tree


@dataclass
class Result:
    status: str
    solution: Optional[Node] = None
    generated: int = 0               # nodes created (root included)
    expanded: int = 0
    pruned: int = 0                  # children discarded as repeated states
    cutoffs: int = 0
    max_frontier: int = 0
    max_depth: int = 0
    elapsed: float = 0.0
    iterations: List[Dict] = field(default_factory=list)  # IDDFS per-iteration counts
    root: Optional[Node] = None      # root of the (last) recorded tree
    recorded: int = 0
    message: str = ""

    @property
    def path(self) -> List[Node]:
        return self.solution.path() if self.solution else []


class _Stop(Exception):
    pass


class Search:
    """One search run. Iterate over .events() or call .run()."""

    def __init__(self, problem: Problem, cfg: Config):
        if cfg.algorithm not in ALGORITHMS:
            raise ValueError(f"algorithm must be one of {ALGORITHMS}")
        if cfg.repeated not in ("graph", "path", "none"):
            raise ValueError("repeated must be graph, path or none")
        if cfg.algorithm == "dls" and cfg.depth_limit is None:
            raise ValueError("dls needs depth_limit")
        self.p, self.cfg = problem, cfg
        self.res = Result(NO_SOLUTION)
        self._ids = itertools.count()
        self._gen_order = itertools.count()
        self._exp_order = itertools.count()

    # ---------------------------------------------------------------- helpers
    def _new(self, state, parent, action) -> Node:
        depth = parent.depth + 1 if parent else 0
        g = parent.g + self.p.step_cost(parent.state, action, state) if parent else 0
        node = Node(next(self._ids), state, parent, action, depth, g, next(self._gen_order))
        self.res.generated += 1
        self.res.max_depth = max(self.res.max_depth, depth)
        if self.res.recorded < self.cfg.record_limit:
            self.res.recorded += 1
            if parent is not None:
                parent.children.append(node)
        return node

    def _limits(self):
        c, r = self.cfg, self.res
        if c.max_nodes is not None and r.generated >= c.max_nodes:
            raise _Stop(f"node limit {c.max_nodes:,}")
        if c.time_limit is not None and (r.generated & 1023) == 0 \
                and time.perf_counter() - self.start > c.time_limit:
            raise _Stop(f"time limit {c.time_limit}s")

    def _expand(self, node: Node, seen):
        """Generate the children of node. seen = set of reached states (graph search)."""
        node.order_expanded = next(self._exp_order)
        node.status = "expanded"
        self.res.expanded += 1
        children, pruned = [], []
        for a in self.p.actions(node.state):
            t = self.p.result(node.state, a)
            child = self._new(t, node, a)
            rep = self.cfg.repeated
            if (rep == "graph" and t in seen) or (rep == "path" and node.on_path(t)):
                child.status = "duplicate"
                self.res.pruned += 1
                pruned.append(child)
            else:
                if rep == "graph":
                    seen.add(t)
                children.append(child)
            self._limits()
        if not children and not pruned:
            node.status = "deadend" if not self.p.is_goal(node.state) else node.status
        return children, pruned

    # ---------------------------------------------------------------- algorithms
    def events(self):
        self.start = time.perf_counter()
        alg = self.cfg.algorithm
        try:
            if alg == "bfs":
                yield from self._bfs()
            elif alg in ("dfs", "dls"):
                limit = self.cfg.depth_limit
                yield from self._dls(limit, top=True)
            elif alg == "iddfs":
                yield from self._iddfs()
            else:
                yield from self._ucs()
        except _Stop as s:
            self.res.message = str(s)
            self.res.status = LIMIT_REACHED
        self.res.elapsed = time.perf_counter() - self.start
        yield ("end", self.res)

    def run(self) -> Result:
        for _ in self.events():
            pass
        return self.res

    def _root(self):
        root = self._new(self.p.initial, None, None)
        self.res.root = root
        return root

    def _bfs(self):
        root = self._root()
        if self.p.is_goal(root.state):
            root.status = "goal"
            self.res.solution, self.res.status = root, FOUND
            yield ("goal", root)
            return
        seen = {root.state}
        frontier = deque([root])
        self.frontier = frontier                   # visible to the visualizer
        while frontier:
            node = frontier.popleft()
            children, pruned = self._expand(node, seen)
            goal = None
            for ch in children:
                if self.p.is_goal(ch.state):          # goal test when generated
                    ch.status = "goal"
                    goal = ch
                    break
                frontier.append(ch)
            self.res.max_frontier = max(self.res.max_frontier, len(frontier))
            yield ("expand", node, children, pruned)
            if goal:
                self.res.solution, self.res.status = goal, FOUND
                yield ("goal", goal)
                return
        self.res.status = NO_SOLUTION

    def _ucs(self):
        root = self._root()
        best = {root.state: root}             # cheapest node found for each state
        tie = itertools.count()
        frontier = [(0, next(tie), root)]
        self.frontier = frontier
        while frontier:
            g, _, node = heapq.heappop(frontier)
            if node.status == "duplicate":            # a cheaper copy was found later
                continue
            if self.p.is_goal(node.state):            # goal test when EXPANDED (optimal)
                node.status = "goal"
                self.res.solution, self.res.status = node, FOUND
                yield ("goal", node)
                return
            node.order_expanded = next(self._exp_order)
            node.status = "expanded"
            self.res.expanded += 1
            children, pruned = [], []
            for a in self.p.actions(node.state):
                t = self.p.result(node.state, a)
                child = self._new(t, node, a)
                if self.cfg.repeated == "graph" and t in best and best[t].g <= child.g:
                    child.status = "duplicate"
                    self.res.pruned += 1
                    pruned.append(child)
                elif self.cfg.repeated == "path" and node.on_path(t):
                    child.status = "duplicate"
                    self.res.pruned += 1
                    pruned.append(child)
                else:
                    if self.cfg.repeated == "graph" and t in best:
                        best[t].status = "duplicate"     # the old, more expensive copy
                    best[t] = child
                    children.append(child)
                    heapq.heappush(frontier, (child.g, next(tie), child))
                self._limits()
            self.res.max_frontier = max(self.res.max_frontier, len(frontier))
            yield ("expand", node, children, pruned)
        self.res.status = NO_SOLUTION

    def _dls(self, limit, top=False):
        """Depth-first (stack) search with optional depth limit."""
        root = self._root()
        seen = {root.state}
        stack = [root]
        self.frontier = stack
        cut = False
        while stack:
            node = stack.pop()
            if self.p.is_goal(node.state):            # goal test when popped
                node.status = "goal"
                self.res.solution, self.res.status = node, FOUND
                yield ("goal", node)
                return
            if limit is not None and node.depth >= limit:
                node.status = "cutoff"
                self.res.cutoffs += 1
                cut = True
                yield ("cutoff", node)
                continue
            children, pruned = self._expand(node, seen)
            for ch in reversed(children):              # first action on top of the stack
                stack.append(ch)
            self.res.max_frontier = max(self.res.max_frontier, len(stack))
            yield ("expand", node, children, pruned)
        self.res.status = CUTOFF if cut else NO_SOLUTION

    def _iddfs(self):
        """Repeated DLS with L = 0, 1, 2, ...  Graph mode is not used inside a DLS
        (a 'seen' set would wrongly block states reachable by a shorter path);
        use 'path' (default advice) or 'none'."""
        L = 0
        while L <= self.cfg.max_depth:
            before = (self.res.generated, self.res.expanded, self.res.cutoffs)
            yield ("iteration", L)
            self.res.status = NO_SOLUTION
            self.res.recorded = 0                      # record the tree of THIS iteration
            yield from self._dls(L)
            self.res.iterations.append({
                "limit": L, "generated": self.res.generated - before[0],
                "expanded": self.res.expanded - before[1],
                "cutoffs": self.res.cutoffs - before[2], "status": self.res.status})
            if self.res.status in (FOUND, NO_SOLUTION):
                return
            L += 1
        self.res.status = CUTOFF
        self.res.message = f"no solution up to depth {self.cfg.max_depth}"


def solve(problem: Problem, cfg: Config) -> Result:
    if cfg.algorithm == "iddfs" and cfg.repeated == "graph":
        cfg.repeated = "path"
    return Search(problem, cfg).run()


# =============================================================================
# TREE OUTPUT: text, Graphviz DOT and a self-made SVG (no extra packages)
# =============================================================================

STATUS_COLORS = {"expanded": "#cfe2ff", "frontier": "#ffffff", "goal": "#b7f0b1",
                 "duplicate": "#eeeeee", "cutoff": "#e8d5f5", "deadend": "#ffd6d6"}


def select_nodes(res: Result, max_nodes: int):
    """The first max_nodes recorded nodes (generation order) + the solution path."""
    if res.root is None:
        return set()
    path = res.path if len(res.path) <= 300 else []   # a 60,000-step DFS path is not drawable
    for n in path[1:]:                     # make sure the solution path is drawable
        if n not in n.parent.children:
            n.parent.children.append(n)
    keep = set()
    todo = [res.root]
    allnodes = []
    while todo:
        n = todo.pop()
        allnodes.append(n)
        todo.extend(n.children)
    allnodes.sort(key=lambda n: n.order_generated)
    for n in allnodes[:max_nodes]:
        keep.add(n.id)
    for n in path:
        keep.add(n.id)
    # keep the tree connected
    for n in allnodes:
        if n.id in keep:
            p = n.parent
            while p is not None and p.id not in keep:
                keep.add(p.id)
                p = p.parent
    return keep


def text_tree(problem: Problem, res: Result, max_nodes: int = 60) -> str:
    keep = select_nodes(res, max_nodes)
    on_path = {n.id for n in res.path}
    lines = []

    def rec(n: Node, prefix: str, last: bool):
        tag = {"expanded": f"E{n.order_expanded}", "goal": "GOAL", "duplicate": "dup",
               "cutoff": "cut", "deadend": "dead", "frontier": "open"}[n.status]
        star = " *" if n.id in on_path else ""
        act = "" if n.action is None else f"--{problem.action_label(n.action)}--> "
        lab = problem.label(n.state).replace("\n", " | ")
        lines.append(f"{prefix}{'`-' if last else '|-'}{act}[{lab}] d={n.depth} {tag}{star}")
        kids = [c for c in n.children if c.id in keep]
        for i, c in enumerate(kids):
            rec(c, prefix + ("  " if last else "| "), i == len(kids) - 1)

    if res.root is not None:
        rec(res.root, "", True)
    hidden = res.generated - len(keep)
    if hidden > 0:
        lines.append(f"... {hidden:,} more generated nodes not shown")
    return "\n".join(lines)


def layout(res: Result, keep):
    """Tidy layout: leaves get consecutive x positions, parents are centered."""
    pos = {}
    nxt = [0]

    def rec(n: Node):
        kids = [c for c in n.children if c.id in keep]
        if not kids:
            pos[n.id] = (nxt[0], n.depth)
            nxt[0] += 1
            return
        for c in kids:
            rec(c)
        xs = [pos[c.id][0] for c in kids]
        pos[n.id] = ((min(xs) + max(xs)) / 2, n.depth)

    if res.root is not None:
        rec(res.root)
    return pos


def to_dot(problem: Problem, res: Result, max_nodes: int = 80) -> str:
    keep = select_nodes(res, max_nodes)
    on_path = {n.id for n in res.path}
    out = ["digraph SearchTree {", '  node [shape=box, style="rounded,filled", fontname="Courier"];']
    todo = [res.root] if res.root else []
    while todo:
        n = todo.pop()
        if n.id not in keep:
            continue
        lab = problem.label(n.state).replace("\n", "\\n")
        extra = f"\\n[{n.status}{'' if n.order_expanded is None else ' #' + str(n.order_expanded)}]"
        pen = ', penwidth=3, color="#1a7f37"' if n.id in on_path else ""
        out.append(f'  n{n.id} [label="{lab}{extra}", fillcolor="{STATUS_COLORS[n.status]}"{pen}];')
        for c in n.children:
            if c.id in keep:
                style = ', color="#1a7f37", penwidth=3' if c.id in on_path else ""
                out.append(f'  n{n.id} -> n{c.id} [label="{problem.action_label(c.action)}"{style}];')
                todo.append(c)
    out.append("}")
    return "\n".join(out)


def to_svg(problem: Problem, res: Result, max_nodes: int = 80, title: str = "") -> str:
    keep = select_nodes(res, max_nodes)
    pos = layout(res, keep)
    on_path = {n.id for n in res.path}
    nodes = {}
    todo = [res.root] if res.root else []
    while todo:
        n = todo.pop()
        if n.id in keep:
            nodes[n.id] = n
            todo.extend(n.children)
    lines_of = {i: problem.label(n.state).split("\n") for i, n in nodes.items()}
    maxlen = max((len(s) for ls in lines_of.values() for s in ls), default=4)
    maxl = max((len(ls) for ls in lines_of.values()), default=1)
    foot = max((len(f"d={n.depth} {n.status} #{n.order_expanded}") for n in nodes.values()),
               default=10)
    bw, bh = max(8 + 7.2 * maxlen, 8 + 5.6 * foot), 10 + 13 * maxl + 12
    gx, gy = bw + 16, bh + 46
    width = int(max((p[0] for p in pos.values()), default=0) * gx + bw + 40)
    height = int(max((p[1] for p in pos.values()), default=0) * gy + bh + 70)
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'font-family="Courier New, monospace" font-size="12">',
           f'<rect width="100%" height="100%" fill="white"/>',
           f'<text x="10" y="18" font-family="Helvetica" font-size="14">{esc(title)}</text>']
    cx = lambda i: 20 + pos[i][0] * gx + bw / 2
    cy = lambda i: 40 + pos[i][1] * gy
    for i, n in nodes.items():
        for c in n.children:
            if c.id in nodes:
                col, w = ("#1a7f37", 3) if c.id in on_path else ("#888", 1)
                x1, y1, x2, y2 = cx(i), cy(i) + bh, cx(c.id), cy(c.id)
                out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                           f'stroke="{col}" stroke-width="{w}"/>')
                out.append(f'<text x="{(x1 + x2) / 2 + 3:.1f}" y="{(y1 + y2) / 2:.1f}" '
                           f'font-size="10" fill="#555">{esc(problem.action_label(c.action))}</text>')
    for i, n in nodes.items():
        x, y = cx(i) - bw / 2, cy(i)
        stroke, sw = ("#1a7f37", 3) if i in on_path else ("#555", 1)
        dash = ' stroke-dasharray="4,3"' if n.status == "duplicate" else ""
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="5" '
                   f'fill="{STATUS_COLORS[n.status]}" stroke="{stroke}" stroke-width="{sw}"{dash}/>')
        for k, s in enumerate(lines_of[i]):
            out.append(f'<text x="{x + 5:.1f}" y="{y + 15 + 13 * k:.1f}">{esc(s)}</text>')
        tag = n.status + ("" if n.order_expanded is None else f" #{n.order_expanded}")
        out.append(f'<text x="{x + 5:.1f}" y="{y + bh - 5:.1f}" font-size="9" fill="#333">'
                   f'd={n.depth} {esc(tag)}</text>')
    out.append("</svg>")
    return "\n".join(out)
