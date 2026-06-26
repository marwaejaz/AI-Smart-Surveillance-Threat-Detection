import time

class SuspiciousTracker:
    SUSPICIOUS_TIME    = 10
    MOVEMENT_THRESHOLD = 40
    FORGET_TIME        = 5

    def __init__(self):
        self._tracks  = {}
        self._next_id = 0

    def _center(self, bbox):
        x1,y1,x2,y2 = bbox
        return ((x1+x2)//2, (y1+y2)//2)

    def _distance(self, p1, p2):
        return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5

    def _match(self, center):
        best_id, best_dist = None, float("inf")
        for tid, t in self._tracks.items():
            d = self._distance(center, t["last_center"])
            if d < best_dist:
                best_id, best_dist = tid, d
        return best_id if best_dist < 120 else None

    def update(self, person_detections):
        now = time.time()
        matched = set()
        results = []
        for det in person_detections:
            center = self._center(det["bbox"])
            tid    = self._match(center)
            if tid is None:
                tid = self._next_id; self._next_id += 1
                self._tracks[tid] = {
                    "first_seen": now, "last_seen": now,
                    "last_center": center, "stationary_since": now,
                    "suspicious": False, "alerted": False,
                }
            else:
                t    = self._tracks[tid]
                moved = self._distance(center, t["last_center"])
                if moved > self.MOVEMENT_THRESHOLD:
                    t["stationary_since"] = now
                    t["suspicious"] = False
                    t["alerted"]    = False
                t["last_center"] = center
                t["last_seen"]   = now
                if now - t["stationary_since"] >= self.SUSPICIOUS_TIME:
                    t["suspicious"] = True
            matched.add(tid)
            results.append((det, self._tracks[tid], tid))
        stale = [tid for tid, t in self._tracks.items()
                 if tid not in matched and now - t["last_seen"] > self.FORGET_TIME]
        for tid in stale:
            del self._tracks[tid]
        return results

    def mark_alerted(self, tid):
        if tid in self._tracks:
            self._tracks[tid]["alerted"] = True
