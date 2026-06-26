import tkinter as tk
from tkinter import simpledialog, messagebox
import cv2, threading, time, os, queue
from PIL import Image, ImageTk

from detector import Detector
from tracker import SuspiciousTracker
from alert_manager import AlertManager, SETTINGS

# ── Cyber dark theme ──────────────────────────────────────────────────────────
BG       = "#070d1a"
PANEL    = "#0d1526"
CARD     = "#111f35"
CARD2    = "#162440"
BORDER   = "#1e3254"
BORDER2  = "#243d63"
RED      = "#ff3b3b"; RED_D  = "#c41c1c"
GREEN    = "#00e676"; GREEN_D= "#00a152"
AMBER    = "#ffab00"; AMBER_D= "#c67c00"
BLUE     = "#2979ff"; BLUE_D = "#1a52c8"
CYAN     = "#00e5ff"; CYAN_D = "#00b2cc"
PURPLE   = "#d500f9"; PURP_D = "#9c00b8"
PINK     = "#ff4081"
TEXT     = "#e8f0fe"
MUTED    = "#546e8a"
WHITE    = "#ffffff"

CROWD_THRESHOLD = 4


class LoginScreen:
    """Password gate before main dashboard"""
    CORRECT_PASSWORD = "admin123"

    def __init__(self, on_success):
        self.on_success = on_success
        self.root = tk.Tk()
        self.root.title("AI Surveillance — Login")
        self.root.configure(bg=BG)
        self.root.geometry("440x340")
        self.root.resizable(False, False)
        self._build()

    def _build(self):
        tk.Label(self.root, text="🔒", font=("Arial", 44), bg=BG, fg=CYAN).pack(pady=(36,6))
        tk.Label(self.root, text="AI SURVEILLANCE SYSTEM", font=("Courier",15,"bold"),
                 bg=BG, fg=CYAN).pack()
        tk.Label(self.root, text="Authorized Access Only", font=("Courier",10),
                 bg=BG, fg=MUTED).pack(pady=(4,24))

        frm = tk.Frame(self.root, bg=BG)
        frm.pack()
        tk.Label(frm, text="Password:", font=("Courier",11), bg=BG, fg=TEXT).grid(row=0, column=0, padx=8, pady=6, sticky="e")
        self.pwd_var = tk.StringVar()
        e = tk.Entry(frm, textvariable=self.pwd_var, show="●",
                     font=("Courier",12), bg=CARD, fg=TEXT, insertbackground=CYAN,
                     relief="flat", bd=0, width=18)
        e.grid(row=0, column=1, padx=8, ipady=7)
        e.bind("<Return>", lambda _: self._login())
        e.focus()

        self.err_lbl = tk.Label(self.root, text="", font=("Courier",10), bg=BG, fg=RED)
        self.err_lbl.pack(pady=4)

        tk.Button(self.root, text="LOGIN  →",
                  bg=CYAN, fg="#000", font=("Courier",12,"bold"),
                  relief="flat", padx=28, pady=8, cursor="hand2",
                  command=self._login).pack(pady=4)

    def _login(self):
        if self.pwd_var.get() == self.CORRECT_PASSWORD:
            self.root.destroy()
            self.on_success()
        else:
            self.err_lbl.config(text="⚠  Incorrect password. Try again.")
            self.pwd_var.set("")

    def run(self):
        self.root.mainloop()


class SurveillanceDashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Smart Surveillance System — ADVANCED v2.0")
        self.root.configure(bg=BG)
        self.root.geometry("1440x860")
        self.root.resizable(True, True)

        self.detector  = Detector(confidence=SETTINGS["confidence"])
        self.tracker   = SuspiciousTracker()
        self.alert_mgr = AlertManager()

        self.cap          = None
        self.cap2         = None
        self.running      = False
        self.frame_queue  = queue.Queue(maxsize=2)
        self.frame_queue2 = queue.Queue(maxsize=2)
        self.dual_cam     = False
        self.heatmap_mode = False

        self.stats = {"persons":0,"weapons":0,"suspicious":0,"alerts":0,"snapshots":0,"zones":0}
        self._fps_start  = time.time()
        self._fps_count  = 0
        self._start_time = None

        self._drawing_zone = False
        self._zone_start   = None
        self._zone_name    = ""

        # Alert toast queue
        self._toasts = []

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────────────────────────────────────
    # UI BUILD
    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=PANEL, height=58)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        # Blinking dot
        self.dot_lbl = tk.Label(hdr, text="⬤", bg=PANEL, fg=RED, font=("Arial",12))
        self.dot_lbl.pack(side="left", padx=(16,4), pady=16)
        self._blink_dot()

        tk.Label(hdr, text="AI SMART SURVEILLANCE — ADVANCED",
                 bg=PANEL, fg=CYAN, font=("Courier",17,"bold")).pack(side="left", pady=16)

        # Right side info
        self.clock_lbl = tk.Label(hdr, bg=PANEL, fg=MUTED, font=("Courier",11))
        self.clock_lbl.pack(side="right", padx=16)
        self._tick_clock()

        self.uptime_lbl = tk.Label(hdr, bg=PANEL, fg=MUTED, font=("Courier",10))
        self.uptime_lbl.pack(side="right", padx=8)

        self.status_badge = tk.Label(hdr, text="  ⬤  OFFLINE  ",
                                     bg=RED_D, fg=WHITE, font=("Courier",10,"bold"), padx=10, pady=4)
        self.status_badge.pack(side="right", padx=12, pady=12)

        tk.Frame(self.root, bg=CYAN, height=2).pack(fill="x", side="top")

        # ── Bottom controls ────────────────────────────────────────────────────
        bottom = tk.Frame(self.root, bg=PANEL, height=56)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", side="bottom")

        def ctrl_btn(parent, text, cmd, bg=CARD2, fg=TEXT, state="normal"):
            return tk.Button(parent, text=text, command=cmd,
                             bg=bg, fg=fg, font=("Courier",10,"bold"),
                             relief="flat", padx=14, pady=8, cursor="hand2",
                             state=state, activebackground=BORDER2)

        self.btn_start = ctrl_btn(bottom, "▶  START", self._start_camera, bg=GREEN_D, fg="#000")
        self.btn_start.pack(side="left", padx=(14,4), pady=10)

        self.btn_stop = ctrl_btn(bottom, "■  STOP", self._stop_camera, state="disabled")
        self.btn_stop.pack(side="left", padx=4, pady=10)

        tk.Frame(bottom, bg=BORDER, width=1).pack(side="left", fill="y", padx=10, pady=10)

        self.btn_zone = ctrl_btn(bottom, "📐  Draw Zone", self._start_zone_draw, fg=CYAN)
        self.btn_zone.pack(side="left", padx=4, pady=10)

        ctrl_btn(bottom, "🗑  Clear Zones", self._clear_zones, fg=MUTED).pack(side="left", padx=4, pady=10)

        tk.Frame(bottom, bg=BORDER, width=1).pack(side="left", fill="y", padx=10, pady=10)

        # Toggles
        for text, var_name, cmd, col in [
            ("🌙 Night", "_night_var", self._toggle_night, CYAN),
            ("🔥 Heatmap", "_heat_var", self._toggle_heatmap, AMBER),
            ("📷 Dual Cam", "_dual_var", self._toggle_dual, PURPLE),
        ]:
            var = tk.BooleanVar(value=False)
            setattr(self, var_name, var)
            tk.Checkbutton(bottom, text=text, variable=var,
                           bg=PANEL, fg=col, selectcolor=CARD,
                           activebackground=PANEL, font=("Courier",10,"bold"),
                           cursor="hand2", command=cmd).pack(side="left", padx=6, pady=10)

        self.fps_lbl = tk.Label(bottom, text="FPS: --  |  CPU", bg=PANEL, fg=MUTED, font=("Courier",10))
        self.fps_lbl.pack(side="right", padx=16)

        self.zone_hint = tk.Label(bottom, text="", bg=PANEL, fg=CYAN, font=("Courier",9))
        self.zone_hint.pack(side="right", padx=8)

        # ── Middle body ────────────────────────────────────────────────────────
        middle = tk.Frame(self.root, bg=BG)
        middle.pack(fill="both", expand=True)
        self._build_video_panel(middle)
        self._build_right_panel(middle)

    # ── Video Panel ───────────────────────────────────────────────────────────
    def _build_video_panel(self, parent):
        self.vid_outer = tk.Frame(parent, bg=BG)
        self.vid_outer.pack(side="left", fill="both", expand=True, padx=(10,5), pady=8)

        top = tk.Frame(self.vid_outer, bg=BG)
        top.pack(fill="x", pady=(0,4))
        tk.Label(top, text="LIVE FEED", bg=BG, fg=MUTED, font=("Courier",9,"bold")).pack(side="left")
        self.scan_lbl = tk.Label(top, text="◉ SCANNING", bg=BG, fg=GREEN, font=("Courier",9))
        self.scan_lbl.pack(side="right")

        # Camera 1
        self.cam1_frame = tk.Frame(self.vid_outer, bg=BG)
        self.cam1_frame.pack(fill="both", expand=True)

        b1 = tk.Frame(self.cam1_frame, bg=BORDER2, padx=2, pady=2)
        b1.pack(fill="both", expand=True)
        self.video_lbl = tk.Label(b1, bg="#020810",
                                  text="[ SYSTEM OFFLINE ]", fg=MUTED,
                                  font=("Courier",16), cursor="crosshair")
        self.video_lbl.pack(fill="both", expand=True)
        self.video_lbl.bind("<ButtonPress-1>",  self._zone_press)
        self.video_lbl.bind("<B1-Motion>",       self._zone_drag)
        self.video_lbl.bind("<ButtonRelease-1>", self._zone_release)

        # Camera 2 (hidden)
        self._cam2_container = tk.Frame(self.vid_outer, bg=BG)
        b2 = tk.Frame(self._cam2_container, bg=BORDER2, padx=2, pady=2)
        b2.pack(fill="both", expand=True)
        self.video_lbl2 = tk.Label(b2, bg="#020810", text="[ CAM 2 ]", fg=MUTED, font=("Courier",12))
        self.video_lbl2.pack(fill="both", expand=True)

    # ── Right Panel ───────────────────────────────────────────────────────────
    def _build_right_panel(self, parent):
        right = tk.Frame(parent, bg=BG, width=340)
        right.pack(side="right", fill="y", padx=(0,10), pady=8)
        right.pack_propagate(False)

        # Stats grid
        tk.Label(right, text="DETECTION STATS", bg=BG, fg=MUTED,
                 font=("Courier",8,"bold")).pack(anchor="w", pady=(0,5))

        grid = tk.Frame(right, bg=BG)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self.var_persons    = tk.StringVar(value="0")
        self.var_weapons    = tk.StringVar(value="0")
        self.var_suspicious = tk.StringVar(value="0")
        self.var_alerts     = tk.StringVar(value="0")
        self.var_snapshots  = tk.StringVar(value="0")
        self.var_zones      = tk.StringVar(value="0")

        self._stat(grid, "👤 PERSONS",    self.var_persons,    GREEN,  0, 0)
        self._stat(grid, "🔪 WEAPONS",    self.var_weapons,    RED,    0, 1)
        self._stat(grid, "⚠  SUSPICIOUS", self.var_suspicious, AMBER,  1, 0)
        self._stat(grid, "🔔 ALERTS",     self.var_alerts,     BLUE,   1, 1)
        self._stat(grid, "📸 SNAPSHOTS",  self.var_snapshots,  CYAN,   2, 0)
        self._stat(grid, "📐 ZONES",      self.var_zones,      PURPLE, 2, 1)

        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", pady=8)

        # Active alert box (glowing)
        tk.Label(right, text="ACTIVE ALERT", bg=BG, fg=MUTED,
                 font=("Courier",8,"bold")).pack(anchor="w", pady=(0,4))
        self.active_frame = tk.Frame(right, bg=CARD, padx=10, pady=10, highlightthickness=2,
                                     highlightbackground=BORDER2, highlightcolor=BORDER2)
        self.active_frame.pack(fill="x")
        self.active_lbl = tk.Label(self.active_frame, text="System nominal — no alerts",
                                   bg=CARD, fg=MUTED, font=("Courier",10),
                                   wraplength=290, justify="left", anchor="w")
        self.active_lbl.pack(fill="x")

        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", pady=8)

        # Settings quick panel
        tk.Label(right, text="QUICK SETTINGS", bg=BG, fg=MUTED,
                 font=("Courier",8,"bold")).pack(anchor="w", pady=(0,4))
        sfrm = tk.Frame(right, bg=CARD, padx=10, pady=8)
        sfrm.pack(fill="x")

        def setting_row(parent, label, var, from_, to_, col=TEXT):
            row = tk.Frame(parent, bg=CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, bg=CARD, fg=MUTED, font=("Courier",8), width=16, anchor="w").pack(side="left")
            tk.Scale(row, variable=var, from_=from_, to=to_,
                     orient="horizontal", bg=CARD, fg=col,
                     troughcolor=BORDER, highlightthickness=0,
                     font=("Courier",8), length=140, showvalue=True,
                     activebackground=col).pack(side="left")

        self._conf_var = tk.DoubleVar(value=40)
        self._crowd_var= tk.IntVar(value=4)
        self._susp_var = tk.IntVar(value=10)
        setting_row(sfrm, "Confidence %", self._conf_var, 20, 80, CYAN)
        setting_row(sfrm, "Crowd limit",  self._crowd_var, 2, 10, AMBER)
        setting_row(sfrm, "Suspicious s", self._susp_var,  5, 30, PURPLE)

        tk.Button(sfrm, text="Apply", bg=CYAN, fg="#000",
                  font=("Courier",9,"bold"), relief="flat", cursor="hand2",
                  command=self._apply_settings).pack(anchor="e", pady=(4,0))

        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", pady=8)

        # Alert log
        tk.Label(right, text="ALERT LOG", bg=BG, fg=MUTED,
                 font=("Courier",8,"bold")).pack(anchor="w", pady=(0,4))

        log_frm = tk.Frame(right, bg=CARD)
        log_frm.pack(fill="both", expand=True)
        sb = tk.Scrollbar(log_frm, bg=CARD, troughcolor=CARD)
        sb.pack(side="right", fill="y")
        self.log_box = tk.Listbox(
            log_frm, bg=CARD, fg=TEXT, font=("Courier",9),
            relief="flat", bd=0, selectbackground=BORDER2,
            activestyle="none", yscrollcommand=sb.set, highlightthickness=0
        )
        self.log_box.pack(fill="both", expand=True, padx=4, pady=4)
        sb.config(command=self.log_box.yview)

        btn_row = tk.Frame(right, bg=BG)
        btn_row.pack(fill="x", pady=(4,0))
        tk.Button(btn_row, text="🗑 Clear", bg=CARD, fg=MUTED,
                  font=("Courier",9), relief="flat", pady=4,
                  cursor="hand2", command=self._clear_log,
                  activebackground=BORDER2).pack(side="left", fill="x", expand=True, padx=(0,4))
        tk.Button(btn_row, text="📂 Snapshots", bg=CARD, fg=CYAN,
                  font=("Courier",9), relief="flat", pady=4,
                  cursor="hand2", command=self._open_snapshots,
                  activebackground=BORDER2).pack(side="left", fill="x", expand=True)

    def _stat(self, parent, title, var, color, row, col):
        c = tk.Frame(parent, bg=CARD, padx=10, pady=10,
                     highlightbackground=BORDER, highlightthickness=1)
        c.grid(row=row, column=col, sticky="nsew",
               padx=(0,4) if col==0 else 0, pady=(0,4))
        tk.Label(c, text=title, bg=CARD, fg=MUTED, font=("Courier",8)).pack(anchor="w")
        tk.Label(c, textvariable=var, bg=CARD, fg=color,
                 font=("Courier",28,"bold")).pack(anchor="w")

    # ─────────────────────────────────────────────────────────────────────────
    # SETTINGS
    # ─────────────────────────────────────────────────────────────────────────
    def _apply_settings(self):
        self.detector.confidence = self._conf_var.get() / 100.0
        SETTINGS["crowd_threshold"] = self._crowd_var.get()
        SETTINGS["suspicious_time"] = self._susp_var.get()
        self.tracker.SUSPICIOUS_TIME = self._susp_var.get()
        self._log("⚙ Settings applied", CYAN)

    # ─────────────────────────────────────────────────────────────────────────
    # ZONE DRAWING
    # ─────────────────────────────────────────────────────────────────────────
    def _start_zone_draw(self):
        if not self.running:
            messagebox.showinfo("Info", "Pehle camera start karo!")
            return
        name = simpledialog.askstring("Zone Name", "Zone name (e.g. Entry, Restricted, Door):")
        if not name: return
        self._zone_name    = name
        self._drawing_zone = True
        self.zone_hint.config(text=f"Drawing: {name} — click & drag on video")

    def _zone_press(self, e):
        if self._drawing_zone: self._zone_start = (e.x, e.y)

    def _zone_drag(self, e):
        if not self._drawing_zone or not self._zone_start: return
        w = abs(e.x - self._zone_start[0]); h2 = abs(e.y - self._zone_start[1])
        self.zone_hint.config(text=f"Zone '{self._zone_name}': {w}×{h2}px — release to confirm")

    def _zone_release(self, e):
        if not self._drawing_zone or not self._zone_start: return
        x1,y1 = self._zone_start; x2,y2 = e.x, e.y
        if abs(x2-x1) < 20 or abs(y2-y1) < 20:
            self.zone_hint.config(text="Zone too small — try again"); self._drawing_zone = False; return
        lw = self.video_lbl.winfo_width()  or 640
        lh = self.video_lbl.winfo_height() or 480
        cap_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))  if self.cap else 640
        cap_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if self.cap else 480
        sx,sy = cap_w/lw, cap_h/lh
        fx1,fy1 = int(min(x1,x2)*sx), int(min(y1,y2)*sy)
        fx2,fy2 = int(max(x1,x2)*sx), int(max(y1,y2)*sy)
        self.detector.add_zone(self._zone_name, (fx1,fy1,fx2,fy2))
        self.stats["zones"] = len(self.detector.zones)
        self.var_zones.set(str(self.stats["zones"]))
        self._log(f"📐 Zone added: {self._zone_name}", PURPLE)
        self.zone_hint.config(text=f"✓ Zone '{self._zone_name}' active!")
        self._drawing_zone = False

    def _clear_zones(self):
        self.detector.clear_zones()
        self.var_zones.set("0"); self.stats["zones"] = 0
        self.zone_hint.config(text=""); self._log("🗑 Zones cleared", MUTED)

    # ─────────────────────────────────────────────────────────────────────────
    # TOGGLES
    # ─────────────────────────────────────────────────────────────────────────
    def _toggle_night(self):
        self.detector.night_mode = self._night_var.get()
        self._log(f"🌙 Night mode {'ON' if self.detector.night_mode else 'OFF'}", CYAN)

    def _toggle_heatmap(self):
        self.heatmap_mode = self._heat_var.get()
        self._log(f"🔥 Heatmap {'ON' if self.heatmap_mode else 'OFF'}", AMBER)

    def _toggle_dual(self):
        self.dual_cam = self._dual_var.get()
        if self.dual_cam:
            self._cam2_container.pack(fill="both", expand=True, pady=(4,0))
        else:
            self._cam2_container.pack_forget()
            if self.cap2: self.cap2.release(); self.cap2 = None

    # ─────────────────────────────────────────────────────────────────────────
    # CAMERA
    # ─────────────────────────────────────────────────────────────────────────
    def _start_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self._log("❌ Camera nahi khuli!", RED); return
        if self.dual_cam:
            self.cap2 = cv2.VideoCapture(1)
        self.running      = True
        self._start_time  = time.time()
        self._fps_start   = time.time()
        self._fps_count   = 0
        self.btn_start.config(state="disabled", bg=CARD2, fg=MUTED)
        self.btn_stop.config(state="normal", bg=RED_D, fg=WHITE)
        self.status_badge.config(text="  ⬤  LIVE  ", bg=GREEN_D, fg="#000")
        self.dot_lbl.config(fg=GREEN)
        threading.Thread(target=self._capture_loop, daemon=True).start()
        if self.dual_cam and self.cap2 and self.cap2.isOpened():
            threading.Thread(target=self._capture_loop2, daemon=True).start()
        self._ui_loop()
        self._uptime_loop()

    def _stop_camera(self):
        self.running = False
        if self.cap:  self.cap.release()
        if self.cap2: self.cap2.release()
        self.btn_start.config(state="normal", bg=GREEN_D, fg="#000")
        self.btn_stop.config(state="disabled", bg=CARD2, fg=MUTED)
        self.status_badge.config(text="  ⬤  OFFLINE  ", bg=RED_D, fg=WHITE)
        self.dot_lbl.config(fg=RED)
        self.video_lbl.config(image="", text="[ SYSTEM OFFLINE ]")
        self.stats["persons"] = 0; self.var_persons.set("0")
        self._start_time = None

    # ─────────────────────────────────────────────────────────────────────────
    # CAPTURE LOOP
    # ─────────────────────────────────────────────────────────────────────────
    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret: break

            detections = self.detector.detect(frame)
            persons    = [d for d in detections if d["is_person"]]
            weapons    = [d for d in detections if d["is_dangerous"]]

            # Weapon — FORAN
            for w in weapons:
                self.alert_mgr.weapon_alert(w["label"], frame.copy())
                self.stats["weapons"]   += 1
                self.stats["alerts"]    += 1
                self.stats["snapshots"] += 1
                self._log(f"🔪 WEAPON: {w['label'].upper()}", RED)

            # Crowd
            if len(persons) >= SETTINGS["crowd_threshold"]:
                self.alert_mgr.crowd_alert(len(persons), frame.copy())
                self.stats["alerts"] += 1
                self._log(f"👥 CROWD: {len(persons)} persons!", PURPLE)

            # Suspicious behavior tracking
            tracked = self.tracker.update(persons)
            for det, tinfo, tid in tracked:
                if tinfo["suspicious"] and not tinfo["alerted"]:
                    self.alert_mgr.suspicious_alert(tid, frame.copy())
                    self.tracker.mark_alerted(tid)
                    self.stats["suspicious"] += 1
                    self.stats["alerts"]     += 1
                    self.stats["snapshots"]  += 1
                    self._log(f"⚠ SUSPICIOUS: Person #{tid}", AMBER)

            # ── ZONE BREACH — check ALL detections (person + any object) ──────
            # Collect which zones are currently breached by ANY object
            currently_breached = set()
            for det in detections:   # ALL objects, not just persons
                for zname in (det.get("zone_breached") or []):
                    currently_breached.add(zname)

            # Also check non-person objects manually
            for det in detections:
                if not det["is_person"]:
                    # Check if any part of this object bbox is in a zone
                    x1,y1,x2,y2 = det["bbox"]
                    for z in self.detector.zones:
                        if not z["active"]: continue
                        zx1,zy1,zx2,zy2 = z["rect"]
                        # Check overlap
                        if not (x2 < zx1 or x1 > zx2 or y2 < zy1 or y1 > zy2):
                            currently_breached.add(z["name"])

            # Fire zone alerts
            for z in self.detector.zones:
                zname = z["name"]
                in_zone = zname in currently_breached
                self.alert_mgr.zone_breach_update(zname, in_zone, frame.copy())
                if in_zone:
                    dur = self.alert_mgr.get_zone_duration(zname)
                    if dur > 0 and int(dur) % 3 == 0:  # har 3 sec log update
                        self._log(f"📐 ZONE: {zname} ({int(dur)}s)", PINK)

            self.stats["persons"] = len(persons)
            self._fps_count += 1

            # Heatmap
            if self.heatmap_mode:
                self.detector.update_heatmap(frame, persons)
                frame = self.detector.get_heatmap_overlay(frame)

            frame = self.detector.draw(frame, detections)
            if not self.frame_queue.full():
                self.frame_queue.put(frame)

    def _capture_loop2(self):
        while self.running and self.cap2:
            ret, frame = self.cap2.read()
            if not ret: break
            detections = self.detector.detect(frame)
            frame = self.detector.draw(frame, detections)
            if not self.frame_queue2.full():
                self.frame_queue2.put(frame)

    # ─────────────────────────────────────────────────────────────────────────
    # UI LOOPS
    # ─────────────────────────────────────────────────────────────────────────
    def _ui_loop(self):
        if not self.running: return
        self._update_video(self.video_lbl, self.frame_queue)
        if self.dual_cam:
            self._update_video(self.video_lbl2, self.frame_queue2)

        self.var_persons.set(str(self.stats["persons"]))
        self.var_weapons.set(str(self.stats["weapons"]))
        self.var_suspicious.set(str(self.stats["suspicious"]))
        self.var_alerts.set(str(self.stats["alerts"]))
        self.var_snapshots.set(str(self.stats.get("snapshots",0)))

        elapsed = time.time() - self._fps_start
        if elapsed >= 1.0:
            self.fps_lbl.config(text=f"FPS: {self._fps_count/elapsed:.1f}  |  CPU")
            self._fps_count = 0; self._fps_start = time.time()

        notes = self.alert_mgr.get_active_notifications()
        if notes:
            n = notes[-1]
            color = "#{:02x}{:02x}{:02x}".format(*n["color"])
            self.active_lbl.config(text=f"[{n['time']}]\n{n['msg']}", fg=color)
            self.active_frame.config(highlightbackground=color, highlightcolor=color)
        else:
            self.active_lbl.config(text="System nominal — no alerts", fg=MUTED)
            self.active_frame.config(highlightbackground=BORDER2, highlightcolor=BORDER2)

        self.root.after(30, self._ui_loop)

    def _update_video(self, lbl, q):
        try:
            frame = q.get_nowait()
            lw = max(lbl.winfo_width(), 480); lh = max(lbl.winfo_height(), 360)
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img   = Image.fromarray(rgb).resize((lw, lh), Image.LANCZOS)
            imgtk = ImageTk.PhotoImage(image=img)
            lbl.imgtk = imgtk
            lbl.config(image=imgtk, text="")
        except queue.Empty:
            pass

    def _uptime_loop(self):
        if not self.running or not self._start_time: return
        elapsed = int(time.time() - self._start_time)
        h,m,s   = elapsed//3600, (elapsed%3600)//60, elapsed%60
        self.uptime_lbl.config(text=f"Uptime: {h:02d}:{m:02d}:{s:02d}  |")
        self.root.after(1000, self._uptime_loop)

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def _log(self, msg, color=None):
        ts = time.strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {msg}")
        if color: self.log_box.itemconfig(self.log_box.size()-1, fg=color)
        self.log_box.see("end")

    def _clear_log(self): self.log_box.delete(0, "end")

    def _open_snapshots(self):
        path = os.path.join(os.path.dirname(__file__), "snapshots")
        os.makedirs(path, exist_ok=True)
        os.startfile(path)

    def _blink_dot(self):
        current = self.dot_lbl.cget("fg")
        new_color = MUTED if current != MUTED else (GREEN if self.running else RED)
        self.dot_lbl.config(fg=new_color)
        self.root.after(600, self._blink_dot)

    def _tick_clock(self):
        self.clock_lbl.config(text=time.strftime("  %H:%M:%S  |  %d %b %Y"))
        self.root.after(1000, self._tick_clock)

    def _on_close(self):
        self._stop_camera(); self.root.destroy()

    def run(self):
        self.root.mainloop()
