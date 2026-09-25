# Aristotle

Type what you believe. Aristotle dismantles it, on a black stage, in his own voice.
Every film is generated live: Claude writes the Socratic script and the keynote slides as HTML,
ElevenLabs speaks it with per-word timestamps, and the page plays it as a film.
While it cooks, Steve Jobs (1985) explains why he wanted to ask Aristotle a question.

## Run

    uv sync
    uv run uvicorn server:app --port 8000
    open http://localhost:8000

Needs `ELEVENLABS_API_KEY` in `.env` and a logged-in `claude` CLI (Claude is called through `claude -p`).

## Stage keys

- `1` to `7` fills an example belief. `return` submits.
- After a film: `return` asks again, `r` replays, `esc` resets.
- Every belief is cached in `cache/`, so rehearsed beliefs play instantly. If the network dies, the last good film plays.

## Example beliefs (pre-generated)

1. We must pace the frontier or everybody dies as we race to the bottom
2. Money is the only honest measure of value.
3. AI will make humans obsolete.
4. Move fast and break things.
5. Everyone is entitled to their opinion.
6. I will be happy once I am successful.
7. Love is just chemistry.
