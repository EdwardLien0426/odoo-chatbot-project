import json
import logging
import time

from odoo import http
from odoo.http import Response, request

from ..rocketride_client import chat_sync

_logger = logging.getLogger(__name__)


class WebsiteLLMChatController(http.Controller):

    @http.route("/chatbot", type="http", auth="public", website=True)
    def chatbot_page(self):
        return request.render("website_llm_chat.chatbot_page")

    @classmethod
    def _stream(cls, message: str):
        # Phase 1: immediate feedback so the browser sees a response right away
        yield b'data: {"type": "thinking"}\n\n'

        # Phase 2: blocking call to RocketRide (runs on dedicated asyncio thread)
        try:
            answer = chat_sync(message)
        except Exception as e:
            _logger.exception("RocketRide chat failed for message: %r", message)
            yield f'data: {json.dumps({"type": "error", "error": str(e)})}\n\n'.encode()
            return

        # Phase 3: fake streaming — each chunk carries accumulated text so JS
        # innerHTML = data.content (replace, not append) renders correctly
        words = answer.split()
        accumulated = ""
        for i, word in enumerate(words):
            accumulated += word
            if i < len(words) - 1:
                accumulated += " "
            yield f'data: {json.dumps({"type": "chunk", "content": accumulated})}\n\n'.encode()
            time.sleep(0.04)

        yield b'data: {"type": "done"}\n\n'

    @http.route(
        "/chatbot/stream",
        type="http",
        auth="public",
        csrf=False,
        methods=["GET"],
    )
    def chatbot_stream(self, message=None, **kwargs):
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }

        if not message or not message.strip():
            def _err():
                yield f'data: {json.dumps({"type": "error", "error": "Message cannot be empty"})}\n\n'.encode()
            return Response(_err(), direct_passthrough=True, headers=headers)

        return Response(
            self._stream(message.strip()),
            direct_passthrough=True,
            headers=headers,
        )
