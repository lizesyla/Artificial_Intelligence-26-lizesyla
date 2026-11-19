#!/usr/bin/env python3
"""
Social Golfers Problem - visualizer (tkinter UI)
================================================

Shows step by step what the DFS with Backtracking in social_golfers.py does.

    python ui_golfers.py              # open the window
    python ui_golfers.py --selftest   # check that the visual DFS == the real solver

This file contains NO separate algorithm. The class SteppingDFS below inherits
everything from SocialGolfersDFS (candidates, constraint check, assign,
unassign, symmetry breaking, limits). It only rewrites the recursive _dfs()
as a loop that stops after every step so the window can draw it. The self
test checks that both versions produce exactly the same number of nodes,
backtracks and the same schedule.

What you see:
  * Schedule grid - one row per week, one box per group, one cell per golfer.
    The colour of a golfer is the colour of his group in week 1, so you can
    see how the golfers get mixed week after week.
    Yellow frame  = the slot DFS is trying to fill now.
    Red number    = a candidate that was REJECTED (pair already played).
    Orange frame  = a golfer just removed by BACKTRACKING.
  * Pair matrix - cell (a, b) is coloured with the week in which a and b
    played together (= the pair tracker). Red cells = the conflict that
    caused the last rejection. Move the mouse over it to read a cell.
  * Counters and a log explaining every step.

tkinter is part of the standard Python installer on Windows (python.org).
"""

from __future__ import annotations

import math
import sys
import time

import social_golfers as sg

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError:          # the self test does not need tkinter
    tk = None


# =============================================================================
# 1. STEP-BY-STEP VERSION OF THE SAME DFS
# =============================================================================

class SteppingDFS(sg.SocialGolfersDFS):
    """Identical search to SocialGolfersDFS._dfs, written with an explicit
    stack (the stack of the DFS) so that it can pause after every event.

    Events produced by steps():
        ("assign", x, k)        golfer x placed in slot k          (a new node)
        ("reject", x, k, ys)    golfer x does not fit: already met golfers ys
        ("deadend", k)          no candidate fits slot k -> go back up
        ("backtrack", x, k)     golfer x removed from slot k
        ("goal",) / ("exhausted",) / ("limit",)   end of the search
    """

    def __init__(self, config: sg.Config):
        super().__init__(config)
        self.rejects = 0
        self.status = None

    def slot(self, k: int):
        """slot number -> (week, group, position), all 0-based."""
        w, pos = divmod(k, self.N)
        gi, j = divmod(pos, self.S)
        return w, gi, j

    def conflicts(self, x: int, w: int, gi: int):
        return [y for y in self.schedule[w][gi] if (self.met[x] >> y) & 1]

    def week_met(self, a: int, b: int):
        """Week index in which a and b played together, or None."""
        for w, week in enumerate(self.schedule):
            for group in week:
                if a in group and b in group:
                    return w
        return None

    def _frame(self, k: int):
        cands = []
        if k < self.total_slots:
            w, gi, j = self.slot(k)
            cands = self._candidates(w, gi, j, k)   # same order as the solver
        return {"k": k, "cands": cands, "i": 0, "cur": None}

    def steps(self):
        self._start = time.perf_counter()
        stack = [self._frame(0)]                    # the DFS stack (LIFO)
        try:
            while stack:
                f = stack[-1]
                k = f["k"]
                self.max_depth = max(self.max_depth, k)
                if k == self.total_slots:           # goal test
                    self.status = sg.FOUND
                    yield ("goal",)
                    return
                w, gi, _ = self.slot(k)
                if f["cur"] is not None:            # child failed -> BACKTRACK
                    x = f["cur"]
                    self._unassign(x, w, gi)
                    self.backtracks += 1
                    f["cur"] = None
                    yield ("backtrack", x, k)
                went_deeper = False
                while f["i"] < len(f["cands"]):
                    x = f["cands"][f["i"]]
                    f["i"] += 1
                    if not self._consistent(x, w, gi):      # constraint check
                        self.rejects += 1
                        yield ("reject", x, k, self.conflicts(x, w, gi))
                        continue
                    self.nodes += 1
                    self._check_limits()
                    self._assign(x, w, gi)
                    f["cur"] = x
                    yield ("assign", x, k)
                    stack.append(self._frame(k + 1))        # go DEEPER
                    went_deeper = True
                    break
                if not went_deeper:                 # no candidate left
                    stack.pop()
                    yield ("deadend", k)
            self.status = sg.NO_SOLUTION
            yield ("exhausted",)
        except sg._LimitReached:
            self.status = sg.LIMIT_REACHED
            yield ("limit",)

    def run_all(self):
        for _ in self.steps():
            pass
        return self


