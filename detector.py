import cv2
import numpy as np
from ultralytics import YOLO

DANGEROUS_CLASSES = {
    "knife","gun","pistol","rifle","sword","weapon","handgun","blade","scissors"
}
NEVER_DANGEROUS = {
    "bird","cat","dog","horse","cow","elephant","bear","zebra","giraffe","sheep",
    "airplane","bus","train","truck","car","bicycle","motorcycle","boat",
    "traffic light","fire hydrant","stop sign","bench","toilet","tv","microwave",
    "oven","toaster","sink","refrigerator","clock","vase","bowl","banana","apple",
    "orange","sandwich","broccoli","carrot","pizza","cake","donut","hot dog",
    "dining table","potted plant","sports ball","kite","baseball glove","skateboard",
    "surfboard","tennis racket","frisbee","skis","snowboard","wine glass","spoon","keyboard",
}
DISPLAY_NAMES = {
    "scissors":"KNIFE","knife":"KNIFE","gun":"GUN",
    "pistol":"GUN","rifle":"RIFLE","sword":"SWORD","blade":"BLADE"
}

COLOR_PERSON    = (0, 220, 80)
COLOR_DANGEROUS = (0, 0, 255)
COLOR_SAFE      = (30, 160, 255)
COLOR_ZONE_WARN = (0, 80, 255)
COLOR_ZONE_OBJ  = (0, 200, 255)   # non-person in zone


class Detector:
    def __init__(self, confidence=0.35):
        print("[Detector] Loading YOLOv8s...")
        self.model       = YOLO("yolov8s.pt")
        self.confidence  = confidence
        self.weapon_conf = 0.22   # knife ke liye extra sensitive
        self.night_mode  = False
        self.zones       = []
        self._heatmap    = None
        print("[Detector] Ready!")

    def enhance_night(self, frame):
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8,8))
        return cv2.cvtColor(cv2.merge((clahe.apply(l), a, b)), cv2.COLOR_LAB2BGR)

    # ── Zone management ───────────────────────────────────────────────────────
    def add_zone(self, name, rect):
        self.zones.append({"name": name, "rect": rect, "active": True})

    def clear_zones(self):
        self.zones = []

    def point_in_zone(self, cx, cy):
        """Check if point is inside any zone"""
        breached = []
        for z in self.zones:
            if not z["active"]: continue
            x1,y1,x2,y2 = z["rect"]
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                breached.append(z["name"])
        return breached

    def bbox_in_zone(self, bbox):
        """Check if bounding box OVERLAPS with any zone"""
        bx1,by1,bx2,by2 = bbox
        breached = []
        for z in self.zones:
            if not z["active"]: continue
            zx1,zy1,zx2,zy2 = z["rect"]
            # Overlap check
            if not (bx2 < zx1 or bx1 > zx2 or by2 < zy1 or by1 > zy2):
                breached.append(z["name"])
        return breached

    # ── Heatmap ───────────────────────────────────────────────────────────────
    def update_heatmap(self, frame, persons):
        h, w = frame.shape[:2]
        if self._heatmap is None or self._heatmap.shape[:2] != (h,w):
            self._heatmap = np.zeros((h,w), dtype=np.float32)
        for p in persons:
            x1,y1,x2,y2 = p["bbox"]
            cx,cy = (x1+x2)//2, (y1+y2)//2
            r = max(30, (x2-x1)//3)
            cv2.circle(self._heatmap, (cx,cy), r, 8.0, -1)
        self._heatmap *= 0.97

    def get_heatmap_overlay(self, frame):
        if self._heatmap is None: return frame
        norm = cv2.normalize(self._heatmap, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        heat = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
        mask = norm > 10
        out  = frame.copy()
        out[mask] = cv2.addWeighted(frame, 0.45, heat, 0.55, 0)[mask]
        return out

    # ── Detection ────────────────────────────────────────────────────────────
    def detect(self, frame):
        src     = self.enhance_night(frame) if self.night_mode else frame
        results = self.model(src, verbose=False, conf=self.weapon_conf)[0]
        detections = []

        for box in results.boxes:
            cls_id = int(box.cls[0])
            label  = self.model.names[cls_id].lower()
            conf   = float(box.conf[0])

            if label in NEVER_DANGEROUS: continue
            if label == "person" and conf < self.confidence: continue
            if label not in DANGEROUS_CLASSES and label != "person" and conf < self.confidence: continue

            x1,y1,x2,y2 = map(int, box.xyxy[0])
            is_dangerous = label in DANGEROUS_CLASSES
            is_person    = (label == "person")
            cx,cy        = (x1+x2)//2, (y1+y2)//2

            # Zone check for ALL objects using bbox overlap
            zone_breached = self.bbox_in_zone((x1,y1,x2,y2))

            detections.append({
                "label":         label,
                "display_label": DISPLAY_NAMES.get(label, label.upper()),
                "confidence":    conf,
                "bbox":          (x1,y1,x2,y2),
                "is_dangerous":  is_dangerous,
                "is_person":     is_person,
                "zone_breached": zone_breached,
                "center":        (cx,cy),
            })

        return detections

    # ── Draw ─────────────────────────────────────────────────────────────────
    def draw(self, frame, detections):
        h, w = frame.shape[:2]

        # Draw zones first
        for z in self.zones:
            if not z["active"]: continue
            x1,y1,x2,y2 = z["rect"]
            overlay = frame.copy()
            cv2.rectangle(overlay, (x1,y1), (x2,y2), (0,0,180), -1)
            cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)
            cv2.rectangle(frame, (x1,y1), (x2,y2), (60,0,220), 2)
            cv2.putText(frame, f"RESTRICTED: {z['name']}", (x1+6, y1+22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (120,80,255), 2)

        # Draw detections
        for d in detections:
            x1,y1,x2,y2 = d["bbox"]
            conf   = d["confidence"]
            dlabel = d["display_label"]
            in_zone = bool(d["zone_breached"])

            if d["is_dangerous"]:
                color = COLOR_DANGEROUS
                tag   = f"!! {dlabel}  {conf:.0%}"
                thick = 3
                # Yellow outer glow
                cv2.rectangle(frame, (x1-4,y1-4), (x2+4,y2+4), (0,200,255), 2)
            elif d["is_person"]:
                color = COLOR_ZONE_WARN if in_zone else COLOR_PERSON
                tag   = f"Person  {conf:.0%}" + (" [ZONE!]" if in_zone else "")
                thick = 3 if in_zone else 2
            else:
                # Non-person object
                color = COLOR_ZONE_OBJ if in_zone else COLOR_SAFE
                tag   = f"{dlabel}  {conf:.0%}" + (" [ZONE!]" if in_zone else "")
                thick = 2 if in_zone else 1

            cv2.rectangle(frame, (x1,y1), (x2,y2), color, thick)
            (tw,th),_ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)
            cv2.rectangle(frame, (x1, max(0,y1-th-12)), (x1+tw+10,y1), color, -1)
            cv2.putText(frame, tag, (x1+5, max(12,y1-4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255,255,255), 2)

        if self.night_mode:
            cv2.rectangle(frame, (0,h-28), (160,h), (0,50,80), -1)
            cv2.putText(frame, "NIGHT MODE", (8,h-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0,220,255), 2)
        return frame
