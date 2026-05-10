# AegisHarness Backend

This backend is the Person C integration harness. It intentionally uses only the Python standard library so it can run immediately in a conda environment. Live mode uses Gemini first when `GEMINI_API_KEY` is present, then Clod fallback.

It models the revised five-phase architecture:

1. Intent parsing and Gemini-first context retrieval
2. Gemini-first preflight bug list generation
3. HITL `PENDING_APPROVAL`
4. Gemini-first, Clod-fallback difficulty scoring and model routing
5. AI review and repair with `max_iterations = 3`

Run tests:

```bash
conda run -n aegis-harness python -m unittest discover -s backend/tests
```

The same state and event names should be used by a future FastAPI implementation.
