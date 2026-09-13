import database
import time, threading, os, csv, smtplib, cv2
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from dotenv import load_dotenv
load_dotenv()

try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.mixer.init()
    PYGAME_OK = True
except:
    PYGAME_OK = False

try:
    import pyttsx3
    TTS_OK = True
except:
    TTS_OK = False
    print("[TTS] pyttsx3 not available — no voice alerts")

SOUNDS_DIR    = os.path.join(os.path.dirname(__file__), "sounds")
SNAPSHOTS_DIR = os.path.join(os.path.dirname(__file__), "snapshots")
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

ALERT_WEAPON     = "weapon"
ALERT_SUSPICIOUS = "suspicious"
ALERT_CROWD      = "crowd"
ALERT_ZONE       = "zone_breach"

EMAIL_CONFIG = {
    "enabled":   False,
    "sender":    os.getenv("SENDER_EMAIL", "your_gmail@gmail.com"),
    "password":  os.getenv("SENDER_PASSWORD", "your_app_password"),
    "receiver":  os.getenv("RECEIVER_EMAIL", "alert_receiver@gmail.com"),
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
}
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
SETTINGS = {
    "crowd_threshold": 4,
    "suspicious_time": 10,
    "zone_warn_time":  10,
    "confidence":      0.40,
}


