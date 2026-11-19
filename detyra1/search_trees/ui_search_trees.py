#!/usr/bin/env python3
"""
Search Trees - visualizer (tkinter)
===================================

    python ui_search_trees.py

Draws the search tree while it is being built, for the 8-Puzzle, Missionaries
and Cannibals and Rotating Workforce Scheduling, with BFS, DFS, DLS, IDDFS or UCS.
The window runs the SAME generator (search_core.Search.events) as
search_trees.py, one expansion per step, so there is nothing to keep in sync.

Colours: blue = expanded (number = expansion order), white = generated but not
expanded yet (frontier), grey dashed = repeated state (pruned), purple =
cutoff by the depth limit, pink = dead end, green = goal; the solution path
is drawn with thick green lines. The orange frame marks the node that was
expanded in the last step.
"""

from __future__ import annotations

import sys
import time

import eight_puzzle as ep
import missionaries as mc
import search_core as sc
import workforce as wf
from search_trees import make_problem, describe, explain

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError:
    tk = None

INSTANCES = {"puzzle8": list(ep.INSTANCES), "missionaries": list(mc.INSTANCES),
             "workforce": list(wf.INSTANCES)}
SPEEDS = [(1200, 1), (700, 1), (400, 1), (200, 1), (80, 1), (20, 1), (20, 10), (15, 200),
          (10, 5_000)]


