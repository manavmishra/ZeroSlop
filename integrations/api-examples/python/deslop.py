"""One REST request, using Python 3.9+ standard-library HTTP and JSON tools."""
import json
import os
import sys
import threading
import urllib.error
import urllib.request

FIELDS = ("text", "status", "before", "after", "scoreChange", "factsPreserved", "passedFinalChecks",
          "independentModelChecks", "modelRequests", "rolesCompleted", "finishingRounds", "scorerVersion", "durationMs", "note")


def approved(result):
    if not isinstance(result, dict) or any(key not in result for key in FIELDS):
        return False
    def score(value):
        return type(value) in (int, float) and 0 <= value <= 100
    before, after = result.get("before"), result.get("after")
    if (not isinstance(before, dict) or not isinstance(after, dict)
            or not score(before.get("score")) or not score(after.get("score"))
            or not isinstance(result["text"], str) or type(result["passedFinalChecks"]) is not bool):
        return False
    return result["factsPreserved"] is True and (
        (result["status"] == "rewritten" and result["passedFinalChecks"] is True)
        or (result["status"] == "already_clear" and type(result["modelRequests"]) is int
            and result["modelRequests"] == 0 and type(result["scoreChange"]) in (int, float)
            and result["scoreChange"] == 0 and before["score"] == after["score"]))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def send(request_body, outcome):
    try:
        request = urllib.request.Request(
            os.environ.get("ZERO_SLOP_API_URL", "https://mcp.zero-slop.ai/v1/deslop"),
            data=json.dumps(request_body).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            response = urllib.request.build_opener(NoRedirect).open(request, timeout=75)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            result = json.loads(response.read())
            if response.status != 200:
                outcome.update(code=1, error={"httpStatus": response.status,
                    "retryAfter": response.headers.get("Retry-After"), "problem": result})
            else:
                outcome.update(code=0 if approved(result) else 3, result=result)
    except Exception:
        outcome.update(code=1, error="Request failed or response was not JSON. The outcome may be unknown.")


def main():
    try:
        body = json.load(sys.stdin)
    except (ValueError, OSError):
        print("Supply one UTF-8 JSON request on stdin.", file=sys.stderr)
        return 1
    outcome = {}
    # urllib's timeout applies to socket operations. The daemon thread also bounds
    # the complete request, including a slowly arriving response, to 75 seconds.
    worker = threading.Thread(target=send, args=(body, outcome), daemon=True)
    worker.start()
    worker.join(timeout=75)
    if worker.is_alive():
        print("Request timed out. No automatic retry; the outcome may be unknown.", file=sys.stderr)
        return 1
    if "result" in outcome:
        print(json.dumps(outcome["result"], ensure_ascii=False))
    if "error" in outcome:
        print(json.dumps(outcome["error"]), file=sys.stderr)
    if outcome["code"] == 3:
        print("Review required. Keep the original until the result has been reviewed.", file=sys.stderr)
    return outcome["code"]


if __name__ == "__main__":
    sys.exit(main())