class AlertManager:
    WEAPON_COOLDOWN     = 6
    SUSPICIOUS_COOLDOWN = 10
    CROWD_COOLDOWN      = 8
    ZONE_COOLDOWN       = 4

    def __init__(self):
        self._last = {k: 0 for k in [ALERT_WEAPON, ALERT_SUSPICIOUS, ALERT_CROWD, ALERT_ZONE]}
        self.notifications  = []
        self._sounds        = {}
        self._tts_busy      = False
        self._zone_first    = {}   # zone_name -> first_seen time
        self._zone_escalated= {}   # zone_name -> bool
        self._load_sounds()
        self._init_log()

    # ── Sound ────────────────────────────────────────────────────────────────
    def _load_sounds(self):
        if not PYGAME_OK: return
        files = {
            ALERT_WEAPON:     "weapon_alert.wav",
            ALERT_SUSPICIOUS: "suspicious_alert.wav",
            ALERT_CROWD:      "crowd_alert.wav",
            ALERT_ZONE:       "zone_alert.wav",
        }
        for key, fname in files.items():
            path = os.path.join(SOUNDS_DIR, fname)
            if os.path.exists(path):
                try:
                    s = pygame.mixer.Sound(path)
                    s.set_volume(1.0)
                    self._sounds[key] = s
                    print(f"[Sound] OK: {fname}")
                except Exception as e:
                    print(f"[Sound] Error {fname}: {e}")
            else:
                print(f"[Sound] Missing: {fname} — run: py generate_sounds.py")

    def _play(self, alert_type):
        def _run():
            if PYGAME_OK and alert_type in self._sounds:
                self._sounds[alert_type].stop()
                self._sounds[alert_type].play()
            else:
                print(f"\a[ALERT SOUND] {alert_type}")
        threading.Thread(target=_run, daemon=True).start()

    # ── TTS Voice ────────────────────────────────────────────────────────────
    def _speak(self, text):
        if not TTS_OK or self._tts_busy: return
        def _run():
            self._tts_busy = True
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                engine.setProperty('volume', 1.0)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                print(f"[TTS] {e}")
            finally:
                self._tts_busy = False
        threading.Thread(target=_run, daemon=True).start()

    # ── Database log ──────────────────────────────────────────────────────────
    def _init_log(self):
        database.init_db()

    def _log_csv(self, alert_type, detail, snapshot=""):
    
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        database.log_event(timestamp, alert_type, detail, snapshot)

    # ── Snapshot ──────────────────────────────────────────────────────────────
    def save_snapshot(self, frame, label):
        ts   = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(SNAPSHOTS_DIR, f"{label}_{ts}.jpg")
        cv2.imwrite(path, frame)
        return path

    # ── Email ─────────────────────────────────────────────────────────────────
    def _send_email(self, subject, body, img_path=None):
        if not EMAIL_CONFIG["enabled"]: return
        def _run():
            try:
                msg = MIMEMultipart()
                msg["From"] = EMAIL_CONFIG["sender"]
                msg["To"]   = EMAIL_CONFIG["receiver"]
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain"))
                if img_path and os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        msg.attach(MIMEImage(f.read(), name=os.path.basename(img_path)))
                with smtplib.SMTP(EMAIL_CONFIG["smtp_host"], EMAIL_CONFIG["smtp_port"]) as s:
                    s.starttls()
                    s.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
                    s.send_message(msg)
                print("[Email] Sent!")
            except Exception as e:
                print(f"[Email] Failed: {e}")
        threading.Thread(target=_run, daemon=True).start()

    def _send_discord(self, message):
        if not DISCORD_WEBHOOK_URL:
            print("[Discord] Skipped — DISCORD_WEBHOOK_URL not set in .env")
            return
        def _run():
            try:
                resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=5)
                if resp.status_code != 204:
                    print(f"[Discord] Unexpected response: {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"[Discord] Failed: {e}")
        threading.Thread(target=_run, daemon=True).start()
    # ── PUBLIC ALERTS ─────────────────────────────────────────────────────────

    def weapon_alert(self, label, frame=None):
        now = time.time()
        if now - self._last[ALERT_WEAPON] < self.WEAPON_COOLDOWN: return
        self._last[ALERT_WEAPON] = now
        snap = self.save_snapshot(frame, "weapon") if frame is not None else ""
        msg  = f"WEAPON DETECTED: {label.upper()}"
        self._play(ALERT_WEAPON)
        self._speak(f"Warning! {label} detected! Evacuate the area immediately!")
        self._add_notification(msg, (220,40,40), 7, ALERT_WEAPON)
        self._log_csv(ALERT_WEAPON, label, snap)
        self._send_discord(f"🔪 {msg}")
        self._send_email(f"[ALERT] Weapon: {label}",
            f"Weapon: {label.upper()}\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}", snap)
        print(f"[ALERT] {msg}")

    def suspicious_alert(self, person_id, frame=None):
        now = time.time()
        if now - self._last[ALERT_SUSPICIOUS] < self.SUSPICIOUS_COOLDOWN: return
        self._last[ALERT_SUSPICIOUS] = now
        snap = self.save_snapshot(frame, "suspicious") if frame is not None else ""
        msg  = f"SUSPICIOUS: Person #{person_id} stationary >10s"
        self._play(ALERT_SUSPICIOUS)
        self._speak(f"Suspicious behavior! Person {person_id} has been stationary for over 10 seconds.")
        self._add_notification(msg, (210,110,0), 7, ALERT_SUSPICIOUS)
        self._log_csv(ALERT_SUSPICIOUS, f"Person #{person_id}", snap)
        self._send_discord(f"⚠ {msg}")
        print(f"[ALERT] {msg}")

    def crowd_alert(self, count, frame=None):
        now = time.time()
        if now - self._last[ALERT_CROWD] < self.CROWD_COOLDOWN: return
        self._last[ALERT_CROWD] = now
        snap = self.save_snapshot(frame, "crowd") if frame is not None else ""
        msg  = f"CROWD ALERT: {count} persons!"
        self._play(ALERT_CROWD)
        self._speak(f"Crowd alert! {count} persons detected.")
        self._add_notification(msg, (150,50,200), 6, ALERT_CROWD)
        self._log_csv(ALERT_CROWD, f"{count} persons", snap)
        self._send_discord(f"👥 {msg}")
        print(f"[ALERT] {msg}")

    def zone_breach_update(self, zone_name, person_in_zone, frame=None):
        """
        Har frame pe call karo.
        Entry: foran sound + voice "Restricted area! Leave immediately!"
        10 sec baad bhi andar: escalate — urgent sound + screenshot + email
        """
        now = time.time()
        if person_in_zone:
            if zone_name not in self._zone_first:
                # Fresh entry
                self._zone_first[zone_name]    = now
                self._zone_escalated[zone_name] = False
                if now - self._last[ALERT_ZONE] >= self.ZONE_COOLDOWN:
                    self._last[ALERT_ZONE] = now
                    msg = f"ZONE BREACH: {zone_name} — Leave area immediately!"
                    self._play(ALERT_ZONE)
                    self._speak(f"Warning! Restricted area {zone_name}. Please leave this area immediately!")
                    self._add_notification(msg, (200, 0, 100), 6, ALERT_ZONE)
                    self._log_csv(ALERT_ZONE, f"{zone_name} - entry", "")
                    self._send_discord(f"📐 {msg}")
                    print(f"[ALERT] {msg}")
            else:
                # Check 10 sec escalation
                duration = now - self._zone_first[zone_name]
                if duration >= SETTINGS["zone_warn_time"] and not self._zone_escalated[zone_name]:
                    self._zone_escalated[zone_name] = True
                    snap = self.save_snapshot(frame, f"zone_{zone_name}") if frame is not None else ""
                    msg  = f"ZONE ESCALATION: {zone_name} — {int(duration)}s! Security required!"
                    self._play(ALERT_WEAPON)  # urgent weapon sound
                    self._speak(f"Security alert! Person in restricted area {zone_name} for {int(duration)} seconds. Immediate security response required!")
                    self._add_notification(msg, (255, 0, 0), 9, ALERT_ZONE)
                    self._log_csv(ALERT_ZONE, f"{zone_name} escalated {int(duration)}s", snap)
                    self._send_discord(f"🚨 {msg}")
                    self._send_email(
                        f"[ESCALATION] Zone: {zone_name}",
                        f"Person in restricted zone '{zone_name}' for {int(duration)}s.\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                        snap
                    )
                    print(f"[ALERT] {msg}")
        else:
            # Person left — reset
            self._zone_first.pop(zone_name, None)
            self._zone_escalated.pop(zone_name, None)

    def get_zone_duration(self, zone_name):
        if zone_name in self._zone_first:
            return time.time() - self._zone_first[zone_name]
        return 0

    def _add_notification(self, msg, color, duration, kind):
        self.notifications = [n for n in self.notifications if n["expires_at"] > time.time()]
        self.notifications.append({
            "msg": msg, "color": color, "kind": kind,
            "expires_at": time.time() + duration,
            "time": time.strftime("%H:%M:%S"),
        })

    def get_active_notifications(self):
        now = time.time()
        self.notifications = [n for n in self.notifications if n["expires_at"] > now]
        return self.notifications