"""RFC 7807 problem details for every error the API emits.

One shape, one media type (``application/problem+json``), so the frontend has a single error
type to narrow on: ``{type, title, status, detail}``. ``type`` is ``about:blank`` throughout —
the ``title`` carries the classification and ``detail`` the sentence a person reads.
"""

from __future__ import annotations

from typing import Any

from django.http import Http404
from rest_framework import status as http
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

PROBLEM_JSON = "application/problem+json"


class Problem(APIException):
    """An error with an explicit RFC 7807 title and status."""

    def __init__(self, status_code: int, title: str, detail: str) -> None:
        """Build a problem; ``detail`` is shown to the client verbatim."""
        super().__init__(detail=detail)
        self.status_code = status_code
        self.title = title


def _flatten(errors: object, prefix: str = "") -> list[str]:
    """DRF's nested error dict → one "field: message" line per leaf."""
    if isinstance(errors, dict):
        return [
            line
            for key, value in errors.items()
            for line in _flatten(value, f"{prefix}{key}: " if key != "non_field_errors" else "")
        ]
    if isinstance(errors, list):
        return [line for item in errors for line in _flatten(item, prefix)]
    return [f"{prefix}{errors}"]


def problem_response(status_code: int, title: str, detail: str) -> Response:
    """A problem+json response body with the standard four members."""
    body = {"type": "about:blank", "title": title, "status": status_code, "detail": detail}
    return Response(body, status=status_code, content_type=PROBLEM_JSON)


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """DRF ``EXCEPTION_HANDLER``: every handled error becomes problem+json.

    Request validation failures are 422, not DRF's default 400: the body was well-formed
    JSON, it is the *area* that cannot be processed. Unhandled exceptions return None so
    Django's 500 handling applies (a stack trace in DEBUG, a bare 500 otherwise).
    """
    if isinstance(exc, Problem):
        return problem_response(exc.status_code, exc.title, str(exc.detail))
    if isinstance(exc, ValidationError):
        return problem_response(
            http.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid request", "; ".join(_flatten(exc.detail))
        )
    if isinstance(exc, Http404):
        return problem_response(http.HTTP_404_NOT_FOUND, "Not found", str(exc) or "Not found")
    if isinstance(exc, APIException):
        default = drf_exception_handler(exc, context)
        if default is None:
            return None
        return problem_response(
            default.status_code, exc.__class__.__name__, "; ".join(_flatten(exc.detail))
        )
    return None
