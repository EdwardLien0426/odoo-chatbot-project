# website_llm_chat

Public-facing chatbot for Odoo 18, powered by RocketRide AI pipeline. Lets website visitors query company data via natural language.

## Architecture

```
Browser
  └─ GET /chatbot/stream (SSE)
       └─ chat_sync(role)  [rocketride_client.py]
            └─ RocketRide ws://5565  (hr_chat_<role>.pipe)
                 └─ agent → mcp_client
                       └─ POST /mcp  [llm_mcp_server]
                             └─ odoo_record_retriever (llm.tool)
```

### Key Files

| File | Purpose |
|------|---------|
| `rocketride_client.py` | Singleton async RocketRide client; manages 3 pipeline tokens (one per role) |
| `pipelines/hr_chat_visitor.pipe` | RocketRide pipeline for anonymous visitors |
| `pipelines/hr_chat_staff.pipe` | RocketRide pipeline for logged-in staff |
| `pipelines/hr_chat_hr_manager.pipe` | RocketRide pipeline for HR managers |
| `controllers/main.py` | `/chatbot` page + `/chatbot/stream` SSE endpoint |
| `static/src/js/chatbot.js` | Frontend SSE consumer + chat UI |

## RocketRide Pipelines (`hr_chat_<role>.pipe`)

Three pipeline files with identical structure; only the MCP Bearer token differs:

```
chat_1 (source) → agent_rocketride_1 → response_answers_1 (sink)
                       ↓ control
                  llm_qwen_1 + mcp_client_1 + memory_internal_1
```

- `mcp_client_1` connects to Odoo `/mcp` endpoint via `streamable-http`
- `serverName: "odoo"` — tools exposed as `odoo.<toolName>` (e.g. `odoo.search_odoo_records`)
- `max_waves: 3` — agent can call tools up to 3 times per question
- `memory_internal` resets per `client.chat()` call — **no cross-turn memory**
- `llm_qwen` region `"intl"` → Singapore endpoint (dashscope-intl.aliyuncs.com)

## RBAC (Role-Based Access Control)

Role is resolved in `main.py:_get_user_role()` and selects the pipeline token in `rocketride_client.py`:

```
_get_user_role() → "visitor" | "staff" | "hr_manager"
  → chat_sync(message, role)
  → get_client(role) selects token → RocketRide uses role-specific Bearer token
  → mcp_client authenticates to Odoo /mcp as the corresponding service account
  → Odoo ACL enforces field/model visibility for that account
```

Roles and their Odoo service accounts:
- `visitor` — `website_visitor_bot` (Portal; no HR group)
- `staff` — `website_staff_bot` (Internal; `hr.group_hr_user`)
- `hr_manager` — `website_hr_manager_bot` (Internal; `hr.group_hr_manager`)

RBAC is enforced entirely by Odoo ACL on the service account — no field filtering in Python code.

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
| `ROCKETRIDE_QWEN_API_KEY` | `hr_chat_*.pipe` | Qwen LLM API key (substituted in .pipe) |
| `ROCKETRIDE_MCP_VISITOR_KEY` | `hr_chat_visitor.pipe` | MCP Bearer token for `website_visitor_bot` Odoo account |
| `ROCKETRIDE_MCP_STAFF_KEY` | `hr_chat_staff.pipe` | MCP Bearer token for `website_staff_bot` Odoo account |
| `ROCKETRIDE_MCP_HR_KEY` | `hr_chat_hr_manager.pipe` | MCP Bearer token for `website_hr_manager_bot` Odoo account |

Only `ROCKETRIDE_*`-prefixed vars are substituted in `.pipe` files.

## Known Gotchas

- `client.use(..., use_existing=True)` is required — without it, Odoo worker restarts trigger "pipeline already running" errors
- `_debug_message` workaround in `rocketride_client.py` — rocketride 1.0.6 bug where `connection.py` calls `_debug_message` but the method is named `debug_message`
- `ROCKETRIDE_URI` env quirk: `dev.sh` exports `ROCKETRIDE_URI=` (empty string) via `set -a; source .env`. Use `os.environ.get("ROCKETRIDE_URI") or "ws://localhost:5565"` — NOT `.get(key, default)`, which ignores the default when the key exists but is empty.
- `RocketRideClient(persist=True)`: `connect()` silently swallows connection failures; it does NOT raise even if the server is unreachable. Always check `client.is_connected()` after `connect()` to detect failure. Symptom: "Server is not connected" raised at `use()` instead of `connect()`.
- Three pipelines share one RocketRide WebSocket client — `_init_client()` calls `client.use()` once per pipe file and stores three tokens in `_tokens` dict.
- Local dev: MCP endpoint is `http://localhost:8069/mcp`. Docker: `http://odoo:8069/mcp` (via `extra_hosts: ["odoo:172.18.0.1"]`).
- MCP API keys are generated per Odoo user via **My Profile → Account Security → New MCP Key** — copy immediately, cannot be retrieved later.

## Docker Setup

See `docker-compose.yml` at repo root. Ports needed:
- `5565` — WebSocket control channel
- `20003` — data channel

## Testing

Unit tests for `rocketride_client.py` pipe mapping (no Odoo or RocketRide needed):
```bash
/home/pohsu/odoo_env/bin/python3 -m unittest tests.test_rocketride_client -v
```
For full Odoo integration tests, use the Odoo test runner with `--test-enable`.

## What's Missing / Known Limitations

- No cross-turn conversation memory (each question is a fresh session)
- Fake streaming only — no true token-level streaming from RocketRide
- `odoo_record_retriever` queries any model the service account can access — LLM decides which fields to request
