"""Build the prebuilt prologue once: Steve Jobs, 1985, on asking Aristotle a question."""
import json, server

LINES = [
    ("Steve Jobs. Nineteen eighty-five.", '<p class="q">Steve Jobs, 1985</p>', None),
    ("[thoughtful] I was reading Aristotle... and I wanted to ask him a question.", '<p class="s">I wanted to ask him a question.</p>', None),
    ("The problem was... you can't ask Aristotle a question.", '<p class="w">You can\'t.</p>', "bust"),
    ("But someday... we will capture the underlying worldview of a mind like his... inside a machine.", '<p class="w">Someday.</p>', None),
    ("And a student will not only read what Aristotle wrote.", '<p class="s dim">Not only read.</p>', None),
    ("They will ask him a question. [pause] And get an answer.", '<p class="w">Ask him.</p>', None),
    ("Forty years later.", '', "horizon"),
]
pass  # same designed keynote voice as Aristotle
script = " ".join(l for l, _, _ in LINES)
audio = server.tts(script)
al = audio["alignment"]; chars = "".join(al["characters"]); starts = al["character_start_times_seconds"]
scenes, pos = [], 0
for line, html, img in LINES:
    i = max(chars.find(line[:12], pos), pos)
    scenes.append({"line": line, "html": html, "image": img, "start": starts[min(i, len(starts) - 1)]}); pos = i + len(line)
film = {"belief": "prologue", "script": script, "duration": al["character_end_times_seconds"][-1], "scenes": scenes, "audio": audio["audio_base64"]}
json.dump(film, open("static/prologue.json", "w"))
print("prologue", round(film["duration"], 1), "s", [round(s["start"], 1) for s in scenes])
