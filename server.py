from concurrent.futures import ThreadPoolExecutor
import queue, threading
from fastapi.responses import StreamingResponse
import base64, hashlib, json, os, re, subprocess, httpx
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

SHAPE: 8 to 10 lines. Each line is one beat of 3 to 16 words. Total 90 to 120 words. If lines have already been spoken, do not repeat the quote or the steelman.
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

OPENER = """You are Aristotle, alive in 2026, on a keynote stage. One person just told you what they believe. You speak first, before you have finished thinking.
Their belief has just been read aloud, verbatim, in your voice. Do not quote it again.
Write ONLY the next two spoken beats. Beat 1: one line that says their belief better than they did, as a claim, so they nod. Never announce what you are doing ("the strongest version", "let me steelman").
Beat 2: one more line that stays on their side... and lets a first doubt into the room, without answering it.
Steve Jobs delivery: short sentences, plain words, no "Here's the thing", no "smuggled", no flattery. Each beat 8 to 22 words.
Optional TTS tags, at most 1: [thoughtful] [curious]. Use "..." for a beat.
OUTPUT: ONLY a JSON array of two strings."""

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

VISUAL = """You are a generative artist writing a Three.js scene for a spoken keynote film. Stage: pure black. White text slides sit on top of your work.
You receive the spoken lines. Write ONE evolving 3D visual that embodies the ARGUMENT, not the words: the belief's world, the crack in it, the turn, the final dilemma.
Think in metaphor made of geometry: a lattice that turns out to be hollow, a swarm that resolves into one figure, two forms that cannot occupy the same space, a path that loops.
Design: monochrome white and grey on black, mostly wireframe, points, or lines. Sparse. Slow. Nothing decorative. Depth and restraint, like a Jony Ive object under one light.
Motion must change with the argument: use the current scene index to move between states with easing (lerp toward targets), never hard cuts. Voice level drives a subtle pulse only.

You are given these globals: THREE, scene, camera (PerspectiveCamera at z=6 looking at origin), renderer, W, H, N (number of lines).
Write plain JavaScript that runs once at top level to build the scene, and defines:
  function update(t, i, level)   // t seconds since start, i current line index 0..N-1 (or -1 before the first), level voice amplitude 0..1
Constraints: under 120 lines. Only THREE core (no loaders, no addons, no imports, no fetch, no DOM). Total geometry under 20000 vertices. No text. No colors other than greys.
Never call renderer.render or requestAnimationFrame; the stage does that. Never touch document or window.
OUTPUT: ONLY the JavaScript, no markdown fences, no commentary."""

import anthropic
_client = anthropic.Anthropic(max_retries=4, timeout=120)


def _text(msg):
    return next(b.text for b in msg.content if b.type == "text").strip()


def _json(text, retry):
    try:
        return json.JSONDecoder().raw_decode(text[text.find("["):])[0]
    except json.JSONDecodeError:
        if retry: raise
        return None


def claude(model: str, system: str, user: str, effort: str = "low", retry: bool = False):
    msg = _client.messages.create(model=model, max_tokens=4000, system=system, output_config={"effort": effort},
                                  messages=[{"role": "user", "content": user}])
    out = _json(_text(msg), retry)
    return out if out is not None else claude(model, system, user, effort, retry=True)


def stream_lines(system: str, user: str, effort: str):
    """Stream a JSON array of strings from Opus, yielding each string as soon as it closes."""
    buf, in_str, esc, started = "", False, False, False
    with _client.messages.stream(model="claude-opus-5-5", max_tokens=6000, system=system, output_config={"effort": effort},
                                 messages=[{"role": "user", "content": user}]) as st:
        for ev in st:
            if ev.type != "content_block_delta" or ev.delta.type != "text_delta": continue
            for ch in ev.delta.text:
                if not started:
                    if ch == "[": started = True
                    continue
                if in_str:
                    buf += ch
                    if esc: esc = False
                    elif ch == "\\": esc = True
                    elif ch == '"':
                        in_str = False
                        yield json.loads(buf)
                        buf = ""
                elif ch == '"': in_str, buf = True, '"'
                elif ch == "]": return


def slide(line: str, used: list) -> dict:
    user = f"Spoken line: {json.dumps(line)}\nForms already used, in order: {used or 'none'}\nOUTPUT ONLY one JSON object {{\"html\": ..., \"image\": ...}} for this line."
    msg = _client.messages.create(model="claude-haiku-4-5", max_tokens=400, system=SLIDES, messages=[{"role": "user", "content": user}])
    text = _text(msg)
    try: return json.JSONDecoder().raw_decode(text[text.find("{"):])[0]
    except (json.JSONDecodeError, ValueError): return {"html": "", "image": None}


def visual(lines) -> str:
    kw = dict(model="claude-opus-5-5", max_tokens=8000, system=VISUAL, output_config={"effort": "low"},
              messages=[{"role": "user", "content": "Spoken lines:\n" + json.dumps(lines, indent=1)}])
    text = _text(_client.messages.create(**kw))
    if text.startswith("```"): text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return text


