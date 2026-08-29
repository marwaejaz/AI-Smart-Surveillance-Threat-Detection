"""
analytics_dashboard.py
Week 3 — Advanced Feature: Analytics & Reporting Dashboard

Opens as a separate window from the main dashboard. Reads everything
from the SAME SQLite database (security_system.db) your Week 2 work
already set up — no changes to your camera loop, detector, or tracker.

Shows:
  - Total events + a breakdown by alert type (weapon / suspicious / crowd / zone)
  - A simple bar chart of events per day for the last 7 days (drawn with
    plain Tkinter Canvas — no matplotlib install needed)
  - A manual "Refresh" button

Wire it into dashboard.py with 2 small additions — see WIRING NOTES at
the bottom of this file.
"""

import tkinter as tk
import database as db

db.init_db()  # safe no-op if the table already exists

# Reuse the same palette as dashboard.py so it looks like part of the
# same app instead of a bolted-on extra window.
BG = "#070d1a"
PANEL = "#0d1526"
CARD = "#111f35"
BORDER = "#1e3254"
BORDER2 = "#243d63"
CYAN = "#00e5ff"
GREEN = "#00e676"
RED = "#ff3b3b"
AMBER = "#ffab00"
PURPLE = "#d500f9"
TEXT = "#e8f0fe"
MUTED = "#546e8a"

# alert_type -> (display label, color) — matches the constants already
# used in alert_manager.py (ALERT_WEAPON="weapon", ALERT_SUSPICIOUS=
# "suspicious", ALERT_CROWD="crowd", ALERT_ZONE="zone_breach")
TYPE_STYLE = {
    "weapon":       ("WEAPON", RED),
    "suspicious":   ("SUSPICIOUS", AMBER),
    "crowd":        ("CROWD", PURPLE),
    "zone_breach":  ("ZONE BREACH", CYAN),
}


class AnalyticsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Analytics & Reports")
        self.configure(bg=BG)
        self.geometry("620x560")
        self.minsize(560, 480)

        self._build_ui()
        self.refresh()

    # ── UI ──────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg=PANEL, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📊 ANALYTICS & REPORTS", bg=PANEL, fg=CYAN,
                  font=("Courier", 14, "bold")).pack(side="left", padx=14, pady=12)
        tk.Button(hdr, text="⟳ Refresh", command=self.refresh,
                  bg=CARD, fg=CYAN, font=("Courier", 9, "bold"),
                  relief="flat", padx=10, pady=4, cursor="hand2").pack(side="right", padx=14, pady=10)
        tk.Frame(self, bg=CYAN, height=2).pack(fill="x")

        # Summary cards
        self.cards_frame = tk.Frame(self, bg=BG)
        self.cards_frame.pack(fill="x", padx=14, pady=(14, 6))

        # Chart
        tk.Label(self, text="EVENTS — LAST 7 DAYS", bg=BG, fg=MUTED,
                  font=("Courier", 9, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        chart_card = tk.Frame(self, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        chart_card.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.canvas = tk.Canvas(chart_card, bg=CARD, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas.bind("<Configure>", lambda e: self._draw_chart())

    # ── Data + drawing ─────────────────────────────────────────────
    def refresh(self):
        self.total, self.by_type = db.get_summary_counts()
        self.daily = db.get_daily_counts(7)
        self._draw_cards()
        self._draw_chart()

    def _draw_cards(self):
        for w in self.cards_frame.winfo_children():
            w.destroy()

        specs = [
            ("TOTAL EVENTS", self.total, TEXT),
        ]
        for key, (label, color) in TYPE_STYLE.items():
            specs.append((label, self.by_type.get(key, 0), color))

        cols = 3
        for i, (label, value, color) in enumerate(specs):
            r, c = divmod(i, cols)
            card = tk.Frame(self.cards_frame, bg=CARD, padx=10, pady=8,
                              highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
            self.cards_frame.grid_columnconfigure(c, weight=1)
            tk.Label(card, text=label, bg=CARD, fg=MUTED,
                      font=("Courier", 8)).pack(anchor="w")
            tk.Label(card, text=str(value), bg=CARD, fg=color,
                      font=("Courier", 22, "bold")).pack(anchor="w")

    def _draw_chart(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 20 or h < 20 or not self.daily:
            return

        pad_left, pad_bottom, pad_top = 34, 26, 10
        chart_w = w - pad_left - 10
        chart_h = h - pad_bottom - pad_top
        max_count = max((c for _, c in self.daily), default=0)
        max_count = max(max_count, 1)  # avoid divide-by-zero when all-zero

        n = len(self.daily)
        gap = 14
        bar_w = max(10, (chart_w - gap * (n - 1)) / n)

        # y-axis gridlines (0, half, max)
        for frac in (0, 0.5, 1.0):
            y = pad_top + chart_h - frac * chart_h
            self.canvas.create_line(pad_left, y, w - 10, y, fill=BORDER)
            self.canvas.create_text(pad_left - 6, y, text=str(int(max_count * frac)),
                                     fill=MUTED, font=("Courier", 8), anchor="e")

        x = pad_left
        for date_str, count in self.daily:
            bar_h = (count / max_count) * chart_h if max_count else 0
            y0 = pad_top + chart_h - bar_h
            y1 = pad_top + chart_h
            color = CYAN if count > 0 else BORDER
            self.canvas.create_rectangle(x, y0, x + bar_w, y1, fill=color, outline="")
            if count > 0:
                self.canvas.create_text(x + bar_w / 2, y0 - 8, text=str(count),
                                         fill=TEXT, font=("Courier", 9, "bold"))
            # short label: just day-of-month, keeps it readable at 7 bars
            day_label = date_str[-2:]
            self.canvas.create_text(x + bar_w / 2, pad_top + chart_h + 12,
                                     text=day_label, fill=MUTED, font=("Courier", 8))
            x += bar_w + gap


# ─────────────────────────────────────────────────────────────────────
# WIRING NOTES — two small edits to dashboard.py, nothing else changes
# ─────────────────────────────────────────────────────────────────────
#
# 1) Near the top, alongside your other local imports:
#
#       from analytics_dashboard import AnalyticsWindow
#
# 2) In SurveillanceDashboard._build_ui(), find the row where
#    "🗑 Clear Zones" is added (inside the `bottom` controls bar), and
#    add one more button right after it:
#
#       ctrl_btn(bottom, "📊 Analytics", self._open_analytics, fg=CYAN).pack(
#           side="left", padx=4, pady=10)
#
#    Then add this method anywhere inside the SurveillanceDashboard class
#    (e.g. right next to _open_snapshots):
#
#       def _open_analytics(self):
#           AnalyticsWindow(self.root)
#
# That's it — no changes to detector.py, tracker.py, alert_manager.py,
# or your camera capture loop. The button opens a separate window that
# only reads from security_system.db.
