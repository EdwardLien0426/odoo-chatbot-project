import asyncio
import logging
import os
import threading

from rocketride import RocketRideClient
from rocketride.schema import Question

_logger = logging.getLogger(__name__)

_PIPE_FILE = os.path.join(os.path.dirname(__file__), "pipelines", "hr_chat.pipe")

_client: RocketRideClient | None = None
_token: str | None = None
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
    global _client, _token
    uri = os.environ.get("ROCKETRIDE_URI") or "ws://localhost:5565"
    apikey = os.environ.get("ROCKETRIDE_APIKEY", "")
    client = RocketRideClient(uri=uri, auth=apikey, persist=True)
    # Workaround for rocketride 1.0.6 bug: connection.py calls _debug_message
    # but the method is named debug_message in the events mixin.
    if not hasattr(client, "_debug_message"):
        client._debug_message = client.debug_message
    try:
        await client.connect()
        result = await client.use(filepath=_PIPE_FILE, use_existing=True)
    except Exception:
        _client = None
        _token = None
        raise
    _client = client
    _token = result["token"]
    _logger.info("RocketRide HR chat pipeline ready, token=%s", _token)


def get_client() -> tuple[RocketRideClient, str, asyncio.AbstractEventLoop]:
    global _client, _token, _loop
    with _lock:
        if _loop is None:
            thread = threading.Thread(target=_start_background_loop, daemon=True)
            thread.start()
            _loop_ready.wait(timeout=5)

        if _client is None:
            future = asyncio.run_coroutine_threadsafe(_init_client(), _loop)
            future.result(timeout=30)

    return _client, _token, _loop


def tag_message(text: str, role: str) -> str:
    return f"{text}\n[SYSTEM_ROLE:{role}]"


def chat_sync(question_text: str, user_role: str = "visitor") -> str:
    client, token, loop = get_client()
    q = Question()
    q.addQuestion(tag_message(question_text, user_role))
    future = asyncio.run_coroutine_threadsafe(
        client.chat(token=token, question=q),
        loop,
    )
    result = future.result(timeout=60)
    answers = result.get("answers", [])
    return answers[0] if answers else ""
