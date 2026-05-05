import hmac
import json
import logging
import os

from odoo import http
from odoo.http import Response, request

_logger = logging.getLogger(__name__)

_HR_API_KEY = os.environ.get("ODOO_HR_API_KEY", "")


class HrApiController(http.Controller):

    @http.route(
        "/api/v1/employees/search",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def search_employees(self, q=None, **kwargs):
        incoming_key = request.httprequest.headers.get("X-Api-Key", "")
        if not _HR_API_KEY or not hmac.compare_digest(incoming_key, _HR_API_KEY):
            return Response(
                json.dumps({"error": "Unauthorized"}),
                status=401,
                headers={"Content-Type": "application/json"},
            )

        q = q.strip() if q else ""
        if not q:
            return Response(
                json.dumps({"error": "Missing required parameter: q"}),
                status=400,
                headers={"Content-Type": "application/json"},
            )
        if len(q) > 200:
            return Response(
                json.dumps({"error": "Parameter q exceeds maximum length"}),
                status=400,
                headers={"Content-Type": "application/json"},
            )

        employees = (
            request.env["hr.employee"]
            .sudo()
            .search(
                ["|", "|",
                 ("name", "ilike", q),
                 ("department_id.name", "ilike", q),
                 ("job_title", "ilike", q)],
                limit=20,
            )
        )

        result = [
            {
                "id": emp.id,
                "name": emp.name,
                "department": emp.department_id.name or "",
                "job_title": emp.job_title or "",
                "work_email": emp.work_email or "",
            }
            for emp in employees
        ]

        return Response(
            json.dumps(result),
            headers={"Content-Type": "application/json"},
        )