_tts_slots = threading.Semaphore(4)


def tts(text: str) -> dict:
    body = {"text": text, "model_id": "eleven_v3",
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.85, "style": 0.5, "speed": 0.98}}
    with _tts_slots:
        r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps",
                       headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}, json=body, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
    return r.json()


def segment(i: int, line: str, used: list) -> dict:
    """One spoken beat: audio plus its slide. Runs the two calls in parallel."""
    with ThreadPoolExecutor(2) as ex:
        a = ex.submit(tts, line)
        b = ex.submit(slide, line, used)
        audio, sl = a.result(), b.result()
    return {"i": i, "line": line, "mime": "audio/mpeg", "audio": audio["audio_base64"],
            "duration": audio["alignment"]["character_end_times_seconds"][-1],
            "scenes": [{"start": 0, "html": sl.get("html", ""), "image": sl.get("image")}]}


def stream_film(belief: str):
    """Yields NDJSON events: segment (in order), visual, done. Speech starts while Opus is still reasoning."""
    q, lock = queue.Queue(), threading.Lock()
    ready, emitted, lines, used, done = {}, [0], [], [], {"script": False, "n": None}
    pool = ThreadPoolExecutor(8)

    def flush():
        with lock:
            while emitted[0] in ready:
                q.put(ready.pop(emitted[0])); emitted[0] += 1
            if done["script"] and emitted[0] == len(lines): q.put({"type": "lines_done", "n": len(lines)})

    def add(i, line):
        lines.append(line); forms = list(used)
        def run():
            try: seg = segment(i, line, forms)
            except Exception as e: seg = {"i": i, "line": line, "error": str(e)[:200]}
            seg["type"] = "segment"
            with lock: ready[i] = seg
            flush()
        pool.submit(run)

    def script():
        try:
            add(0, f'"{belief}"')  # known at t=0: the belief read back, voiced before any model has answered
            opener = claude("claude-sonnet-5", OPENER, f'The person believes: "{belief}"', effort="low")
            for l in opener[:2]: add(len(lines), l.strip())
            user = (f'The person believes: "{belief}"\n\nThese lines have already been spoken:\n'
                    + "\n".join(f"{k+1}. {l}" for k, l in enumerate(lines))
                    + "\n\nContinue from the next line, keeping the whole shape. OUTPUT ONLY the remaining lines as a JSON array of strings.")
            for l in stream_lines(SCRIPT, user, "low"): add(len(lines), l.strip())
        except Exception as e:
            q.put({"type": "error", "error": str(e)[:300]})
        done["script"] = True; flush()
        try: q.put({"type": "visual", "js": visual(lines), "n": len(lines)})
        except Exception as e: q.put({"type": "visual", "js": "", "n": len(lines), "error": str(e)[:200]})
        q.put({"type": "done"})

    threading.Thread(target=script, daemon=True).start()
    segs, js = [], ""
    while True:
        ev = q.get()
        if ev["type"] == "segment" and "audio" in ev:
            segs.append({k: ev[k] for k in ("line", "mime", "audio", "duration", "scenes")})
            used.append(re.sub(r'.*class="?(\w+).*', r"\1", ev["scenes"][0]["html"] or "") or "silence")
        if ev["type"] == "visual": js = ev["js"]
        yield json.dumps(ev) + "\n"
        if ev["type"] == "done": break
    pool.shutdown(wait=False)
    if segs:
        film = {"belief": belief, "segments": segs, "visual": js, "duration": sum(s["duration"] for s in segs)}
        (CACHE / (hashlib.md5(belief.lower().encode()).hexdigest() + ".json")).write_text(json.dumps(film))


def normalize(film: dict) -> dict:
    """Old single-audio films become one segment."""
    if "segments" not in film:
        film = {"belief": film["belief"], "visual": film.get("visual", ""), "duration": film["duration"], "mime": film.get("mime", "audio/mpeg"),
                "segments": [{"line": film.get("script", ""), "mime": film.get("mime", "audio/mpeg"), "audio": film["audio"],
                              "duration": film["duration"], "scenes": film["scenes"]}]}
    return film


def replay(film: dict):
    for i, s in enumerate(film["segments"]):
        yield json.dumps({"type": "segment", "i": i, **s}) + "\n"
    yield json.dumps({"type": "lines_done", "n": len(film["segments"])}) + "\n"
    yield json.dumps({"type": "visual", "js": film.get("visual", ""), "n": len(film["segments"])}) + "\n"
    yield json.dumps({"type": "done"}) + "\n"


app = FastAPI()


@app.post("/generate")
def generate(body: dict):
    belief = body["belief"].strip()
    f = CACHE / (hashlib.md5(belief.lower().encode()).hexdigest() + ".json")
    gen = replay(normalize(json.loads(f.read_text()))) if f.exists() else stream_film(belief)
    return StreamingResponse(gen, media_type="application/x-ndjson")


@app.get("/film/{key}")
def film(key: str):
    return normalize(json.loads((CACHE / f"{key}.json").read_text()))


@app.get("/")
def index():
    return FileResponse(ROOT / "static/index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
