import wave, struct, math, os
SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "sounds")
os.makedirs(SOUNDS_DIR, exist_ok=True)

def write_wav(filename, pattern, sample_rate=44100, volume=0.95):
    path = os.path.join(SOUNDS_DIR, filename)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
        frames = []
        for (freq, dur, gap) in pattern:
            bn = int(sample_rate*dur); gn = int(sample_rate*gap); fade = int(bn*0.05)
            for i in range(bn):
                env = 1.0
                if i < fade: env = i/fade
                elif i > bn-fade: env = (bn-i)/fade
                val = int(32767*volume*env*math.sin(2*math.pi*freq*i/sample_rate))
                frames.append(struct.pack("<h", val))
            frames.extend([struct.pack("<h",0)]*gn)
        wf.writeframes(b"".join(frames))
    print(f"  Created: {filename}")

print("Generating sounds...")
write_wav("weapon_alert.wav",     [(1400,.18,.07)]*3+[(0,.3,0)]+[(1400,.18,.07)]*3+[(0,.3,0)]+[(1400,.18,.07)]*3)
write_wav("suspicious_alert.wav", [(900,.4,.25)]*7)
write_wav("crowd_alert.wav",      [(700,.3,.2)]*6)
write_wav("zone_alert.wav",       [(1600,.12,.08)]*10)
print("All sounds ready! Now run: py main.py")
