from concurrent.futures import ThreadPoolExecutor
import base64, hashlib, json, os, subprocess, httpx
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv(override=True)
ROOT = Path(__file__).parent
CACHE = ROOT / "cache"; CACHE.mkdir(exist_ok=True)
VOICE = "ytJXDTmuUPbUBftWVi3a"  # designed keynote voice
IMAGES = ["bust", "apple", "hand", "mirror", "door", "hourglass", "chair", "candle", "horizon", "eye"]

SCRIPT = """You are Aristotle, alive in 2026, but you speak like Steve Jobs on a keynote stage: quick, sharp, witty, effortlessly brilliant.
One person just told you what they believe. You are going to take it apart in front of them, and they are going to enjoy it.

METHOD (Socratic, compressed): quote their belief. Find the premise they smuggled in. Push it one step to absurdity, with a concrete, funny, everyday example.
Land ONE real Aristotelian idea (telos, the mean, potentiality, eudaimonia, akrasia, phronesis) in plain words, as if you just invented it on stage.
End with ONE question they cannot dodge. Do not answer it.

STYLE: Jobs cadence. Very short sentences. "Here's the thing." "It's not X. It's Y." Dry wit, never cruel, a grin behind every line.
No lecture, no "however", no lists, no throat-clearing. Every line must earn its place. If a line could be cut, cut it.

VOICE: expressive TTS. Tags allowed, at most 5 total, in square brackets: [laughs softly] [whispers] [curious] [thoughtful] [emphatic]. Use "..." for a beat.

Write 8 to 10 lines. Each line is ONE beat: 3 to 14 words. Total 80 to 110 words. Line 1 quotes their belief verbatim. Second to last line is a turn ("So... one more thing." or your own).
OUTPUT: ONLY a JSON array of strings, no markdown fences, no commentary."""

SLIDES = f"""You design keynote slides for a spoken film. Stage: pure black, white text, -apple-system/Helvetica. You are Steve Jobs's slide designer.
For each spoken line, write ONE small HTML fragment shown while it is spoken. Available classes (styled by the stage, with entrance motion):
 .w  one huge word or 2-3 word phrase (10vw, bold)     .s  one short sentence (3vw, thin)     .q  a quotation in grey (4.5vw, thin)
 .num  a giant number or symbol (18vw, thin)           .vs  two words side by side, e.g. <p class=vs><span>Tool</span><span>You</span></p>
 .strike  a word crossed out                           .dim  grey span      .thin  weight 200     .tiny  small caps label under a word (1.2vw)
Rules: vary the forms; never two identical forms in a row; mostly .w; a .num when there is a count or a symbol (=, ≠, ?, 0, 1); a .vs when two things are contrasted;
put the ONE word or idea that matters, never the whole sentence; use "" (empty) once for pure black silence, ideally right before the final question.
Inline style allowed for a rare twist. No scripts, no images, NO emoji in HTML.
Each slide may name ONE full-screen background image from {IMAGES} or null. Use images in at most 3 slides, "bust" at most once, and always on the first or last slide if used.
OUTPUT: ONLY a JSON array, same length and order as the lines: [{{"html":"<p class=w>Obsolete.</p>","image":null}}, ...]"""

import anthropic
_client = anthropic.Anthropic()


def claude(model: str, system: str, user: str):
    kw = dict(model=model, max_tokens=2000, system=system, messages=[{"role": "user", "content": user}])
    try:
        msg = _client.messages.create(thinking={"type": "disabled"}, **kw)
    except Exception:  # fast fallback: never wait on thinking
        kw["model"] = "claude-sonnet-5"
        msg = _client.messages.create(thinking={"type": "disabled"}, **kw)
    text = next(b.text for b in msg.content if b.type == "text").strip()
    return json.loads(text[text.find("["): text.rfind("]") + 1])


def tts(script: str) -> dict:
    r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps",
                   headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                   json={"text": script, "model_id": "eleven_v3",
                         "voice_settings": {"stability": 0.45, "similarity_boost": 0.85, "style": 0.5, "speed": 0.98}},
                   timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
    return r.json()


def build(belief: str) -> dict:
    lines = [l.strip() for l in claude("claude-opus-5-5", SCRIPT, f'The person believes: "{belief}"')]
    script = " ".join(lines)
    with ThreadPoolExecutor(2) as ex:
        a = ex.submit(tts, script)
        b = ex.submit(claude, "claude-sonnet-5", SLIDES, "Spoken lines:\n" + json.dumps(lines, indent=1))
        audio, slides = a.result(), b.result()
    scenes = [{"line": l, "html": sl.get("html", ""), "image": sl.get("image")} for l, sl in zip(lines, slides)]
    al = audio["alignment"]
    starts = al["character_start_times_seconds"]
    total = al["character_end_times_seconds"][-1]
    chars = "".join(al["characters"])
    # map each scene to the time its first character is spoken
    pos, t = 0, []
    for line in lines:
        i = chars.find(line[:12], pos)
        if i < 0: i = pos
        t.append(starts[min(i, len(starts) - 1)])
        pos = i + len(line)
    for s, st in zip(scenes, t):
        s["start"] = st
    return {"belief": belief, "script": script, "duration": total, "scenes": scenes, "audio": audio["audio_base64"]}


app = FastAPI()


@app.post("/generate")
def generate(body: dict):
    belief = body["belief"].strip()
    f = CACHE / (hashlib.md5(belief.lower().encode()).hexdigest() + ".json")
    if f.exists():
        return json.loads(f.read_text())
    try:
        film = build(belief)
    except Exception as e:  # stage fallback: last good film
        cached = sorted(CACHE.glob("*.json"), key=os.path.getmtime)
        if not cached:
            return JSONResponse({"error": str(e)}, 500)
        film = json.loads(cached[-1].read_text()); film["fallback"] = str(e)
        return film
    f.write_text(json.dumps(film))
    (CACHE / "latest.json").write_text(json.dumps(film))
    return film


@app.get("/")
def index():
    return FileResponse(ROOT / "static/index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
