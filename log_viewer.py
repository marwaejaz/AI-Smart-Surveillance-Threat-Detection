"""
log_viewer.py
Week 3 — Advanced Feature: Searchable Incident Log Viewer

A pop-up window that lets you search and filter your alert history by
keyword or alert type. Uses your EXISTING database.get_logs() function
— no changes to database.py needed for this one.

Wire it into dashboard.py with 2 small additions — see WIRING NOTES at
the bottom of this file.
"""

import tkinter as tk
from tkinter import ttk
import database as db

BG = "#070d1a"
PANEL = "#0d1526"
CARD = "#111f35"
BORDER = "#1e3254"
CYAN = "#00e5ff"
RED = "#ff3b3b"
AMBER = "#ffab00"
PURPLE = "#d500f9"
TEXT = "#e8f0fe"
MUTED = "#546e8a"

TYPE_OPTIONS = ["All", "weapon", "suspicious", "crowd", "zone_breach"]
TYPE_COLOR = {
    "weapon": RED, "suspicious": AMBER, "crowd": PURPLE, "zone_breach": CYAN,
}


class LogViewerWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Incident Log Search")
        self.configure(bg=BG)
        self.geometry("760x520")
        self.minsize(600, 400)

        self.all_logs = []
        self._build_ui()
        self.refresh()

    # ── UI ──────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg=PANEL, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔍 INCIDENT LOG SEARCH", bg=PANEL, fg=CYAN,
                  font=("Courier", 14, "bold")).pack(side="left", padx=14, pady=12)
        tk.Button(hdr, text="⟳ Refresh", command=self.refresh,
                  bg=CARD, fg=CYAN, font=("Courier", 9, "bold"),
                  relief="flat", padx=10, pady=4, cursor="hand2").pack(side="right", padx=14, pady=10)
        tk.Frame(self, bg=CYAN, height=2).pack(fill="x")

        # Search bar
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=14, pady=12)

        tk.Label(bar, text="Search:", bg=BG, fg=MUTED,
                  font=("Courier", 9)).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._apply_filter())
        entry = tk.Entry(bar, textvariable=self.search_var, bg=CARD, fg=TEXT,
                          insertbackground=TEXT, relief="flat",
                          font=("Courier", 10), width=30)
        entry.pack(side="left", padx=(6, 18), ipady=4)

        tk.Label(bar, text="Type:", bg=BG, fg=MUTED,
                  font=("Courier", 9)).pack(side="left")
        self.type_var = tk.StringVar(value="All")
        type_menu = ttk.Combobox(bar, textvariable=self.type_var, values=TYPE_OPTIONS,
                                  state="readonly", width=14, font=("Courier", 9))
        type_menu.pack(side="left", padx=6)
        type_menu.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        self.count_lbl = tk.Label(bar, text="", bg=BG, fg=MUTED, font=("Courier", 9))
        self.count_lbl.pack(side="right")

        # Results table
        table_card = tk.Frame(self, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        table_card.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Log.Treeview", background=CARD, fieldbackground=CARD,
                         foreground=TEXT, rowheight=26, borderwidth=0, font=("Courier", 9))
        style.configure("Log.Treeview.Heading", background=PANEL, foreground=CYAN,
                         font=("Courier", 9, "bold"), relief="flat")
        style.map("Log.Treeview", background=[("selected", "#1c3a5e")])

        cols = ("time", "type", "detail")
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings",
                                  style="Log.Treeview")
        self.tree.heading("time", text="TIMESTAMP")
        self.tree.heading("type", text="TYPE")
        self.tree.heading("detail", text="DETAIL")
        self.tree.column("time", width=150, anchor="w")
        self.tree.column("type", width=110, anchor="w")
        self.tree.column("detail", width=380, anchor="w")

        vsb = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        vsb.pack(side="right", fill="y", pady=10)

        for t, color in TYPE_COLOR.items():
            self.tree.tag_configure(t, foreground=color)

    # ── Data ────────────────────────────────────────────────────────
    def refresh(self):
        self.all_logs = db.get_logs(limit=1000)
        self._apply_filter()

    def _apply_filter(self):
        search_text = self.search_var.get().strip().lower()
        type_filter = self.type_var.get()

        for row in self.tree.get_children():
            self.tree.delete(row)

        shown = 0
        for ts, alert_type, detail, snapshot in self.all_logs:
            if type_filter != "All" and alert_type != type_filter:
                continue
            detail = detail or ""
            if search_text and search_text not in detail.lower() and search_text not in alert_type.lower():
                continue
            tag = alert_type if alert_type in TYPE_COLOR else ""
            self.tree.insert("", "end", values=(ts, alert_type.upper(), detail), tags=(tag,))
            shown += 1

        self.count_lbl.config(text=f"{shown} of {len(self.all_logs)} events")


