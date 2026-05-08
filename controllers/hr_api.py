import hmac
import json
import logging
import os

from odoo import http
from odoo.http import Response, request

from ..rbac import get_allowed_fields

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
    def search_employees(self, q=None, role="visitor", **kwargs):
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

        allowed = get_allowed_fields(role)
        full_data = {
            "name": lambda e: e.name,
            "department": lambda e: e.department_id.name or "",
            "job_title": lambda e: e.job_title or "",
            "work_email": lambda e: e.work_email or "",
        }
        result = [
            {"id": emp.id, **{f: full_data[f](emp) for f in allowed}}
            for emp in employees
        ]

        return Response(
            json.dumps(result),
            headers={"Content-Type": "application/json"},
        )
