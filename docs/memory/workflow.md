# Workflow

## Normal development cycle

1. Read `INDEX.md` and relevant memory files.
2. Make changes to backend or frontend.
3. Test: `uvicorn main:app --reload` + `npm run dev`.
4. Verify on device: watch the lightbar respond.
5. Update `records/decision-log.md` for any non-obvious choices.

## Adding a new inspiration source

1. Add an async `_get_<source>()` method to `engine.py`.
2. Call it in `_build_context()` alongside existing sources.
3. Keep the context snippet short — one line max.
4. Log the data point to `console_log` so the UI shows it.
5. Note the source in `decision-log.md`.

## Changing the AI prompt

The system prompt is cached by Anthropic (stable prefix). Changing it invalidates the cache — avoid frivolous edits.

User context (non-cached) can be changed freely.

## Changing color step execution

`engine.py:_execute_step()` handles interpolation. Changing this affects all programs. Test with a simple 2-step program first.

## Mapping unknown DPs (46, 47, 53)

See `records/dp-map.md`. Run `tinytuya.BulbDevice.status()` before and after changing a value in the app to capture delta.

## Deploying to VPS

Use `docker compose up --build`. Ensure the VPS is on the same LAN as the device, or has VPN access to it. All credentials via `.env`.
