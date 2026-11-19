#!/usr/bin/env python3
"""
Search Trees - 8-Puzzle, Missionaries and Cannibals, Rotating Workforce Scheduling
==================================================================================

Course : Artificial Intelligence - Uninformed Search Techniques (Part 4)

Builds the search tree of each problem with an uninformed algorithm
(BFS, DFS, DLS, IDDFS, UCS), prints it, and saves it as text, Graphviz .dot and
.svg (the .svg opens in any web browser; no extra package is needed).

Usage (run inside the search_trees/ folder)
-------------------------------------------
    python search_trees.py --test
    python search_trees.py puzzle8 --instance medium --algorithm bfs --draw 40
    python search_trees.py puzzle8 --start "1 2 3 4 0 6 7 5 8" --algorithm iddfs
    python search_trees.py missionaries --algorithm bfs --save
    python search_trees.py missionaries --instance impossible --algorithm bfs
    python search_trees.py workforce --instance small --algorithm dfs --save
    python search_trees.py workforce --instance tiny --algorithm bfs --draw 30
    python search_trees.py --compare --save         # table for report.md
    python search_trees.py --list
    python search_trees.py --export-trees           # trees/*.svg used in report.md
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime

import eight_puzzle as ep
import missionaries as mc
import search_core as sc
import workforce as wf

PROBLEMS = ("puzzle8", "missionaries", "workforce")


def make_problem(kind: str, instance: str = None, start: str = None):
    if kind == "puzzle8":
        if start:
            return ep.EightPuzzle(ep.parse(start)), "custom"
        instance = instance or "medium"
        return ep.EightPuzzle(ep.parse(ep.INSTANCES[instance][0])), instance
    if kind == "missionaries":
        instance = instance or "classic"
        return mc.Missionaries(*mc.INSTANCES[instance]), instance
    if kind == "workforce":
        instance = instance or "small"
        return wf.Workforce(wf.INSTANCES[instance]), instance
    raise ValueError(f"unknown problem {kind}")


def describe(problem) -> str:
    if isinstance(problem, ep.EightPuzzle):
        s = problem.initial
        return (f"8-puzzle start {' '.join(map(str, s))}, goal {' '.join(map(str, problem.goal))}, "
                f"inversions {ep.inversions(s)} -> {'solvable' if ep.solvable(s) else 'NOT solvable'}")
    if isinstance(problem, mc.Missionaries):
        return (f"Missionaries & Cannibals: M={problem.M}, C={problem.C}, boat={problem.K}, "
                f"{len(problem.all_valid_states())} valid states (m, c, boat)")
    I = problem.inst
    return (f"Rotating workforce: {I.n} employees x 7 days, demand {I.demand}, forbidden "
            f"{I.forbidden}, work blocks {I.work_min}-{I.work_max}, off blocks "
            f"{I.off_min}-{I.off_max}, max same {I.max_same}")


def explain(res: sc.Result) -> str:
    if res.status == sc.FOUND:
        return f"solution found, {len(res.path) - 1} steps"
    if res.status == sc.NO_SOLUTION:
        return "the whole reachable space was explored: NO solution exists"
    if res.status == sc.CUTOFF:
        return "no solution within the depth limit (a deeper one may exist)"
    return f"stopped by a limit ({res.message}); nothing is proven"


def print_run(problem, inst_name, cfg, res, draw):
    print(describe(problem))
    print(f"Algorithm         : {cfg.algorithm.upper()}, repeated states = {cfg.repeated}"
          + (f", depth limit = {cfg.depth_limit}" if cfg.depth_limit is not None else ""))
    print(f"Status            : {res.status} - {explain(res)}")
    print(f"Nodes generated   : {res.generated:,}")
    print(f"Nodes expanded    : {res.expanded:,}")
    print(f"Pruned duplicates : {res.pruned:,}")
    if cfg.algorithm in ("dls", "iddfs", "dfs"):
        print(f"Cutoffs           : {res.cutoffs:,}")
    print(f"Max frontier      : {res.max_frontier:,}")
    print(f"Max depth         : {res.max_depth}")
    print(f"Time              : {res.elapsed:.4f} s")
    if res.iterations:
        print("IDDFS iterations  : " + ", ".join(
            f"L={it['limit']}:{it['generated']}" for it in res.iterations))
    if res.path:
        print("\nSolution path:")
        for k, n in enumerate(res.path):
            act = "start" if n.action is None else problem.action_label(n.action)
            print(f"  step {k:>2} ({act}):")
            for line in problem.label(n.state).split("\n"):
                print("      " + line)
        if isinstance(problem, wf.Workforce):
            print("\nPlan:\n" + problem.format_plan(res.solution.state))
            v = problem.violations(res.solution.state)
            print("Independent validation: " + ("VALID" if not v else f"INVALID {v}"))
    if draw:
        print(f"\nSearch tree (first {draw} generated nodes + solution path; "
              f"E# = expansion order, * = on the solution path):")
        print(sc.text_tree(problem, res, draw))


def results_dir():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(d, exist_ok=True)
    return d


def save(text, tag, rows, problem=None, res=None, draw=60, title=""):
    folder = results_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(folder, f"{tag}_{stamp}")
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write(text)
    if problem is not None and res is not None and res.root is not None:
        with open(base + ".dot", "w", encoding="utf-8") as f:
            f.write(sc.to_dot(problem, res, draw))
        with open(base + ".svg", "w", encoding="utf-8") as f:
            f.write(sc.to_svg(problem, res, draw, title))
    cpath = os.path.join(folder, "runs.csv")
    new = not os.path.exists(cpath)
    with open(cpath, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "problem", "instance", "algorithm", "repeated", "depth_limit",
                        "status", "solution_length", "generated", "expanded", "pruned",
                        "cutoffs", "max_frontier", "max_depth", "seconds", "message", "python"])
        for prob, inst, cfg, r in rows:
            w.writerow([stamp, prob, inst, cfg.algorithm, cfg.repeated, cfg.depth_limit, r.status,
                        len(r.path) - 1 if r.path else "", r.generated, r.expanded, r.pruned,
                        r.cutoffs, r.max_frontier, r.max_depth, f"{r.elapsed:.4f}", r.message,
                        sys.version.split()[0]])
    return base


# =============================================================================
# AUTOMATED TESTS
# =============================================================================

class TestEightPuzzle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dist = ep.distances_from_goal()

    def test_state_space_size(self):
        self.assertEqual(len(self.dist), 181_440)          # 9!/2
        self.assertEqual(max(self.dist.values()), 31)

    def test_instances_have_declared_depth(self):
        for name, (s, depth) in ep.INSTANCES.items():
            st = ep.parse(s)
            self.assertEqual(self.dist.get(st), depth, name)
            self.assertEqual(ep.solvable(st), depth is not None)

    def test_bfs_and_ucs_are_optimal(self):
        for name in ("easy", "medium", "hard", "veryhard"):
            p = ep.EightPuzzle(ep.parse(ep.INSTANCES[name][0]))
            for alg in ("bfs", "ucs"):
                r = sc.solve(p, sc.Config(alg, "graph"))
                self.assertEqual(len(r.path) - 1, ep.INSTANCES[name][1])

    def test_iddfs_optimal_small(self):
        for name in ("easy", "medium", "hard"):
            p = ep.EightPuzzle(ep.parse(ep.INSTANCES[name][0]))
            r = sc.solve(p, sc.Config("iddfs", "path"))
            self.assertEqual(len(r.path) - 1, ep.INSTANCES[name][1])
            self.assertEqual([it["limit"] for it in r.iterations],
                             list(range(ep.INSTANCES[name][1] + 1)))

    def test_solution_path_is_legal(self):
        p = ep.EightPuzzle(ep.parse(ep.INSTANCES["hard"][0]))
        r = sc.solve(p, sc.Config("dfs", "graph"))
        s = p.initial
        for n in r.path[1:]:
            self.assertIn(n.action, p.actions(s))
            s = p.result(s, n.action)
        self.assertEqual(s, ep.GOAL)

    def test_unsolvable(self):
        p = ep.EightPuzzle(ep.parse(ep.INSTANCES["unsolvable"][0]))
        r = sc.solve(p, sc.Config("bfs", "graph"))
        self.assertEqual(r.status, sc.NO_SOLUTION)
        self.assertEqual(r.expanded, 181_440)              # the other half of the 9! states


class TestMissionaries(unittest.TestCase):
    def test_classic_11_crossings(self):
        p = mc.Missionaries(3, 3, 2)
        self.assertEqual(len(p.all_valid_states()), 20)
        for alg, rep in (("bfs", "graph"), ("bfs", "none"), ("iddfs", "path"), ("ucs", "graph")):
            r = sc.solve(p, sc.Config(alg, rep))
            self.assertEqual(len(r.path) - 1, 11, (alg, rep))

    def test_every_state_on_path_is_safe(self):
        p = mc.Missionaries(3, 3, 2)
        r = sc.solve(p, sc.Config("dfs", "graph"))
        for n in r.path:
            m, c, b = n.state
            self.assertTrue(p.safe(m, c))

    def test_impossible(self):
        r = sc.solve(mc.Missionaries(4, 4, 2), sc.Config("bfs", "graph"))
        self.assertEqual(r.status, sc.NO_SOLUTION)

    def test_tree_search_needs_limit(self):
        # pure tree DFS goes back and forth forever -> only a limit stops it
        r = sc.solve(mc.Missionaries(4, 4, 2), sc.Config("dfs", "none", max_nodes=5000))
        self.assertEqual(r.status, sc.LIMIT_REACHED)


class TestWorkforce(unittest.TestCase):
    def test_instances(self):
        for name, expected in (("tiny", sc.FOUND), ("small", sc.FOUND),
                               ("weekend", sc.FOUND), ("impossible", sc.NO_SOLUTION)):
            p = wf.Workforce(wf.INSTANCES[name])
            r = sc.solve(p, sc.Config("dfs", "graph"))
            self.assertEqual(r.status, expected, name)
            if r.solution:
                self.assertEqual(p.violations(r.solution.state), [])
                self.assertEqual(len(r.path) - 1, 7)

    def test_bfs_same_answer_set(self):
        p = wf.Workforce(wf.INSTANCES["tiny"])
        rb = sc.solve(p, sc.Config("bfs", "graph"))
        self.assertEqual(rb.status, sc.FOUND)
        self.assertEqual(p.violations(rb.solution.state), [])

    def test_violations_detects_errors(self):
        p = wf.Workforce(wf.INSTANCES["tiny"])
        good = sc.solve(p, sc.Config("dfs", "graph")).solution.state
        bad = list(good)
        bad[0] = tuple(reversed(bad[0]))               # same demand, other rows
        bad2 = [("D", "D", "D")] + list(good[1:])      # demand broken
        self.assertTrue(p.violations(tuple(bad2)))
        self.assertTrue(p.violations(good[:6]))
        self.assertIsInstance(p.violations(tuple(bad)), list)

    def test_runs(self):
        self.assertEqual(wf.runs("DD-N"), [("W", 0, 2), ("-", 2, 1), ("W", 3, 1)])


class TestTreeOutput(unittest.TestCase):
    def test_outputs(self):
        p = mc.Missionaries(3, 3, 2)
        r = sc.solve(p, sc.Config("bfs", "graph"))
        t = sc.text_tree(p, r, 30)
        self.assertIn("GOAL", t)
        self.assertTrue(sc.to_dot(p, r, 30).startswith("digraph"))
        self.assertTrue(sc.to_svg(p, r, 30).startswith("<svg"))

    def test_bad_config(self):
        with self.assertRaises(ValueError):
            sc.Search(mc.Missionaries(), sc.Config("dls"))


def run_tests() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


# =============================================================================
# COMMAND LINE
# =============================================================================

TREE_JOBS = [
    # file name, problem, instance, algorithm, repeated, nodes drawn, title
    ("missionaries_bfs_graph", "missionaries", "classic", "bfs", "graph", 60,
     "Missionaries & Cannibals (3,3,2) - BFS, graph search"),
    ("missionaries_bfs_tree", "missionaries", "classic", "bfs", "none", 40,
     "Missionaries & Cannibals - BFS, pure tree search (first 40 nodes)"),
    ("missionaries_dfs_graph", "missionaries", "classic", "dfs", "graph", 60,
     "Missionaries & Cannibals - DFS, graph search"),
    ("puzzle8_easy_bfs", "puzzle8", "easy", "bfs", "graph", 40, "8-puzzle easy - BFS"),
    ("puzzle8_medium_bfs", "puzzle8", "medium", "bfs", "graph", 45,
     "8-puzzle medium - BFS (first 45 nodes + solution path)"),
    ("puzzle8_easy_iddfs", "puzzle8", "easy", "iddfs", "path", 40,
     "8-puzzle easy - IDDFS, last iteration (L = 2)"),
    ("puzzle8_easy_dfs", "puzzle8", "easy", "dfs", "graph", 30,
     "8-puzzle easy - DFS, graph search (first 30 nodes; the path found has 64,328 moves)"),
    ("puzzle8_easy_dls4", "puzzle8", "easy", "dls", "path", 40,
     "8-puzzle easy - DLS with depth limit 4"),
    ("workforce_tiny_dfs", "workforce", "tiny", "dfs", "graph", 40,
     "Rotating Workforce (tiny) - DFS with backtracking"),
    ("workforce_tiny_bfs", "workforce", "tiny", "bfs", "graph", 40,
     "Rotating Workforce (tiny) - BFS (first 40 nodes + solution path)"),
]


def export_trees() -> int:
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trees")
    os.makedirs(folder, exist_ok=True)
    for fname, kind, inst, alg, rep, draw, title in TREE_JOBS:
        problem, _ = make_problem(kind, inst)
        r = sc.solve(problem, sc.Config(alg, rep, depth_limit=4 if alg == "dls" else None))
        for ext, text in (("svg", sc.to_svg(problem, r, draw, title)),
                          ("dot", sc.to_dot(problem, r, draw)),
                          ("txt", sc.text_tree(problem, r, draw))):
            with open(os.path.join(folder, f"{fname}.{ext}"), "w", encoding="utf-8") as f:
                f.write(text)
        print(f"{fname:<26} {r.status:<12} generated={r.generated:<6} "
              f"path={len(r.path) - 1 if r.path else '-'}")
    print(f"Written to {folder}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Search trees for three problems")
    ap.add_argument("problem", nargs="?", choices=PROBLEMS)
    ap.add_argument("--instance")
    ap.add_argument("--start", help="8-puzzle start, e.g. '1 2 3 4 0 6 7 5 8'")
    ap.add_argument("--algorithm", choices=sc.ALGORITHMS, default="bfs")
    ap.add_argument("--repeated", choices=["graph", "path", "none"], default=None,
                    help="default: graph (path for iddfs)")
    ap.add_argument("--depth-limit", type=int)
    ap.add_argument("--max-nodes", type=int, default=2_000_000, help="0 = unlimited")
    ap.add_argument("--time-limit", type=float, default=60.0, help="0 = unlimited")
    ap.add_argument("--draw", type=int, default=40, help="nodes shown in the printed tree")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--export-trees", action="store_true",
                    help="write the tree pictures used in report.md into trees/")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args(argv)

    if a.test:
        return run_tests()
    if a.export_trees:
        return export_trees()
    if a.list:
        print("puzzle8      :", ", ".join(f"{k} (depth {d})" for k, (s, d) in ep.INSTANCES.items()))
        print("missionaries :", ", ".join(f"{k} {v}" for k, v in mc.INSTANCES.items()))
        print("workforce    :", ", ".join(wf.INSTANCES))
        return 0

    lim = dict(max_nodes=a.max_nodes or None, time_limit=a.time_limit or None)
    buf = io.StringIO()
    rows = []
    last = None
    with redirect_stdout(buf):
        print("=" * 72)
        print("SEARCH TREES - UNINFORMED SEARCH")
        print(f"Run at {datetime.now():%Y-%m-%d %H:%M:%S}, Python {sys.version.split()[0]}")
        print("=" * 72)
        if a.compare:
            jobs = []
            for inst in ("easy", "medium", "hard", "veryhard", "hardest", "unsolvable"):
                for alg, rep in (("bfs", "graph"), ("ucs", "graph"), ("dfs", "graph"),
                                 ("iddfs", "path"), ("bfs", "none")):
                    jobs.append(("puzzle8", inst, alg, rep))
            for inst in mc.INSTANCES:
                for alg, rep in (("bfs", "graph"), ("ucs", "graph"), ("dfs", "graph"),
                                 ("iddfs", "path"), ("bfs", "none"), ("dfs", "none")):
                    jobs.append(("missionaries", inst, alg, rep))
            for inst in wf.INSTANCES:
                for alg, rep in (("bfs", "graph"), ("dfs", "graph"), ("iddfs", "path"),
                                 ("ucs", "graph")):
                    jobs.append(("workforce", inst, alg, rep))
            print(f"{'problem':<13}{'instance':<11}{'alg':<6}{'repeated':<9}{'status':<14}"
                  f"{'len':>5}{'generated':>12}{'expanded':>11}{'max frontier':>13}{'time s':>9}")
            for kind, inst, alg, rep in jobs:
                problem, _ = make_problem(kind, inst)
                cfg = sc.Config(alg, rep, **lim)
                r = sc.solve(problem, cfg)
                rows.append((kind, inst, cfg, r))
                print(f"{kind:<13}{inst:<11}{alg:<6}{rep:<9}{r.status:<14}"
                      f"{(len(r.path) - 1) if r.path else '-':>5}{r.generated:>12,}"
                      f"{r.expanded:>11,}{r.max_frontier:>13,}{r.elapsed:>9.3f}")
        else:
            if not a.problem:
                ap.error("choose a problem (puzzle8, missionaries, workforce) or --compare")
            problem, inst = make_problem(a.problem, a.instance, a.start)
            rep = a.repeated or ("path" if a.algorithm == "iddfs" else "graph")
            cfg = sc.Config(a.algorithm, rep, depth_limit=a.depth_limit, **lim)
            r = sc.solve(problem, cfg)
            rows.append((a.problem, inst, cfg, r))
            last = (problem, r, f"{a.problem} / {inst} / {a.algorithm.upper()} ({rep})")
            print_run(problem, inst, cfg, r, a.draw)
    text = buf.getvalue()
    print(text, end="")
    if a.save:
        if a.compare:
            base = save(text, "compare", rows)
        else:
            problem, r, title = last
            base = save(text, f"{a.problem}_{rows[0][1]}_{a.algorithm}", rows, problem, r,
                        a.draw, title)
        print(f"\nSaved to {base}.txt" + ("" if a.compare else " (+ .dot and .svg tree)")
              + " and results/runs.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
