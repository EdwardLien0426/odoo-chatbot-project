# website_llm_chat

Public-facing chatbot for Odoo 18, powered by RocketRide AI pipeline. Lets website visitors query HR employee data via natural language.

## Architecture

```
Browser
  └─ GET /chatbot/stream (SSE)
       └─ chat_sync()  [rocketride_client.py]
            └─ RocketRide ws://5565  (hr_chat.pipe)
                 └─ agent → tool_http_request
                       └─ GET /api/v1/employees/search  [hr_api.py]
```

### Key Files

| File | Purpose |
|------|---------|
| `rocketride_client.py` | Singleton async RocketRide client + sync bridge |
| `pipelines/hr_chat.pipe` | RocketRide pipeline definition |
| `controllers/main.py` | `/chatbot` page + `/chatbot/stream` SSE endpoint |
| `controllers/hr_api.py` | `/api/v1/employees/search` — HR data API for the pipeline tool |
| `static/src/js/chatbot.js` | Frontend SSE consumer + chat UI |

## RocketRide Pipeline (`hr_chat.pipe`)

Components wired together:

```
chat_1 (source) → agent_rocketride_1 → response_answers_1 (sink)
                       ↓ control
                  llm_qwen_1 + tool_http_request_1 + memory_internal_1
```

- `max_waves: 3` — agent can call the tool up to 3 times per question
- `memory_internal` resets per `client.chat()` call — **no cross-turn memory**
- `llm_qwen` region `"intl"` → Singapore endpoint (dashscope-intl.aliyuncs.com)

## Streaming Model

RocketRide returns the full answer in one shot (no token streaming).
`main.py:_stream()` implements fake streaming: splits answer into words,
yields each chunk with **accumulated** text so `innerHTML = data.content` (replace, not append) works correctly.

SSE event types emitted:
- `{"type": "thinking"}` — immediate, before RocketRide call
- `{"type": "chunk", "content": "<accumulated text>"}` — word by word
- `{"type": "done"}`
- `{"type": "error", "error": "..."}`


## Environment Variables

| Variable | Used in | Purpose |
|----------|---------|---------|
| `ROCKETRIDE_URI` | `rocketride_client.py` | WebSocket URL, default `ws://localhost:5565` |
| `ROCKETRIDE_APIKEY` | `rocketride_client.py` | Auth for RocketRide control channel |
| `ROCKETRIDE_QWEN_API_KEY` | `hr_chat.pipe` | Qwen LLM API key (substituted in .pipe) |
| `ROCKETRIDE_ODOO_HR_API_KEY` | `hr_chat.pipe` + `hr_api.py` | Shared secret for pipeline → Odoo tool calls |
| `ODOO_HR_API_KEY` | `hr_api.py` | Same key read by Odoo side |

Only `ROCKETRIDE_*`-prefixed vars are substituted in `.pipe` files.

## Known Gotchas

- `client.use(..., use_existing=True)` is required — without it, Odoo worker restarts trigger "pipeline already running" errors
- `_debug_message` workaround in `rocketride_client.py:35-37` — rocketride 1.0.6 bug where `connection.py` calls `_debug_message` but the method is named `debug_message`
- `auth="public"` (not `auth="none"`) on HR API route — `auth="none"` breaks `.sudo()` ORM access
- `urlWhitelist` patterns in the pipe use `^...$` anchors to prevent SSRF
- Docker: RocketRide container reaches Odoo at `odoo:8069` via `extra_hosts: ["odoo:172.18.0.1"]`
- `ROCKETRIDE_URI` env quirk: `dev.sh` exports `ROCKETRIDE_URI=` (empty string) via `set -a; source .env`. Use `os.environ.get("ROCKETRIDE_URI") or "ws://localhost:5565"` — NOT `.get(key, default)`, which ignores the default when the key exists but is empty.
- `RocketRideClient(persist=True)`: `connect()` silently swallows connection failures; it does NOT raise even if the server is unreachable. Always check `client.is_connected()` after `connect()` to detect failure. Symptom: "Server is not connected" raised at `use()` instead of `connect()`.

## Docker Setup

See `docker-compose.yml` at repo root. Ports needed:
- `5565` — WebSocket control channel
- `20003` — data channel

## What's Missing / Known Limitations

- No cross-turn conversation memory (each question is a fresh session)
- Fake streaming only — no true token-level streaming from RocketRide
- HR search limited to name / department / job_title fields, max 20 results
