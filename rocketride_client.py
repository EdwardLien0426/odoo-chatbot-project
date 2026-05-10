import asyncio
import logging
import os
import threading

from rocketride import RocketRideClient
from rocketride.schema import Question

_logger = logging.getLogger(__name__)

_PIPE_DIR = os.path.dirname(__file__)
_PIPE_FILES = {
    "visitor": os.path.join(_PIPE_DIR, "pipelines", "hr_chat_visitor.pipe"),
    "staff": os.path.join(_PIPE_DIR, "pipelines", "hr_chat_staff.pipe"),
    "hr_manager": os.path.join(_PIPE_DIR, "pipelines", "hr_chat_hr_manager.pipe"),
}

_client: RocketRideClient | None = None
_tokens: dict[str, str] = {}
_loop: asyncio.AbstractEventLoop | None = None
_lock = threading.Lock()
_loop_ready = threading.Event()


def _start_background_loop() -> None:
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop_ready.set()
    _loop.run_forever()


async def _init_client() -> None:
    global _client, _tokens
    uri = os.environ.get("ROCKETRIDE_URI") or "ws://localhost:5565"
    apikey = os.environ.get("ROCKETRIDE_APIKEY", "")
    client = RocketRideClient(uri=uri, auth=apikey, persist=True)
    # Workaround: rocketride 1.0.6 names the method debug_message but calls _debug_message
    if not hasattr(client, "_debug_message"):
        client._debug_message = client.debug_message
    try:
        await client.connect()
        roles = list(_PIPE_FILES.keys())
        results = await asyncio.gather(*[
            client.use(filepath=_PIPE_FILES[r], use_existing=True)
            for r in roles
        ])
        tokens = {r: res["token"] for r, res in zip(roles, results)}
    except Exception:
        _client = None
        _tokens = {}
        raise
    _client = client
    _tokens = tokens
    _logger.info("RocketRide pipelines ready, roles=%s", list(tokens.keys()))


def get_client(role: str = "visitor") -> tuple[RocketRideClient, str, asyncio.AbstractEventLoop]:
    global _client, _tokens, _loop
    with _lock:
        if _loop is None:
            thread = threading.Thread(target=_start_background_loop, daemon=True)
            thread.start()
            _loop_ready.wait(timeout=5)

        if _client is None:
            future = asyncio.run_coroutine_threadsafe(_init_client(), _loop)
            future.result(timeout=30)

    token = _tokens.get(role) or _tokens.get("visitor")
    if token is None:
        raise RuntimeError(f"No pipeline token for role={role!r} and no visitor fallback")
    return _client, token, _loop


def chat_sync(question_text: str, user_role: str = "visitor") -> str:
    client, token, loop = get_client(user_role)
    q = Question()
    q.addQuestion(question_text)
    future = asyncio.run_coroutine_threadsafe(
        client.chat(token=token, question=q),
        loop,
    )
    result = future.result(timeout=60)
    answers = result.get("answers", [])
    return answers[0] if answers else ""
