"""Private HTTP service binding for the exact Zero Slop scorer."""

from __future__ import annotations

import json
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

from scorer_core import ScorerInputError, delta, health, rank, report


HEADERS = {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
}


def respond(payload, status=200):
    return Response(json.dumps(payload, ensure_ascii=False), status=status, headers=HEADERS)


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlparse(str(request.url)).path
        if request.method == "GET" and path == "/health":
            return respond(health())
        if request.method != "POST":
            return respond({"error": "method_not_allowed"}, 405)

        try:
            body = await request.json()
            if path == "/report":
                return respond(report(body.get("text"), body.get("genre")))
            if path == "/rank":
                return respond(rank(body.get("original"), body.get("candidates"), body.get("genre")))
            if path == "/delta":
                return respond(delta(body.get("original"), body.get("rewrite")))
            return respond({"error": "not_found"}, 404)
        except (ScorerInputError, KeyError, TypeError, ValueError) as error:
            return respond({"error": "invalid_input", "message": str(error)}, 400)
        except Exception:
            # Never leak a draft or a traceback across the service boundary.
            return respond({"error": "scorer_unavailable"}, 503)
