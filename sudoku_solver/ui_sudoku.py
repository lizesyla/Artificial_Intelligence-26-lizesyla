#!/usr/bin/env python3
"""
Sudoku - visualizer for BFS with Backtracking (tkinter)
=======================================================

    python ui_sudoku.py              # open the window
    python ui_sudoku.py --selftest   # check: visual search == sudoku_solver.solve()

The window does not contain a second algorithm: it uses expand() from
sudoku_solver.py (the same successor function, the same pruning and the same
cell order) and only runs the queue loop one expansion at a time. The self
test checks that every counter (generated, expanded, dead ends, max frontier,
states per depth, solutions) is identical to solve().

What you see
  * Big grid   : the state that is being EXPANDED now.
                 black = given, blue = digit placed by the search,
                 yellow cell = the cell chosen for expansion, small digits =
                 its legal values (= the children). A red cell = dead end.
  * Queue      : the next states waiting in the FIFO queue (BFS) or on the
                 stack (DFS), with their depth (blue digits = placed by search).
  * Bar chart  : how many states were generated at each depth. BFS fills it
                 level by level from left to right - that is breadth-first.
"""

from __future__ import annotations

import math
import sys
import time
from collections import deque

import sudoku_solver as sv

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError:
    tk = None


# =============================================================================
# 1. STEP-BY-STEP SEARCH (same rules as sudoku_solver._bfs / _dfs)
# =============================================================================

class SteppingSearch:
    def __init__(self, puzzle: bytes, board: sv.Board, cfg: sv.Config):
        self.puzzle, self.board, self.cfg = puzzle, board, cfg
        self.empty = puzzle.count(0)
        self.res = sv.Result(sv.NO_SOLUTION, [], empty_cells=self.empty,
                             level_sizes=[0] * (self.empty + 1))
        self.res.generated = 1
        self.res.level_sizes[0] = 1
        self.frontier = deque([(puzzle, 0)])
        self.start = 0.0
        self.finished = False

    def steps(self):
        """One event per expansion:
        ("expand", state, depth, cell, digits, n_children_queued)
        ("end", status)"""
        cfg, res, board = self.cfg, self.res, self.board
        self.start = time.perf_counter()
        errs = sv.validate_puzzle(self.puzzle, board)
        if errs:
            self.res = res = sv.Result(sv.INVALID, [], stop_reason="; ".join(errs))
            self.finished = True
            yield ("end", res.status)
            return
        if self.empty == 0:
            res.status, res.solutions, res.first_solution_after = sv.SOLVED, [self.puzzle], 1
            self.finished = True
            yield ("end", res.status)
            return
        bfs = cfg.algorithm == "bfs"
        q = self.frontier
        try:
            while q:
                state, depth = q.popleft() if bfs else q.pop()
                res.expanded += 1
                cell, digits, children = sv.expand(state, board, cfg.order)
                if not children:
                    res.dead_ends += 1
                stop = False
                queued = 0
                for child in (children if bfs else reversed(children)):
                    res.generated += 1
                    res.level_sizes[depth + 1] += 1
                    res.max_depth = max(res.max_depth, depth + 1)
                    if depth + 1 == self.empty:
                        if sv._record_solution(child, cfg, res):
                            stop = True
                            break
                    else:
                        q.append((child, depth + 1))
                        queued += 1
                    if len(q) > res.max_frontier:
                        res.max_frontier = len(q)
                    sv._check(cfg, res, len(q), self.start)
                yield ("expand", state, depth, cell, digits, queued)
                if stop:
                    break
        except sv._Stop as s:
            res.stop_reason = str(s)
            res.status = sv.LIMIT_REACHED
        if res.solutions:
            res.status = sv.SOLVED
        self.finished = True
        yield ("end", res.status)

    def run_all(self):
        for _ in self.steps():
            pass
        return self.res


