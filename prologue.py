"""Build the intro from the original Steve Jobs recording: three passages spliced, slides timed to his words."""
import wave, io, json, base64, struct

SRC = "steve-jobs-aristotle-clean.wav"
CUTS = [(0.0, 9.8), (37.0, 42.0), (105.2, 128.6)]  # tutor/jealous · can't ask him · hope: ask him, get an answer
FADE = 0.04

w = wave.open(SRC); fr = w.getframerate(); raw = w.readframes(w.getnframes()); params = w.getparams()
samples = list(struct.unpack(f"<{len(raw)//2}h", raw))
out = []
for a, b in CUTS:
    seg = samples[int(a * fr):int(b * fr)]; n = int(FADE * fr)
    for i in range(n): seg[i] = int(seg[i] * i / n); seg[-1 - i] = int(seg[-1 - i] * i / n)
    out += seg
buf = io.BytesIO(); o = wave.open(buf, "wb"); o.setparams(params); o.writeframes(struct.pack(f"<{len(out)}h", *out)); o.close()
dur = len(out) / fr

def T(src_t):  # source time -> spliced time
    acc = 0
    for a, b in CUTS:
        if a <= src_t <= b: return acc + src_t - a
        acc += b - a
    raise ValueError(src_t)

SCENES = [
    (0.0,      '<p class="q">Steve Jobs, 1985</p>', None),
    (T(5.3),   '<p class="w">Aristotle.</p>', None),
    (T(7.5),   '<p class="s dim">I became immensely jealous.</p>', None),
    (T(37.4),  '<p class="w">You can\'t ask him.</p>', None),
    (T(40.7),  '<p class="s dim">I won\'t get an answer.</p>', None),
    (T(106.3), '<p class="w">Someday.</p>', None),
    (T(111.0), '<p class="s">Capture a worldview.</p>', None),
    (T(117.4), '<p class="w">In a computer.</p>', None),
    (T(124.3), '<p class="w">Ask him.</p>', None),
    (T(127.4), '<p class="w">Get an answer.</p>', None),
    (dur - 0.3, '', 'horizon'),
]
film = {"belief": "prologue", "mime": "audio/wav", "duration": dur,
        "scenes": [{"line": "", "html": h, "image": i, "start": round(s, 2)} for s, h, i in SCENES],
        "audio": base64.b64encode(buf.getvalue()).decode()}
json.dump(film, open("static/prologue.json", "w"))
print("prologue", round(dur, 1), "s", [s["start"] for s in film["scenes"]])