class App:
    def __init__(self, root):
        self.root = root
        root.title("Search Trees - uninformed search (visualizer)")
        root.geometry("1400x900")
        root.minsize(1100, 700)
        self.after_id = None
        self.running = False
        self.search = None
        self._controls()
        self._body()
        self.reset()
        root.protocol("WM_DELETE_WINDOW", self.close)

    # ------------------------------------------------------------ layout
    def _controls(self):
        bar = ttk.Frame(self.root, padding=(8, 6))
        bar.pack(fill="x")
        r0 = ttk.Frame(bar)
        r0.pack(fill="x")
        self.v_prob = tk.StringVar(value="missionaries")
        self.v_inst = tk.StringVar(value="classic")
        self.v_start = tk.StringVar(value="")
        self.v_alg = tk.StringVar(value="bfs")
        self.v_rep = tk.StringVar(value="graph")
        self.v_lim = tk.StringVar(value="")
        self.v_draw = tk.IntVar(value=120)
        self.v_zoom = tk.DoubleVar(value=1.0)
        self.v_follow = tk.BooleanVar(value=True)
        ttk.Label(r0, text="Problem:").pack(side="left")
        cb = ttk.Combobox(r0, textvariable=self.v_prob, values=list(INSTANCES), width=13,
                          state="readonly")
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self._problem_changed())
        ttk.Label(r0, text="Instance:").pack(side="left", padx=(8, 2))
        self.cb_inst = ttk.Combobox(r0, textvariable=self.v_inst, width=11, state="readonly")
        self.cb_inst.pack(side="left")
        self.cb_inst.bind("<<ComboboxSelected>>", lambda e: self.reset())
        ttk.Label(r0, text="8-puzzle start (optional):").pack(side="left", padx=(8, 2))
        ttk.Entry(r0, textvariable=self.v_start, width=20).pack(side="left")
        ttk.Label(r0, text="Algorithm:").pack(side="left", padx=(12, 2))
        for a in sc.ALGORITHMS:
            ttk.Radiobutton(r0, text=a.upper(), value=a, variable=self.v_alg,
                            command=self._alg_changed).pack(side="left", padx=2)
        ttk.Button(r0, text="Apply / Reset", command=self.reset).pack(side="left", padx=10)

        r1 = ttk.Frame(bar)
        r1.pack(fill="x", pady=(6, 0))
        ttk.Label(r1, text="Repeated states:").pack(side="left")
        for v, t in (("graph", "graph search (no state twice)"),
                     ("path", "no cycles on a path"), ("none", "pure tree search")):
            ttk.Radiobutton(r1, text=t, value=v, variable=self.v_rep, command=self.reset).pack(
                side="left", padx=4)
        ttk.Label(r1, text="Depth limit (DLS/DFS):").pack(side="left", padx=(12, 2))
        ttk.Entry(r1, textvariable=self.v_lim, width=5).pack(side="left")
        ttk.Label(r1, text="Nodes drawn:").pack(side="left", padx=(12, 2))
        ttk.Spinbox(r1, from_=10, to=600, increment=10, textvariable=self.v_draw, width=5,
                    command=self._redraw).pack(side="left")
        ttk.Label(r1, text="Zoom:").pack(side="left", padx=(12, 2))
        tk.Scale(r1, from_=0.4, to=1.6, resolution=0.1, orient="horizontal", showvalue=1,
                 variable=self.v_zoom, length=120, command=lambda v: self._redraw()).pack(side="left")
        ttk.Checkbutton(r1, text="Follow the search (auto-scroll)", variable=self.v_follow).pack(
            side="left", padx=12)

        r2 = ttk.Frame(bar)
        r2.pack(fill="x", pady=(6, 0))
        ttk.Button(r2, text="Step (1 expansion)", command=self.step).pack(side="left")
        self.b_play = ttk.Button(r2, text="Play", width=8, command=self.toggle)
        self.b_play.pack(side="left", padx=4)
        ttk.Button(r2, text="Run to end", command=self.run_to_end).pack(side="left")
        ttk.Label(r2, text="Speed:").pack(side="left", padx=(12, 2))
        self.v_speed = tk.IntVar(value=3)
        tk.Scale(r2, from_=0, to=len(SPEEDS) - 1, orient="horizontal", showvalue=0, length=160,
                 variable=self.v_speed, command=lambda v: self._speed_label()).pack(side="left")
        self.l_speed = ttk.Label(r2, width=26)
        self.l_speed.pack(side="left", padx=6)
        self.l_desc = ttk.Label(r2, foreground="#555")
        self.l_desc.pack(side="left", padx=8)
        self._speed_label()
        self._problem_changed(reset=False)

    def _body(self):
        body = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        tf = ttk.LabelFrame(body, text="Search tree")
        tf.grid(row=0, column=0, sticky="nsew")
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)
        self.cv = tk.Canvas(tf, bg="white", highlightthickness=0)
        xs = ttk.Scrollbar(tf, orient="horizontal", command=self.cv.xview)
        ys = ttk.Scrollbar(tf, orient="vertical", command=self.cv.yview)
        self.cv.configure(xscrollcommand=xs.set, yscrollcommand=ys.set)
        self.cv.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")

        right = ttk.Frame(body)
        right.grid(row=0, column=1, rowspan=2, sticky="ns", padx=(8, 0))
        st = ttk.LabelFrame(right, text="Search state", padding=6)
        st.pack(fill="x")
        self.stats = {}
        for name in ("Status", "Generated", "Expanded", "Pruned (repeated)", "Cutoffs",
                     "Frontier size", "Max frontier", "Max depth", "Solution length",
                     "IDDFS limit", "Time (s)"):
            row = ttk.Frame(st)
            row.pack(fill="x")
            ttk.Label(row, text=name + ":", width=18).pack(side="left")
            lab = ttk.Label(row, text="-", font=("Helvetica", 10, "bold"), width=14)
            lab.pack(side="left")
            self.stats[name] = lab
        ff = ttk.LabelFrame(right, text="Frontier (next nodes to expand)", padding=6)
        ff.pack(fill="both", expand=True, pady=(8, 0))
        self.l_front = tk.Label(ff, text="", font=("Courier New", 9), justify="left", anchor="nw")
        self.l_front.pack(fill="both", expand=True)
        lg = ttk.LabelFrame(right, text="Legend", padding=6)
        lg.pack(fill="x", pady=(8, 0))
        for st_, txt in (("expanded", "expanded (#order)"), ("frontier", "in frontier"),
                         ("duplicate", "repeated state, pruned"), ("cutoff", "cutoff (limit)"),
                         ("deadend", "dead end"), ("goal", "goal")):
            row = ttk.Frame(lg)
            row.pack(fill="x")
            c = tk.Canvas(row, width=16, height=14, highlightthickness=0)
            c.create_rectangle(1, 1, 15, 13, fill=sc.STATUS_COLORS[st_], outline="#555")
            c.pack(side="left")
            ttk.Label(row, text=txt).pack(side="left", padx=4)

        bottom = ttk.Frame(body)
        bottom.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        bottom.columnconfigure(0, weight=1)
        self.l_explain = tk.Label(bottom, text="", anchor="w", justify="left",
                                  font=("Helvetica", 12, "bold"), wraplength=1050)
        self.l_explain.grid(row=0, column=0, sticky="ew")
        self.log = tk.Text(bottom, height=6, font=("Courier", 10), state="disabled", wrap="word")
        self.log.grid(row=1, column=0, sticky="ew")

    def _speed_label(self):
        d, n = SPEEDS[self.v_speed.get()]
        self.l_speed.configure(text=f"{n:,} expansion(s) every {d} ms")

    def _problem_changed(self, reset=True):
        insts = INSTANCES[self.v_prob.get()]
        self.cb_inst.configure(values=insts)
        if self.v_inst.get() not in insts:
            self.v_inst.set({"puzzle8": "easy", "missionaries": "classic",
                             "workforce": "tiny"}[self.v_prob.get()])
        if reset:
            self.reset()

    def _alg_changed(self):
        if self.v_alg.get() == "iddfs" and self.v_rep.get() == "graph":
            self.v_rep.set("path")
        if self.v_alg.get() == "dls" and not self.v_lim.get().strip():
            self.v_lim.set("3")
        self.reset()

    # ------------------------------------------------------------ setup
    def reset(self):
        self.pause()
        try:
            start = self.v_start.get().strip() if self.v_prob.get() == "puzzle8" else None
            self.problem, inst = make_problem(self.v_prob.get(), self.v_inst.get(), start or None)
            lim = int(self.v_lim.get()) if self.v_lim.get().strip() else None
            rep = self.v_rep.get()
            if self.v_alg.get() == "iddfs" and rep == "graph":
                rep = "path"
            self.cfg = sc.Config(self.v_alg.get(), rep, depth_limit=lim, max_nodes=2_000_000,
                                 time_limit=120)
            self.search = sc.Search(self.problem, self.cfg)
        except (ValueError, tk.TclError) as e:
            messagebox.showerror("Invalid input", str(e))
            return
        self.gen = self.search.events()
        self.finished = False
        self.last = None
        self.iter_L = None
        self.paused_at = None
        self.l_desc.configure(text=describe(self.problem)[:110])
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._log(f"New search: {self.v_prob.get()} / {inst} / {self.cfg.algorithm.upper()} "
                  f"(repeated = {self.cfg.repeated})")
        self.l_explain.configure(text="Press Step: the root is created and expanded.", fg="#222")
        self._redraw()
        self.cv.xview_moveto(0)
        self.cv.yview_moveto(0)

    # ------------------------------------------------------------ drawing
    def _redraw(self):
        cv = self.cv
        cv.delete("all")
        res = self.search.res
        if res.root is None:
            cv.create_text(300, 60, text="Press Step to create the root node.", fill="#888",
                           font=("Helvetica", 12))
            self._stats()
            return
        z = float(self.v_zoom.get())
        keep = sc.select_nodes(res, int(self.v_draw.get()))
        pos = sc.layout(res, keep)
        nodes = {}
        todo = [res.root]
        while todo:
            n = todo.pop()
            if n.id in keep:
                nodes[n.id] = n
                todo.extend(n.children)
        labels = {i: self.problem.label(n.state).split("\n") for i, n in nodes.items()}
        maxlen = max(max((len(s) for s in ls), default=3) for ls in labels.values())
        nlines = max(len(ls) for ls in labels.values())
        fs = max(6, int(9 * z))
        cw, lh = fs * 0.72, fs * 1.45
        bw = max(cw * maxlen + 10, 64 * z)
        bh = lh * nlines + 22 * z
        gx, gy = bw + 14 * z, bh + 40 * z
        on_path = {n.id for n in res.path}
        cx = lambda i: 20 + pos[i][0] * gx + bw / 2
        cy = lambda i: 20 + pos[i][1] * gy
        for i, n in nodes.items():
            for c in n.children:
                if c.id in nodes:
                    col, w = ("#1a7f37", 3) if c.id in on_path else ("#999", 1)
                    x1, y1, x2, y2 = cx(i), cy(i) + bh, cx(c.id), cy(c.id)
                    cv.create_line(x1, y1, x2, y2, fill=col, width=w)
                    cv.create_text((x1 + x2) / 2 + 4, (y1 + y2) / 2, anchor="w",
                                   text=self.problem.action_label(c.action),
                                   font=("Helvetica", max(6, int(7 * z))), fill="#666")
        for i, n in nodes.items():
            x, y = cx(i) - bw / 2, cy(i)
            outline, w = ("#1a7f37", 3) if i in on_path else ("#666", 1)
            if self.last is not None and n is self.last:
                outline, w = "#ff8c1a", 4
            cv.create_rectangle(x, y, x + bw, y + bh, fill=sc.STATUS_COLORS[n.status],
                                outline=outline, width=w,
                                dash=(4, 3) if n.status == "duplicate" else None)
            for k, s in enumerate(labels[i]):
                cv.create_text(x + 5, y + 4 + k * lh, anchor="nw", text=s,
                               font=("Courier", fs))
            tag = f"d={n.depth}" + (f" #{n.order_expanded}" if n.order_expanded is not None else "")
            cv.create_text(x + 5, y + bh - 3, anchor="sw", text=tag,
                           font=("Helvetica", max(6, int(7 * z))), fill="#333")
        bbox = cv.bbox("all")
        if bbox:
            W, H = bbox[2] + 30, bbox[3] + 30
            cv.configure(scrollregion=(0, 0, W, H))
            if self.v_follow.get():
                target = self.last if (self.last is not None and self.last.id in nodes) else res.root
                if self.finished and res.solution is not None and res.solution.id in nodes:
                    target = res.solution
                vw, vh = max(cv.winfo_width(), 200), max(cv.winfo_height(), 200)
                cv.xview_moveto(max(0.0, (cx(target.id) - vw / 2) / W))
                cv.yview_moveto(max(0.0, (cy(target.id) - vh / 2) / H))
        total, todo = 0, [res.root]
        while todo:
            m = todo.pop()
            total += 1
            todo.extend(m.children)
        if total > len(nodes) or res.generated > total:
            what = "nodes of the current IDDFS iteration" if self.cfg.algorithm == "iddfs" \
                else "recorded nodes"
            cv.create_text(10, 8, anchor="nw", fill="#a00", font=("Helvetica", 9),
                           text=f"showing {len(nodes)} of {total:,} {what} "
                                f"({res.generated:,} generated in total)")
        self._stats()

    def _stats(self):
        res, s = self.search.res, self.stats
        s["Status"].configure(text=res.status if self.finished else
                              ("running" if self.running else "paused"))
        s["Generated"].configure(text=f"{res.generated:,}")
        s["Expanded"].configure(text=f"{res.expanded:,}")
        s["Pruned (repeated)"].configure(text=f"{res.pruned:,}")
        s["Cutoffs"].configure(text=f"{res.cutoffs:,}")
        fr = getattr(self.search, "frontier", [])
        s["Frontier size"].configure(text=f"{len(fr):,}")
        s["Max frontier"].configure(text=f"{res.max_frontier:,}")
        s["Max depth"].configure(text=f"{res.max_depth}")
        s["Solution length"].configure(text=str(len(res.path) - 1) if res.path else "-")
        s["IDDFS limit"].configure(text="-" if self.iter_L is None else str(self.iter_L))
        end = self.paused_at or time.perf_counter()
        t = end - self.search.start if hasattr(self.search, "start") else 0
        s["Time (s)"].configure(text=f"{max(0.0, t):.3f}")
        # frontier preview
        items = []
        if self.cfg.algorithm == "bfs":
            seq = list(fr)[:8]
            head = "FIFO queue, front first:"
        elif self.cfg.algorithm == "ucs":
            seq = [n for _, _, n in sorted(fr)[:8]]
            head = "priority queue, lowest g first:"
        else:
            seq = list(reversed(fr))[:8]
            head = "LIFO stack, top first:"
        for n in seq:
            lab = self.problem.label(n.state).replace("\n", " / ")
            items.append(f"d={n.depth} g={n.g:g}: {lab[:34]}")
        self.l_front.configure(text=head + "\n" + "\n".join(items) if items else head + "\n(empty)")

    # ------------------------------------------------------------ running
    def step(self):
        if not self.finished:
            self.pause()
            self._advance(1)

    def toggle(self):
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
            self.toggle()

    def pause(self):
        self.running = False
        if hasattr(self, "b_play"):
            self.b_play.configure(text="Play")
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.search is not None:
            self._redraw()

    def _tick(self):
        self.after_id = None
        if not self.running or self.finished:
            return
        d, n = SPEEDS[self.v_speed.get()]
        self._advance(n)
        if self.running and not self.finished:
            self.after_id = self.root.after(d, self._tick)

    def _advance(self, n):
        if self.paused_at is not None and hasattr(self.search, "start"):
            self.search.start += time.perf_counter() - self.paused_at
        self.paused_at = None
        verbose = n <= 10
        done = 0
        while done < n:
            try:
                ev = next(self.gen)
            except StopIteration:
                break
            kind = ev[0]
            if kind == "expand":
                done += 1
                node, children, pruned = ev[1], ev[2], ev[3]
                self.last = node
                if verbose:
                    msg = (f"Expand node #{node.order_expanded} (depth {node.depth}): "
                           f"{len(children)} new children" +
                           (f", {len(pruned)} repeated state(s) pruned" if pruned else "") +
                           ("" if children or pruned else " - dead end"))
                    self._log(msg)
                    self.l_explain.configure(text=msg, fg="#1f5fbf")
            elif kind == "iteration":
                self.iter_L = ev[1]
                self._log(f"=== IDDFS: new depth-limited search with L = {ev[1]} "
                          f"(the tree is built again from the root) ===")
                self.last = None
            elif kind == "cutoff":
                if verbose:
                    self._log(f"Cutoff at depth {ev[1].depth}: limit reached")
                    self.l_explain.configure(text=f"Cutoff: depth limit reached at depth "
                                                  f"{ev[1].depth}", fg="#8e44ad")
                self.last = ev[1]
                done += 1
            elif kind == "goal":
                self._log(f"GOAL found at depth {ev[1].depth}")
            elif kind == "end":
                self._finish(ev[1])
                break
        if self.paused_at is None:
            self.paused_at = time.perf_counter()
        self._redraw()

    def _finish(self, res):
        self.finished = True
        self.running = False
        self.paused_at = time.perf_counter()
        self.b_play.configure(text="Play")
        msg = f"{res.status}: {explain(res)}"
        if res.solution and isinstance(self.problem, wf.Workforce):
            v = self.problem.violations(res.solution.state)
            msg += f" - plan {'VALID' if not v else 'INVALID'}"
        msg += f"  (generated {res.generated:,}, expanded {res.expanded:,})"
        col = {"FOUND": "#1a7f37", "NO_SOLUTION": "#7a3e9d"}.get(res.status, "#c00000")
        self.l_explain.configure(text=msg, fg=col)
        self._log(msg)

    def _log(self, line):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        if int(self.log.index("end-1c").split(".")[0]) > 400:
            self.log.delete("1.0", "101.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def close(self):
        self.pause()
        self.root.destroy()


def main() -> int:
    if tk is None:
        print("tkinter is not available. Install Python from python.org (keep 'tcl/tk and "
              "IDLE' checked).")
        return 1
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