def selftest() -> int:
    """Compare SteppingDFS with the real recursive solver on several cases."""
    cases = [
        dict(groups=2, group_size=4, weeks=1),
        dict(groups=2, group_size=4, weeks=2),
        dict(groups=2, group_size=4, weeks=2, symmetry_breaking=False),
        dict(groups=2, group_size=2, weeks=4),
        dict(groups=3, group_size=3, weeks=4),
        dict(groups=3, group_size=3, weeks=5),
        dict(groups=4, group_size=4, weeks=5),
        dict(groups=8, group_size=4, weeks=5),
        dict(groups=8, group_size=4, weeks=6, value_order="random", seed=0),
        dict(groups=3, group_size=3, weeks=3, symmetry_breaking=False,
             value_order="random", seed=2),
        dict(groups=8, group_size=4, weeks=7, max_nodes=20_000, time_limit=None),
    ]
    ok = True
    for c in cases:
        c.setdefault("time_limit", None)
        ref = sg.SocialGolfersDFS(sg.Config(**c)).solve()
        vis = SteppingDFS(sg.Config(**c)).run_all()
        vis_sched = ([[sorted(g) for g in wk] for wk in vis.schedule]
                     if vis.status == sg.FOUND else None)
        same = (ref.status == vis.status and ref.nodes == vis.nodes
                and ref.backtracks == vis.backtracks and ref.schedule == vis_sched)
        ok &= same
        print(f"{'OK  ' if same else 'FAIL'} {c}: solver {ref.status} "
              f"nodes={ref.nodes} bt={ref.backtracks} | visual {vis.status} "
              f"nodes={vis.nodes} bt={vis.backtracks}")
    print("SELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


# =============================================================================
# 2. THE WINDOW
# =============================================================================

GOLFER_COLORS = ["#a6cee3", "#b2df8a", "#fb9a99", "#fdbf6f", "#cab2d6", "#ffff99",
                 "#8dd3c7", "#bebada", "#80b1d3", "#fccde5", "#d9d9d9", "#ccebc5"]
WEEK_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd", "#8c564b", "#e377c2",
               "#17becf", "#bcbd22", "#7f7f7f", "#393b79", "#637939", "#8c6d31"]
EMPTY, CONFLICT, CURSOR, BACK = "#f2f2f2", "#ff0000", "#e6a700", "#ff7f0e"

# speed level -> (milliseconds between frames, DFS steps per frame)
SPEEDS = [(900, 1), (500, 1), (250, 1), (120, 1), (50, 1), (15, 1),
          (15, 5), (15, 25), (15, 200), (10, 2_000), (5, 20_000)]
VERBOSE_MAX = 25        # above this many steps per frame the log is paused

PRESETS = {
    "8 golfers - 2 groups x 4, W=2 (impossible)": (2, 4, 2, True, False, 0),
    "8 golfers - 2 groups x 4, W=2, no symmetry": (2, 4, 2, False, False, 0),
    "9 golfers - 3 groups x 3, W=4 (Kirkman)":    (3, 3, 4, True, False, 0),
    "16 golfers - 4 groups x 4, W=5":             (4, 4, 5, True, False, 0),
    "32 golfers - 8 groups x 4, W=5":             (8, 4, 5, True, False, 0),
    "32 golfers - 8 groups x 4, W=6 (random, seed 0)": (8, 4, 6, True, True, 0),
    "32 golfers - 8 groups x 4, W=6 (ascending, gets stuck)": (8, 4, 6, True, False, 0),
}


def txt(w, gi, j=None):
    s = f"week {w + 1}, group {gi + 1}"
    return s if j is None else s + f", position {j + 1}"