def selftest() -> int:
    ok = True
    cases = []
    for name in ("easy", "medium", "hard", "easy4", "empty4", "easy6", "hard6", "wiki9",
                 "escargot9", "nosol9", "invalid9"):
        for alg in ("bfs", "dfs"):
            for order in ("first", "mrv"):
                for fa in (False, True):
                    cases.append((name, sv.Config(alg, order, find_all=fa, time_limit=None)))
    cases.append(("clue17", sv.Config("bfs", "first", max_nodes=30_000, time_limit=None)))
    cases.append(("clue17", sv.Config("bfs", "first", max_frontier=5_000, time_limit=None)))
    for name, cfg in cases:
        box, grid, _ = sv.PUZZLES[name]
        board = sv.Board(*sv.parse_box(box))
        p = sv.parse_grid(grid, board)
        ref = sv.solve(p, board, cfg)
        vis = SteppingSearch(p, board, cfg).run_all()
        keys = ("status", "generated", "expanded", "dead_ends", "max_frontier", "max_depth",
                "level_sizes", "solutions", "first_solution_after")
        same = all(getattr(ref, k) == getattr(vis, k) for k in keys)
        ok &= same
        if not same:
            print("FAIL", name, cfg, {k: (getattr(ref, k), getattr(vis, k)) for k in keys
                                      if getattr(ref, k) != getattr(vis, k)})
    print(f"{len(cases)} cases compared.  SELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


# =============================================================================
# 2. WINDOW
# =============================================================================

SPEEDS = [(1000, 1), (500, 1), (250, 1), (120, 1), (50, 1), (15, 1), (15, 10),
          (15, 100), (10, 1_000), (5, 10_000)]
VERBOSE_MAX = 10
GIVEN, PLACED, CHOSEN, DEAD, NEW, SOLVED_BG = "#000000", "#1f5fbf", "#fff2a8", "#ffb3b3", "#ffcf99", "#d8f5d0"


class App:
    def __init__(self, root):
        self.root = root
        root.title("Sudoku - BFS with Backtracking (visualizer)")
        root.geometry("1360x880")
        root.minsize(1100, 700)
        self.after_id = None
        self.running = False
        self.engine = None
        self._controls()
        self._body()
        self.v_puzzle.set("easy")
        self.reset()
        root.protocol("WM_DELETE_WINDOW", self.close)

    # ------------------------------------------------------------ layout
    def _controls(self):
        bar = ttk.Frame(self.root, padding=(8, 6))
        bar.pack(fill="x")
        r0 = ttk.Frame(bar)
        r0.pack(fill="x")
        ttk.Label(r0, text="Puzzle:").pack(side="left")
        self.v_puzzle = tk.StringVar()
        cb = ttk.Combobox(r0, textvariable=self.v_puzzle, values=list(sv.PUZZLES) + ["custom"],
                          width=11, state="readonly")
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.reset())
        self.l_desc = ttk.Label(r0, width=44, foreground="#555")
        self.l_desc.pack(side="left", padx=(4, 10))
        ttk.Label(r0, text="Custom grid:").pack(side="left")
        self.v_custom = tk.StringVar(value="." * 81)
        ttk.Entry(r0, textvariable=self.v_custom, width=40).pack(side="left", padx=4)
        ttk.Label(r0, text="box").pack(side="left")
        self.v_box = tk.StringVar(value="3x3")
        ttk.Combobox(r0, textvariable=self.v_box, values=["2x2", "2x3", "3x3"], width=4,
                     state="readonly").pack(side="left", padx=4)
        ttk.Button(r0, text="Apply / Reset", command=self.reset).pack(side="left", padx=(10, 0))
        ttk.Label(r0, text="   New puzzle:").pack(side="left")
        self.v_gen = tk.StringVar(value="medium")
        ttk.Combobox(r0, textvariable=self.v_gen, values=["easy", "medium", "hard"], width=7,
                     state="readonly").pack(side="left", padx=4)
        ttk.Label(r0, text="seed").pack(side="left")
        self.v_seed = tk.IntVar(value=1)
        ttk.Spinbox(r0, from_=0, to=9999, textvariable=self.v_seed, width=5).pack(side="left", padx=4)
        ttk.Button(r0, text="Generate", command=self.generate).pack(side="left")

        r1 = ttk.Frame(bar)
        r1.pack(fill="x", pady=(6, 0))
        self.v_alg = tk.StringVar(value="bfs")
        ttk.Label(r1, text="Algorithm:").pack(side="left")
        ttk.Radiobutton(r1, text="BFS (required)", value="bfs", variable=self.v_alg,
                        command=self.reset).pack(side="left", padx=4)
        ttk.Radiobutton(r1, text="DFS (comparison)", value="dfs", variable=self.v_alg,
                        command=self.reset).pack(side="left", padx=4)
        ttk.Label(r1, text="Cell order:").pack(side="left", padx=(14, 2))
        self.v_order = tk.StringVar(value="first")
        ttk.Radiobutton(r1, text="first empty", value="first", variable=self.v_order,
                        command=self.reset).pack(side="left", padx=4)
        ttk.Radiobutton(r1, text="fewest options (MRV)", value="mrv", variable=self.v_order,
                        command=self.reset).pack(side="left", padx=4)
        self.v_all = tk.BooleanVar(value=False)
        ttk.Checkbutton(r1, text="Find all solutions", variable=self.v_all,
                        command=self.reset).pack(side="left", padx=(14, 0))
        self.v_nodes = tk.StringVar(value="5000000")
        self.v_front = tk.StringVar(value="2000000")
        self.v_time = tk.StringVar(value="120")
        for lab, var in (("Max nodes", self.v_nodes), ("Max queue", self.v_front),
                         ("Time (s)", self.v_time)):
            ttk.Label(r1, text=lab + ":").pack(side="left", padx=(12, 2))
            ttk.Entry(r1, textvariable=var, width=9).pack(side="left")

        r2 = ttk.Frame(bar)
        r2.pack(fill="x", pady=(6, 0))
        ttk.Button(r2, text="Step", width=8, command=self.step).pack(side="left")
        self.b_play = ttk.Button(r2, text="Play", width=8, command=self.toggle)
        self.b_play.pack(side="left", padx=4)
        ttk.Button(r2, text="Run to end", command=self.run_to_end).pack(side="left")
        ttk.Label(r2, text="Speed:").pack(side="left", padx=(14, 2))
        self.v_speed = tk.IntVar(value=3)
        tk.Scale(r2, from_=0, to=len(SPEEDS) - 1, orient="horizontal", showvalue=0, length=180,
                 variable=self.v_speed, command=lambda v: self._speed_label()).pack(side="left")
        self.l_speed = ttk.Label(r2, width=28)
        self.l_speed.pack(side="left", padx=6)
        self.v_log = tk.BooleanVar(value=True)
        ttk.Checkbutton(r2, text="Log every step", variable=self.v_log).pack(side="left", padx=8)
        self.b_save = ttk.Button(r2, text="Save result", command=self.save, state="disabled")
        self.b_save.pack(side="left", padx=8)
        self._speed_label()

    def _body(self):
        body = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        gf = ttk.LabelFrame(body, text="State being expanded")
        gf.grid(row=0, column=0, sticky="nw")
        self.cv = tk.Canvas(gf, width=470, height=470, bg="white", highlightthickness=0)
        self.cv.pack(padx=6, pady=6)
        self.l_state = ttk.Label(gf, text="", wraplength=460)
        self.l_state.pack(fill="x", padx=6, pady=(0, 6))

        mid = ttk.Frame(body)
        mid.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        qf = ttk.LabelFrame(mid, text="Frontier: next states in the queue")
        qf.pack(fill="x")
        self.qv = tk.Canvas(qf, height=250, bg="white", highlightthickness=0)
        self.qv.pack(fill="x", padx=6, pady=6)
        cf = ttk.LabelFrame(mid, text="States generated per depth (log scale)")
        cf.pack(fill="x", pady=(8, 0))
        self.ch = tk.Canvas(cf, height=170, bg="white", highlightthickness=0)
        self.ch.pack(fill="x", padx=6, pady=6)

        st = ttk.LabelFrame(body, text="Search state", padding=6)
        st.grid(row=0, column=2, sticky="ne", padx=(8, 0))
        self.stats = {}
        for name in ("Status", "Solutions found", "Generated", "Expanded", "Dead ends",
                     "Queue size now", "Max queue size", "Current depth", "Max depth",
                     "Empty cells (= goal depth)", "Search time (s)"):
            row = ttk.Frame(st)
            row.pack(fill="x")
            ttk.Label(row, text=name + ":", width=24).pack(side="left")
            lab = ttk.Label(row, text="-", font=("Helvetica", 10, "bold"), width=14)
            lab.pack(side="left")
            self.stats[name] = lab

        bottom = ttk.Frame(body)
        bottom.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(1, weight=1)
        self.l_explain = tk.Label(bottom, text="", anchor="w", justify="left",
                                  font=("Helvetica", 12, "bold"), wraplength=1300)
        self.l_explain.grid(row=0, column=0, sticky="ew")
        lf = ttk.LabelFrame(bottom, text="Log")
        lf.grid(row=1, column=0, sticky="nsew")
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)
        self.log = tk.Text(lf, height=7, font=("Courier", 10), state="disabled", wrap="word")
        sb = ttk.Scrollbar(lf, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        for tag, col in (("expand", "#1f5fbf"), ("dead", "#c00000"), ("goal", "#1a7f37"),
                         ("end", "#000080")):
            self.log.tag_configure(tag, foreground=col)

    def _speed_label(self):
        d, n = SPEEDS[self.v_speed.get()]
        self.l_speed.configure(text=f"{n:,} expansion(s) every {d} ms")

    # ------------------------------------------------------------ setup
    def generate(self):
        board = sv.Board(*sv.parse_box(self.v_box.get()))
        try:
            seed = int(self.v_seed.get())
        except (ValueError, tk.TclError):
            seed = 0
        self.root.config(cursor="watch")
        self.root.update()
        p = sv.generate(self.v_gen.get(), board, seed)
        self.root.config(cursor="")
        self.v_custom.set(sv.to_string(p))
        self.v_puzzle.set("custom")
        self.reset()
        self.l_desc.configure(text=f"generated: {self.v_gen.get()}, seed {seed}, "
                                   f"{board.cells - p.count(0)} givens")

    def reset(self):
        self.pause()
        name = self.v_puzzle.get()
        try:
            if name == "custom":
                board = sv.Board(*sv.parse_box(self.v_box.get()))
                puzzle = sv.parse_grid(self.v_custom.get(), board)
                desc = "your own grid"
            else:
                box, grid, desc = sv.PUZZLES[name]
                board = sv.Board(*sv.parse_box(box))
                puzzle = sv.parse_grid(grid, board)
            cfg = sv.Config(self.v_alg.get(), self.v_order.get(), find_all=self.v_all.get(),
                            max_nodes=int(self.v_nodes.get() or 0) or None,
                            max_frontier=int(self.v_front.get() or 0) or None,
                            time_limit=float(self.v_time.get() or 0) or None)
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return
        self.l_desc.configure(text=desc)
        self.board, self.puzzle, self.cfg = board, puzzle, cfg
        self.engine = SteppingSearch(puzzle, board, cfg)
        self.gen = self.engine.steps()
        self.paused_at = None
        self.current = None          # (state, depth, cell, digits)
        self.b_save.configure(state="disabled")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._log(f"New search: {name}, {board.n}x{board.n}, empty cells = {puzzle.count(0)}, "
                  f"{cfg.algorithm.upper()}, cell order = {cfg.order}, find all = {cfg.find_all}",
                  "end")
        self.l_explain.configure(
            text="Root of the search tree = the puzzle. Press Step to expand the first state.",
            fg="#222")
        self._redraw()

    # ------------------------------------------------------------ drawing
    def _draw_grid(self, cv, state, x0, y0, size, cell_hl=None, hl_color=CHOSEN,
                   digits=None, bg="white", font_scale=0.55):
        b = self.board
        n = b.n
        c = size / n
        cv.create_rectangle(x0, y0, x0 + size, y0 + size, fill=bg, outline="")
        for i in range(b.cells):
            r, col = divmod(i, n)
            x, y = x0 + col * c, y0 + r * c
            if i == cell_hl:
                cv.create_rectangle(x, y, x + c, y + c, fill=hl_color, outline="")
            v = state[i]
            if v:
                color = GIVEN if self.puzzle[i] else PLACED
                cv.create_text(x + c / 2, y + c / 2, text=str(v), fill=color,
                               font=("Helvetica", max(6, int(c * font_scale)),
                                     "bold" if self.puzzle[i] else "normal"))
            elif i == cell_hl and digits is not None:
                small = max(6, int(c * 0.22))
                k = math.ceil(math.sqrt(n))
                for d in digits:
                    rr, cc = divmod(d - 1, k)
                    cv.create_text(x + (cc + 0.5) * c / k, y + (rr + 0.5) * c / k, text=str(d),
                                   fill="#7a5c00", font=("Helvetica", small, "bold"))
        for k in range(n + 1):
            w = 2 if k % b.bc == 0 else 1
            cv.create_line(x0 + k * c, y0, x0 + k * c, y0 + size, width=w,
                           fill="#333" if w == 2 else "#bbb")
            w = 2 if k % b.br == 0 else 1
            cv.create_line(x0, y0 + k * c, x0 + size, y0 + k * c, width=w,
                           fill="#333" if w == 2 else "#bbb")

    def _redraw(self):
        e, res = self.engine, self.engine.res
        # big grid
        self.cv.delete("all")
        if res.solutions and e.finished:
            self._draw_grid(self.cv, res.solutions[0], 10, 10, 450, bg=SOLVED_BG)
            self.l_state.configure(text="First solution (green background). "
                                        "Black = givens, blue = found by search.")
        elif self.current is not None:
            state, depth, cell, digits = self.current
            dead = not digits
            self._draw_grid(self.cv, state, 10, 10, 450, cell_hl=cell,
                            hl_color=DEAD if dead else CHOSEN, digits=digits)
            r, c = divmod(cell, self.board.n)
            self.l_state.configure(
                text=f"Depth {depth}: cell (row {r + 1}, col {c + 1}) chosen; legal digits "
                     f"{digits if digits else 'NONE -> dead end'}")
        else:
            self._draw_grid(self.cv, self.puzzle, 10, 10, 450)
            self.l_state.configure(text="Initial state (root).")
        # queue preview
        self._draw_queue()
        self._draw_chart()
        st = self.stats
        st["Status"].configure(text=res.status if e.finished else
                               ("running" if self.running else "paused"))
        st["Solutions found"].configure(text=f"{len(res.solutions)}")
        st["Generated"].configure(text=f"{res.generated:,}")
        st["Expanded"].configure(text=f"{res.expanded:,}")
        st["Dead ends"].configure(text=f"{res.dead_ends:,}")
        st["Queue size now"].configure(text=f"{len(e.frontier):,}")
        st["Max queue size"].configure(text=f"{res.max_frontier:,}")
        st["Current depth"].configure(text="-" if self.current is None else str(self.current[1]))
        st["Max depth"].configure(text=f"{res.max_depth}")
        st["Empty cells (= goal depth)"].configure(text=f"{e.empty}")
        st["Search time (s)"].configure(text=f"{self._time():.3f}")

    def _draw_queue(self):
        q = self.qv
        q.delete("all")
        e = self.engine
        bfs = self.cfg.algorithm == "bfs"
        width = max(q.winfo_width(), 600)
        size = 104
        per = max(1, (width - 10) // (size + 16))
        items = list(e.frontier)[:per] if bfs else list(reversed(e.frontier))[:per]
        q.create_text(6, 10, anchor="w", fill="#555", font=("Helvetica", 9),
                      text=("FRONT of the FIFO queue (next to expand) ->" if bfs else
                            "TOP of the LIFO stack (next to expand) ->")
                      + f"   showing {len(items)} of {len(e.frontier):,}")
        for k, (state, depth) in enumerate(items):
            x = 6 + k * (size + 16)
            self._draw_grid(q, state, x, 26, size, font_scale=0.6)
            q.create_text(x + size / 2, 26 + size + 12, text=f"#{k + 1}  depth {depth}",
                          font=("Helvetica", 9))
        if not items:
            q.create_text(width / 2, 120, text="(queue empty)", fill="#888")

    def _draw_chart(self):
        ch = self.ch
        ch.delete("all")
        sizes = self.engine.res.level_sizes
        width = max(ch.winfo_width(), 600)
        h = 170
        n = len(sizes)
        if n == 0:
            return
        mx = max(sizes) or 1
        top = math.log10(mx + 1) or 1
        bw = (width - 50) / n
        cur = None if self.current is None else self.current[1]
        for d, s in enumerate(sizes):
            x = 40 + d * bw
            bh = (h - 34) * (math.log10(s + 1) / top) if s else 0
            col = "#e6a700" if d == cur else "#5b8fd6"
            ch.create_rectangle(x + 1, h - 18 - bh, x + bw - 1, h - 18, fill=col, outline="")
            if n <= 40 or d % 5 == 0:
                ch.create_text(x + bw / 2, h - 8, text=str(d), font=("Helvetica", 7))
        ch.create_text(4, 8, anchor="w", font=("Helvetica", 8), fill="#555",
                       text=f"max = {mx:,} states at one depth   (x axis: depth = digits added)")

    # ------------------------------------------------------------ running
    def _time(self):
        e = self.engine
        if not e.start:
            return 0.0
        end = self.paused_at if self.paused_at is not None else time.perf_counter()
        return max(0.0, end - e.start)

    def step(self):
        if not self.engine.finished:
            self.pause()
            self._advance(1)

    def toggle(self):
        if self.running:
            self.pause()
        elif not self.engine.finished:
            self.running = True
            self.b_play.configure(text="Pause")
            self._tick()

    def run_to_end(self):
        self.v_speed.set(len(SPEEDS) - 1)
        self._speed_label()
        if not self.running:
            self.toggle()

    def pause(self):
        self.running = False
        if hasattr(self, "b_play"):
            self.b_play.configure(text="Play")
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.engine is not None:
            self._redraw()

    def _tick(self):
        self.after_id = None
        if not self.running or self.engine.finished:
            return
        d, n = SPEEDS[self.v_speed.get()]
        self._advance(n)
        if self.running and not self.engine.finished:
            self.after_id = self.root.after(d, self._tick)

    def _advance(self, n):
        if self.paused_at is not None and self.engine.start:
            self.engine.start += time.perf_counter() - self.paused_at
        self.paused_at = None
        verbose = n <= VERBOSE_MAX and self.v_log.get()
        for _ in range(n):
            try:
                ev = next(self.gen)
            except StopIteration:
                break
            if ev[0] == "end":
                self.paused_at = time.perf_counter()
                self._finish()
                break
            _, state, depth, cell, digits, queued = ev
            self.current = (state, depth, cell, digits)
            if verbose:
                self._explain(state, depth, cell, digits, queued)
        if self.paused_at is None:
            self.paused_at = time.perf_counter()
        if not verbose and not self.engine.finished:
            self.l_explain.configure(text=f"Running {n:,} expansions per frame (log paused).",
                                     fg="#555")
        self._redraw()

    def _explain(self, state, depth, cell, digits, queued):
        r, c = divmod(cell, self.board.n)
        where = "end of the queue" if self.cfg.algorithm == "bfs" else "top of the stack"
        if not digits:
            msg = (f"Expand state at depth {depth}: cell ({r + 1},{c + 1}) has NO legal digit "
                   f"-> DEAD END, this branch is dropped (backtracking).")
            tag, col = "dead", "#c00000"
        else:
            goals = len(digits) - queued if depth + 1 == self.engine.empty else 0
            msg = (f"Expand state at depth {depth}: cell ({r + 1},{c + 1}) can take {digits} -> "
                   f"{len(digits)} children" +
                   (f", {goals} complete grid(s) = SOLUTION" if goals else
                    f" added to the {where}"))
            tag, col = ("goal", "#1a7f37") if goals else ("expand", "#1f5fbf")
        self._log(msg, tag)
        self.l_explain.configure(text=msg, fg=col)

    def _finish(self):
        res, cfg = self.engine.res, self.cfg
        self.running = False
        self.b_play.configure(text="Play")
        msg = sv.describe_status(res, cfg)
        if res.solutions:
            errs = sv.validate_solution(res.solutions[0], self.puzzle, self.board)
            msg += f"  Independent validation: {'VALID' if not errs else 'INVALID'}."
        col = {"SOLVED": "#1a7f37", "NO_SOLUTION": "#7a3e9d"}.get(res.status, "#c00000")
        self.l_explain.configure(text=f"{res.status}: {msg}", fg=col)
        self._log(f"{res.status}: {msg} [generated={res.generated:,}, max queue="
                  f"{res.max_frontier:,}, time={self._time():.3f}s]", "end")
        self.b_save.configure(state="normal")

    def _log(self, line, tag):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n", tag)
        if int(self.log.index("end-1c").split(".")[0]) > 500:
            self.log.delete("1.0", "101.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def save(self):
        import contextlib
        import io
        res = self.engine.res
        res.elapsed = self._time()
        buf = io.StringIO()
        name = self.v_puzzle.get()
        with contextlib.redirect_stdout(buf):
            print("Run from ui_sudoku.py (search time excludes drawing and pauses)")
            sv.print_run(name, self.puzzle, self.board, self.cfg, res)
        tag = f"{name}_{self.cfg.algorithm}_{self.cfg.order}_ui"
        path = sv.save_run(buf.getvalue(), tag, [(name, self.board, self.puzzle, self.cfg, res)])
        messagebox.showinfo("Saved", f"Saved to:\n{path}\nand a row in results/runs.csv")

    def close(self):
        self.pause()
        self.root.destroy()


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    if tk is None:
        print("tkinter is not available. Install Python from python.org (keep 'tcl/tk and "
              "IDLE' checked), or run: python ui_sudoku.py --selftest")
        return 1
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
