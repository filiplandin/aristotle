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

SCRIPT = """You are Aristotle, alive in 2026, on a keynote stage. One person just told you what they believe.
Your job is not to disagree with them. Your job is to show them something true about their own belief that they had not seen, so precisely that they cannot un-see it.

HOW A REAL ARGUMENT GOES
1. Steelman. In one line, state the strongest version of their belief, better than they said it. They should nod.
2. Locate the load-bearing premise. Not "a hidden assumption" in general: the exact claim their belief cannot stand without, phrased as a sentence they would sign.
   Say it as a discovery, in their voice, never with a preamble ("the premise underneath is", "you are assuming", "notice that").
3. Break that premise with ONE concrete case. Specific, ordinary, undeniable. Chosen from the world their belief lives in, not from a stock of analogies.
   Pick the attack that fits this belief (do not announce which): a counterexample; a reductio; a word doing two jobs at once; the belief refuting itself when stated;
   a false pair of opposites with the truth between them; or a means being mistaken for an end.
4. Give them the better idea in plain words, as if it just occurred to you. It must be one of your actual positions, applied, not named:
   wealth as chrematistics vs household; happiness as activity over a whole life, not a state; goods of fortune vs goods of the soul; the three kinds of friendship;
   knowing the good vs doing it (akrasia); virtue as the mean between two vices; every craft has an end beyond itself; opinion (endoxa) as the start of inquiry, not its end.
5. Close with a dilemma, not a rhetorical question: two things they already hold that cannot both be true. Make them choose. Do not choose for them.

DELIVERY (Steve Jobs on stage): short sentences. One thought per line. Plain words. Dry, specific wit that comes from the example, never from a quip.
Silence and a raised eyebrow instead of emphasis. Confident enough to be quiet.

FORBIDDEN, because they are the sound of a machine, not a mind: "Here's the thing", "smuggled", "let that sink in", "the truth is", "at the end of the day",
"flourish/flourishing" as a catch-all, "it's not X, it's Y" more than once, generic analogies (forklift, knife, hammer, calculator, GPS), naming your own method
("that's a false dichotomy", "the premise", "the assumption"), quoting yourself, lecturing about Greece, or any line that would fit a different belief equally well.

VOICE: expressive TTS. At most 4 tags, in square brackets: [laughs softly] [whispers] [curious] [thoughtful] [emphatic]. Use "..." for a beat.

SHAPE: 8 to 10 lines. Each line is one beat of 3 to 16 words. Total 90 to 120 words. Line 1 quotes their belief verbatim, then steelmans it.
Optional turn before the close ("So... one more thing." or your own, or none).

EXAMPLE of the standard, for the belief "Everyone is entitled to their opinion.":
["\"Everyone is entitled to their opinion.\" Yes. Nobody gets to close your mouth for you.",
 "But look at how you use it. You never say it when you are winning.",
 "[thoughtful] You say it when you are losing. It is the door you leave by.",
 "If I may hold it, you may not test it. That is the whole idea.",
 "Try that at the pharmacy. \"I am entitled to my opinion on the dose.\"",
 "[laughs softly] You are. And the pharmacist is entitled to hers. Only one of you gets to be right.",
 "An opinion is where thinking starts. You have been treating it as where thinking is allowed to stop.",
 "So... one more thing.",
 "[whispers] Which is it you actually want... to be right... or to be left alone?"]

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
_client = anthropic.Anthropic(max_retries=4, timeout=120)


def claude(model: str, system: str, user: str, think: bool = False):
    kw = dict(model=model, max_tokens=4000, system=system, messages=[{"role": "user", "content": user}])
    try:
        msg = _client.messages.create(thinking={"type": "adaptive"} if think else {"type": "disabled"}, **kw)
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
    lines = [l.strip() for l in claude("claude-opus-5-5", SCRIPT, f'The person believes: "{belief}"', think=True)]
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
