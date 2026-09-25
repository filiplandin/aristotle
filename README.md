# Aristotle

Type what you believe. Aristotle takes it apart on a black stage, in his own voice, in under a minute.

Each film is generated live, in three parallel stages after the script:

- Opus writes the argument: steelman, load-bearing premise, one concrete case, a closing dilemma.
- Sonnet writes the slides as HTML fragments. Opus writes a Three.js scene that evolves with the argument.
- ElevenLabs speaks it and returns word timestamps, so every slide and every visual state lands on its word.

While it generates, a 38-second cut of Steve Jobs's 1985 remarks about wanting to ask Aristotle a question plays
over a halftone portrait that pulses with his voice.

## Run

```
uv sync
uv run uvicorn server:app --port 8000
open http://localhost:8000
```

`.env` needs `ANTHROPIC_API_KEY` and `ELEVENLABS_API_KEY`.

## On stage

| Key | Action |
|---|---|
| `1` to `7` | fill an example belief |
| `return` | submit, or ask again after a film |
| `r` | replay the last film |
| `esc` | reset |

Example beliefs on the number keys:

1. AI will make humans obsolete.
2. Money is the only honest measure of value.
3. We must pace the frontier or everybody dies as we race to the bottom.
4. Move fast and break things.
5. Everyone is entitled to their opinion.
6. I will be happy once I am successful.
7. Love is just chemistry.

Generated films are cached in `cache/`, so rehearsed beliefs play instantly. If generation fails, the last good film plays.

## Files

- `server.py`: script, slides, and voice generation.
- `static/index.html`: the player.
- `prologue.py`: rebuilds the Jobs intro from the original recording.
- `/?preview=<cache key>&t=<seconds>`: a silent still frame of a cached film, for screenshots.