class App:
    def __init__(self, root):
        self.root = root
        root.title("Social Golfers - DFS with Backtracking (visualizer)")
        root.geometry("1360x860")
        root.minsize(1000, 640)
        self.after_id = None
        self.running = False
        self.engine = None
        self._build_controls()
        self._build_body()
        self.preset.set("8 golfers - 2 groups x 4, W=2 (impossible)")
        self.load_preset()
        root.protocol("WM_DELETE_WINDOW", self.close)

    # ---------------------------------------------------------------- layout
    def _build_controls(self):
        bar = ttk.Frame(self.root, padding=(8, 6))
        bar.pack(fill="x")

        ttk.Label(bar, text="Preset:").grid(row=0, column=0, sticky="w")
        self.preset = ttk.Combobox(bar, values=list(PRESETS), width=56, state="readonly")
        self.preset.grid(row=0, column=1, columnspan=5, sticky="w", padx=4)
        self.preset.bind("<<ComboboxSelected>>", lambda e: self.load_preset())

        self.v_groups, self.v_size, self.v_weeks = tk.IntVar(), tk.IntVar(), tk.IntVar()
        self.v_sym, self.v_rand = tk.BooleanVar(), tk.BooleanVar()
        self.v_seed = tk.IntVar(value=0)
        self.v_nodes = tk.StringVar(value="10000000")
        self.v_time = tk.StringVar(value="60")
        self.v_show_rej = tk.BooleanVar(value=True)

        col = 6
        for label, var, lo, hi in (("Groups G", self.v_groups, 1, 12),
                                   ("Size S", self.v_size, 2, 8),
                                   ("Weeks W", self.v_weeks, 1, 20)):
            ttk.Label(bar, text=label).grid(row=0, column=col, padx=(10, 2))
            ttk.Spinbox(bar, from_=lo, to=hi, textvariable=var, width=4).grid(row=0, column=col + 1)
            col += 2
        ttk.Button(bar, text="Apply / Reset", command=self.reset).grid(
            row=0, column=col, padx=(14, 0))

        r1 = ttk.Frame(bar)
        r1.grid(row=1, column=0, columnspan=20, sticky="w", pady=(6, 0))
        ttk.Checkbutton(r1, text="Symmetry breaking", variable=self.v_sym).pack(side="left")
        ttk.Checkbutton(r1, text="Random order, seed:", variable=self.v_rand).pack(
            side="left", padx=(14, 2))
        ttk.Spinbox(r1, from_=0, to=9999, textvariable=self.v_seed, width=5).pack(side="left")
        ttk.Label(r1, text="Max nodes:").pack(side="left", padx=(14, 2))
        ttk.Entry(r1, textvariable=self.v_nodes, width=10).pack(side="left")
        ttk.Label(r1, text="Time limit (s):").pack(side="left", padx=(14, 2))
        ttk.Entry(r1, textvariable=self.v_time, width=6).pack(side="left")
        ttk.Label(r1, text="(0 = no limit; press Apply / Reset after changing settings)",
                  foreground="#666").pack(side="left", padx=(10, 0))

        r2 = ttk.Frame(bar)
        r2.grid(row=2, column=0, columnspan=20, sticky="w", pady=(6, 0))
        ttk.Button(r2, text="Step", width=8, command=self.step).pack(side="left")
        self.b_play = ttk.Button(r2, text="Play", width=8, command=self.toggle_play)
        self.b_play.pack(side="left", padx=(4, 0))
        ttk.Button(r2, text="Run to end", command=self.run_to_end).pack(side="left", padx=(4, 0))
        ttk.Label(r2, text="Speed:").pack(side="left", padx=(14, 2))
        self.v_speed = tk.IntVar(value=3)
        tk.Scale(r2, from_=0, to=len(SPEEDS) - 1, orient="horizontal", showvalue=0,
                 variable=self.v_speed, length=180,
                 command=lambda v: self._speed_label()).pack(side="left")
        self.l_speed = ttk.Label(r2, width=26)
        self.l_speed.pack(side="left", padx=(6, 0))
        ttk.Checkbutton(r2, text="Log rejected candidates", variable=self.v_show_rej).pack(
            side="left", padx=(14, 0))
        self.b_save = ttk.Button(r2, text="Save result", command=self.save, state="disabled")
        self.b_save.pack(side="left", padx=(14, 0))
        self._speed_label()

    def _build_body(self):
        body = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=3)
        body.rowconfigure(2, weight=1)

        # schedule canvas (scrollable)
        left = ttk.LabelFrame(body, text="Schedule (rows = weeks, boxes = groups)")
        left.grid(row=0, column=0, sticky="nsew")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self.cv = tk.Canvas(left, bg="white", highlightthickness=0)
        ys = ttk.Scrollbar(left, orient="vertical", command=self.cv.yview)
        xs = ttk.Scrollbar(left, orient="horizontal", command=self.cv.xview)
        self.cv.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.cv.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        self.cv.bind("<Motion>", self._hover_schedule)
        self.cv.bind("<Leave>", lambda e: self._highlight_golfer(None))

        # right panel: counters + pair matrix
        right = ttk.Frame(body)
        right.grid(row=0, column=1, rowspan=3, sticky="ns", padx=(8, 0))
        st = ttk.LabelFrame(right, text="Search state", padding=6)
        st.pack(fill="x")
        self.stats = {}
        for name in ("Status", "Nodes (states generated)", "Backtracks", "Rejected candidates",
                     "Current depth (filled slots)", "Max depth reached", "Complete weeks",
                     "Pairs used", "Upper bound on weeks", "Search time (s)"):
            row = ttk.Frame(st)
            row.pack(fill="x")
            ttk.Label(row, text=name + ":", width=26).pack(side="left")
            lab = ttk.Label(row, text="-", font=("Helvetica", 10, "bold"))
            lab.pack(side="left")
            self.stats[name] = lab

        pm = ttk.LabelFrame(right, text="Pair tracker: who has played with whom", padding=6)
        pm.pack(fill="both", expand=True, pady=(8, 0))
        self.pm = tk.Canvas(pm, width=380, height=380, bg="white", highlightthickness=0)
        self.pm.pack()
        self.pm.bind("<Motion>", self._hover_matrix)
        self.l_pm = ttk.Label(pm, text="Move the mouse over the matrix.", wraplength=370)
        self.l_pm.pack(fill="x", pady=(4, 0))
        self.legend = tk.Canvas(pm, width=380, height=44, bg=self.root.cget("bg"),
                                highlightthickness=0)
        self.legend.pack(pady=(4, 0))

        # explanation line + log
        self.l_explain = tk.Label(body, text="", anchor="w", justify="left",
                                  font=("Helvetica", 12, "bold"), fg="#222",
                                  wraplength=900)
        self.l_explain.grid(row=1, column=0, sticky="ew", pady=(6, 2))
        lf = ttk.LabelFrame(body, text="Log (what DFS does, step by step)")
        lf.grid(row=2, column=0, sticky="nsew")
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)
        self.log = tk.Text(lf, height=9, font=("Courier", 10), state="disabled", wrap="word")
        sb = ttk.Scrollbar(lf, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        for tag, color in (("assign", "#1a7f37"), ("reject", "#c00000"),
                           ("backtrack", "#d46b00"), ("deadend", "#7a3e9d"),
                           ("end", "#000080")):
            self.log.tag_configure(tag, foreground=color)

    def _speed_label(self):
        d, n = SPEEDS[self.v_speed.get()]
        self.l_speed.configure(text=f"{n:,} step(s) every {d} ms")

    # ---------------------------------------------------------------- setup
    def load_preset(self):
        g, s, w, sym, rnd, seed = PRESETS[self.preset.get()]
        self.v_groups.set(g)
        self.v_size.set(s)
        self.v_weeks.set(w)
        self.v_sym.set(sym)
        self.v_rand.set(rnd)
        self.v_seed.set(seed)
        self.reset()

    def _read_config(self):
        try:
            mn = int(self.v_nodes.get() or 0)
            tl = float(self.v_time.get() or 0)
            cfg = sg.Config(groups=int(self.v_groups.get()), group_size=int(self.v_size.get()),
                            weeks=int(self.v_weeks.get()), max_nodes=mn or None,
                            time_limit=tl or None, symmetry_breaking=self.v_sym.get(),
                            value_order="random" if self.v_rand.get() else "ascending",
                            seed=int(self.v_seed.get()))
            cfg.check()
            if cfg.golfers > 96:
                raise ValueError("please keep N = G x S at most 96 for the drawing")
            return cfg
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("Invalid settings", str(e))
            return None

    def reset(self):
        cfg = self._read_config()
        if cfg is None:
            return
        self.pause()
        self.cfg = cfg
        self.engine = SteppingDFS(cfg)
        self.gen = self.engine.steps()
        self.finished = False
        self.paused_at = None
        self.flash_pairs = []
        self.last_event = None
        self.b_save.configure(state="disabled")
        self._draw_schedule()
        self._draw_matrix()
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        n, ub = cfg.golfers, sg.upper_bound_weeks(cfg.groups, cfg.group_size)
        self._log(f"New search: N={n} golfers, G={cfg.groups}, S={cfg.group_size}, "
                  f"W={cfg.weeks}, symmetry={cfg.symmetry_breaking}, "
                  f"order={cfg.value_order}"
                  + (f" (seed {cfg.seed})" if cfg.value_order == "random" else ""), "end")
        msg = "Press Step to make one DFS step, or Play to animate."
        if cfg.weeks > ub:
            msg = (f"Note: W={cfg.weeks} is above the upper bound {ub} - impossible by "
                   f"counting. DFS will still try. " + msg)
        self.l_explain.configure(text=msg, fg="#222")
        self._refresh()

    # ---------------------------------------------------------------- schedule drawing
    def _draw_schedule(self):
        c, cfg = self.cv, self.cfg
        c.delete("all")
        G, S, W, N = cfg.groups, cfg.group_size, cfg.weeks, cfg.golfers
        width = max(c.winfo_width(), 820)
        self.left, self.top, self.gap, self.rowgap = 74, 30, 14, 12
        avail = width - self.left - 40 - (G - 1) * self.gap
        self.cell = cell = max(18, min(46, avail // (G * S)))
        font = ("Helvetica", max(7, int(cell * 0.40)), "bold")
        self.slot_items = []
        for g in range(G):
            x = self.left + g * (S * cell + self.gap)
            c.create_text(x + S * cell / 2, 14, text=f"Group {g + 1}", fill="#555",
                          font=("Helvetica", 9))
        self.week_marks = []
        for w in range(W):
            y = self.top + w * (cell + self.rowgap)
            col = WEEK_COLORS[w % len(WEEK_COLORS)]
            c.create_rectangle(8, y + cell / 2 - 6, 20, y + cell / 2 + 6, fill=col, outline="")
            c.create_text(24, y + cell / 2, text=f"Week {w + 1}", anchor="w",
                          font=("Helvetica", 9, "bold"))
            for g in range(G):
                x = self.left + g * (S * cell + self.gap)
                c.create_rectangle(x - 3, y - 3, x + S * cell + 3, y + cell + 3,
                                   outline="#9a9a9a")
                for j in range(S):
                    r = c.create_rectangle(x + j * cell + 1, y + 1, x + (j + 1) * cell - 1,
                                           y + cell - 1, fill=EMPTY, outline="#d0d0d0")
                    t = c.create_text(x + j * cell + cell / 2, y + cell / 2, text="",
                                      font=font)
                    self.slot_items.append((r, t))
            xm = self.left + G * (S * cell + self.gap)
            self.week_marks.append(c.create_text(xm, y + cell / 2, text="", anchor="w",
                                                 fill="#1a7f37", font=("Helvetica", 12, "bold")))
        self.cursor = c.create_rectangle(0, 0, 0, 0, outline=CURSOR, width=4)
        self.flash = c.create_rectangle(0, 0, 0, 0, outline=BACK, width=4, state="hidden")
        self.cand = c.create_text(0, 0, text="", fill=CONFLICT, font=font, state="hidden")
        self.shown = [None] * (W * N)
        self.hl_golfer = None
        h = self.top + W * (cell + self.rowgap) + 10
        c.configure(scrollregion=(0, 0, self.left + G * (S * cell + self.gap) + 40, h))

    def _slot_box(self, k):
        w, gi, j = self.engine.slot(k)
        cell, S = self.cell, self.cfg.group_size
        x = self.left + gi * (S * cell + self.gap) + j * cell
        y = self.top + w * (cell + self.rowgap)
        return x, y, x + cell, y + cell

    def _golfer_color(self, x):
        return GOLFER_COLORS[((x - 1) // self.cfg.group_size) % len(GOLFER_COLORS)]

    # ---------------------------------------------------------------- matrix drawing
    def _draw_matrix(self):
        p, N, S = self.pm, self.cfg.golfers, self.cfg.group_size
        p.delete("all")
        self.m = m = max(3, min(28, 350 // N))
        self.m0 = m0 = 22
        size = m0 + N * m + 4
        p.configure(width=max(size, 200), height=max(size, 200))
        step = 1 if m >= 14 else (S if N <= 40 else 2 * S)
        self.pm_items = {}
        for a in range(1, N + 1):
            if (a - 1) % step == 0 or a == N and step == 1:
                p.create_text(m0 + (a - 0.5) * m, 10, text=str(a), font=("Helvetica", 7))
                p.create_text(10, m0 + (a - 0.5) * m, text=str(a), font=("Helvetica", 7))
            for b in range(1, N + 1):
                x, y = m0 + (b - 1) * m, m0 + (a - 1) * m
                fill = "#cfcfcf" if a == b else "white"
                self.pm_items[(a, b)] = p.create_rectangle(x, y, x + m, y + m, fill=fill,
                                                           outline="#eeeeee" if m > 5 else "")
        for i in range(0, N + 1, S):          # lines between week-1 groups
            z = m0 + i * m
            p.create_line(m0, z, m0 + N * m, z, fill="#888")
            p.create_line(z, m0, z, m0 + N * m, fill="#888")
        self.pm_shown = {}
        # legend
        lg = self.legend
        lg.delete("all")
        for w in range(min(self.cfg.weeks, 12)):
            x = 4 + (w % 6) * 62
            y = 4 + (w // 6) * 20
            lg.create_rectangle(x, y, x + 14, y + 14, fill=WEEK_COLORS[w], outline="")
            lg.create_text(x + 18, y + 7, text=f"week {w + 1}", anchor="w", font=("Helvetica", 8))

    # ---------------------------------------------------------------- refresh
    def _refresh(self):
        e, cfg = self.engine, self.cfg
        N, S, total = cfg.golfers, cfg.group_size, e.total_slots
        filled = 0
        pair_week = {}
        for w, week in enumerate(e.schedule):
            for gi, group in enumerate(week):
                for j in range(S):
                    k = w * N + gi * S + j
                    x = group[j] if j < len(group) else None
                    if x is not None:
                        filled += 1
                    if self.shown[k] != x:
                        r, t = self.slot_items[k]
                        self.cv.itemconfigure(r, fill=EMPTY if x is None else self._golfer_color(x))
                        self.cv.itemconfigure(t, text="" if x is None else str(x))
                        self.shown[k] = x
                for i in range(len(group)):
                    for jj in range(i + 1, len(group)):
                        pair_week[(group[i], group[jj])] = w
                        pair_week[(group[jj], group[i])] = w
        for w in range(cfg.weeks):
            complete = all(self.shown[w * N + i] is not None for i in range(N))
            self.cv.itemconfigure(self.week_marks[w], text="✓" if complete else "")
        # cursor = next slot DFS will fill
        if filled < total and not self.finished:
            self.cv.coords(self.cursor, *self._slot_box(filled))
            self.cv.itemconfigure(self.cursor, state="normal")
        else:
            self.cv.itemconfigure(self.cursor, state="hidden")
        # pair matrix
        flash = set()
        for a, b in self.flash_pairs:
            flash.add((a, b))
            flash.add((b, a))
        for key, item in self.pm_items.items():
            if key[0] == key[1]:
                continue
            col = WEEK_COLORS[pair_week[key] % len(WEEK_COLORS)] if key in pair_week else "white"
            if key in flash:
                col = CONFLICT
            if self.pm_shown.get(key) != col:
                self.pm.itemconfigure(item, fill=col)
                self.pm_shown[key] = col
        # counters
        used = len(pair_week) // 2
        st = self.stats
        st["Status"].configure(text=e.status or ("running" if self.running else "ready / paused"))
        st["Nodes (states generated)"].configure(text=f"{e.nodes:,}")
        st["Backtracks"].configure(text=f"{e.backtracks:,}")
        st["Rejected candidates"].configure(text=f"{e.rejects:,}")
        st["Current depth (filled slots)"].configure(text=f"{filled} / {total}")
        st["Max depth reached"].configure(text=f"{e.max_depth} / {total}")
        st["Complete weeks"].configure(text=f"{filled // N} / {cfg.weeks}")
        st["Pairs used"].configure(text=f"{used} / {math.comb(N, 2)}")
        st["Upper bound on weeks"].configure(
            text=f"floor(({N}-1)/({S}-1)) = {sg.upper_bound_weeks(cfg.groups, S)}")
        st["Search time (s)"].configure(text=f"{self._search_time():.3f}")

    def _search_time(self):
        e = self.engine
        if not e._start:
            return 0.0
        end = self.paused_at if self.paused_at is not None else time.perf_counter()
        return max(0.0, end - e._start)

    # ---------------------------------------------------------------- running
    def step(self):
        if not self.finished:
            self.pause()
            self._advance(1)

    def toggle_play(self):
        if self.running:
            self.pause()
        elif not self.finished:
            self.running = True
            self.b_play.configure(text="Pause")
            self._tick()

    def run_to_end(self):
        self.v_speed.set(len(SPEEDS) - 1)
        self._speed_label()
        if not self.running:
            self.toggle_play()

    def pause(self):
        self.running = False
        if hasattr(self, "b_play"):
            self.b_play.configure(text="Play")
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.engine is not None:
            self._refresh()

    def _tick(self):
        self.after_id = None
        if not self.running or self.finished:
            return
        delay, n = SPEEDS[self.v_speed.get()]
        self._advance(n)
        if self.running and not self.finished:
            self.after_id = self.root.after(delay, self._tick)

    def _advance(self, n):
        # time spent drawing / waiting between frames is not counted as search time
        if self.paused_at is not None and self.engine._start:
            self.engine._start += time.perf_counter() - self.paused_at
        self.paused_at = None
        verbose = n <= VERBOSE_MAX
        self.flash_pairs = []
        self.cv.itemconfigure(self.flash, state="hidden")
        self.cv.itemconfigure(self.cand, state="hidden")
        for _ in range(n):
            try:
                ev = next(self.gen)
            except StopIteration:
                break
            self.last_event = ev
            if ev[0] in ("goal", "exhausted", "limit"):
                self.paused_at = time.perf_counter()
                self._finish(ev[0])
                break
            if verbose:
                self._explain(ev)
        if self.paused_at is None:
            self.paused_at = time.perf_counter()
        if not verbose and not self.finished:
            self.l_explain.configure(
                text=f"Running fast ({n:,} steps per frame) - log paused. "
                     f"Slow down the speed to read every step.", fg="#555")
            if self.last_event is not None:
                self._show_transient(self.last_event)
        self._refresh()

    def _show_transient(self, ev):
        kind = ev[0]
        if kind == "reject":
            x, k, ys = ev[1], ev[2], ev[3]
            x0, y0, x1, y1 = self._slot_box(k)
            self.cv.coords(self.cand, (x0 + x1) / 2, (y0 + y1) / 2)
            self.cv.itemconfigure(self.cand, text=str(x), state="normal")
            self.cv.tag_raise(self.cand)
            self.flash_pairs = [(x, y) for y in ys]
        elif kind == "backtrack":
            self.cv.coords(self.flash, *self._slot_box(ev[2]))
            self.cv.itemconfigure(self.flash, state="normal")
            self.cv.tag_raise(self.flash)

    def _explain(self, ev):
        e = self.engine
        kind = ev[0]
        self._show_transient(ev)
        if kind == "assign":
            x, k = ev[1], ev[2]
            w, gi, j = e.slot(k)
            msg = f"Place golfer {x} in {txt(w, gi, j)}  -> fits, go deeper (node #{e.nodes})"
            self._log(msg, "assign")
            color = "#1a7f37"
        elif kind == "reject":
            x, k, ys = ev[1], ev[2], ev[3]
            w, gi, j = e.slot(k)
            parts = []
            for y in ys:
                wm = e.week_met(x, y)
                parts.append(f"{y} (week {wm + 1})" if wm is not None else str(y))
            msg = (f"Try golfer {x} in {txt(w, gi, j)}  -> REJECTED: already played with "
                   + ", ".join(parts))
            if self.v_show_rej.get():
                self._log(msg, "reject")
            color = "#c00000"
        elif kind == "backtrack":
            x, k = ev[1], ev[2]
            w, gi, j = e.slot(k)
            msg = f"BACKTRACK: remove golfer {x} from {txt(w, gi, j)}, try the next candidate"
            self._log(msg, "backtrack")
            color = "#d46b00"
        else:  # deadend
            k = ev[1]
            w, gi, j = e.slot(k)
            msg = (f"DEAD END: no golfer fits {txt(w, gi, j)} -> return to the previous slot")
            self._log(msg, "deadend")
            color = "#7a3e9d"
        self.l_explain.configure(text=msg, fg=color)

    def _finish(self, kind):
        self.finished = True
        self.running = False
        self.b_play.configure(text="Play")
        e, cfg = self.engine, self.cfg
        if kind == "goal":
            sched = [[sorted(g) for g in wk] for wk in e.schedule]
            errs = sg.validate_schedule(sched, cfg.groups, cfg.group_size, cfg.weeks)
            msg = (f"FOUND a valid {cfg.weeks}-week schedule "
                   f"(independent validation: {'VALID' if not errs else 'INVALID'}). "
                   f"This shows {cfg.weeks} weeks are POSSIBLE; it does not prove it is the maximum.")
            color = "#1a7f37"
        elif kind == "exhausted":
            msg = (f"NO_SOLUTION: the whole search tree was explored. A {cfg.weeks}-week "
                   f"schedule is IMPOSSIBLE (proved by exhaustive search).")
            color = "#7a3e9d"
        else:
            msg = (f"LIMIT_REACHED: stopped by the node/time limit. NOTHING is proven - a "
                   f"{cfg.weeks}-week schedule may or may not exist.")
            color = "#c00000"
        self.l_explain.configure(text=msg, fg=color)
        self._log(msg + f"  [nodes={e.nodes:,}, backtracks={e.backtracks:,}, "
                        f"time={self._search_time():.3f}s]", "end")
        self.b_save.configure(state="normal")

    def _log(self, line, tag):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n", tag)
        if int(self.log.index("end-1c").split(".")[0]) > 600:
            self.log.delete("1.0", "101.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ---------------------------------------------------------------- hover
    def _hover_schedule(self, event):
        if not self.engine:
            return
        x, y = self.cv.canvasx(event.x), self.cv.canvasy(event.y)
        golfer = None
        for k, (r, _) in enumerate(self.slot_items):
            x0, y0, x1, y1 = self.cv.coords(r)
            if x0 <= x <= x1 and y0 <= y <= y1:
                golfer = self.shown[k]
                break
        self._highlight_golfer(golfer)

    def _highlight_golfer(self, golfer):
        if golfer == self.hl_golfer:
            return
        self.hl_golfer = golfer
        for k, (r, _) in enumerate(self.slot_items):
            on = golfer is not None and self.shown[k] == golfer
            self.cv.itemconfigure(r, outline="#000000" if on else "#d0d0d0", width=3 if on else 1)
        if golfer is not None:
            met = bin(self.engine.met[golfer]).count("1")
            self.l_pm.configure(text=f"Golfer {golfer} has played with {met} of the "
                                     f"{self.cfg.golfers - 1} other golfers so far "
                                     f"(highlighted in black in every week).")

    def _hover_matrix(self, event):
        if not self.engine:
            return
        b = int((event.x - self.m0) // self.m) + 1
        a = int((event.y - self.m0) // self.m) + 1
        N = self.cfg.golfers
        if not (1 <= a <= N and 1 <= b <= N):
            return
        if a == b:
            self.l_pm.configure(text=f"Golfer {a} (diagonal)")
            return
        wm = self.engine.week_met(a, b)
        self.l_pm.configure(text=f"Golfers {a} & {b}: " +
                            (f"played together in week {wm + 1} -> may NOT meet again"
                             if wm is not None else "have not played together yet"))

    # ---------------------------------------------------------------- save / close
    def save(self):
        e, cfg = self.engine, self.cfg
        sched = ([[sorted(g) for g in wk] for wk in e.schedule]
                 if e.status == sg.FOUND else None)
        res = sg.SearchResult(e.status, sched, e.nodes, e.backtracks, self._search_time(),
                              cfg, e.max_depth, e.max_depth // cfg.golfers)
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print("Run from ui_golfers.py (search time excludes drawing and pauses)")
            sg.print_problem_info(cfg.groups, cfg.group_size, cfg.weeks)
            sg.print_result(res)
        tag = (f"{cfg.golfers}-{cfg.groups}-{cfg.group_size}_W{cfg.weeks}_ui"
               + ("" if cfg.symmetry_breaking else "_nosym")
               + (f"_rand{cfg.seed}" if cfg.value_order == "random" else ""))
        path = sg.save_output(buf.getvalue(), tag, [res])
        messagebox.showinfo("Saved", f"Saved to:\n{path}\nand a row in results/runs.csv")

    def close(self):
        self.pause()
        self.root.destroy()


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    if tk is None:
        print("tkinter is not available in this Python installation.\n"
              "On Windows reinstall Python from python.org and keep the option "
              "'tcl/tk and IDLE' checked. Run 'python ui_golfers.py --selftest' to "
              "test the engine without a window.")
        return 1
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
