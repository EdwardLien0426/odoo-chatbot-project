_VISITOR_FIELDS = ("name", "department", "job_title")
_PRIVILEGED_FIELDS = ("name", "department", "job_title", "work_email")


def get_allowed_fields(role: str) -> tuple[str, ...]:
    if role in ("staff", "hr_manager"):
        return _PRIVILEGED_FIELDS
    return _VISITOR_FIELDS
