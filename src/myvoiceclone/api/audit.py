import json
import time
from typing import Any, Dict, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from myvoiceclone.config import resolve_db_path
from myvoiceclone.ids import is_mvc_id, new_id
from myvoiceclone.storage.repositories import dict_to_json
from myvoiceclone.storage.sqlite import get_connection


def _safe_json(data: bytes) -> Dict[str, Any]:
    if not data:
        return {}
    try:
        parsed = json.loads(data.decode("utf-8"))
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def _extract_error_code(response_json: Dict[str, Any], status_code: int) -> Optional[str]:
    error = response_json.get("error")
    if isinstance(error, dict) and error.get("code"):
        return str(error["code"])
    if status_code >= 400:
        return "http_error"
    return None


def _extract_ids(path: str, response_json: Dict[str, Any]) -> Dict[str, Optional[str]]:
    ids: Dict[str, Optional[str]] = {"run_id": None, "job_id": None, "artifact_id": None}
    parts = path.strip("/").split("/")
    for index, part in enumerate(parts[:-1]):
        value = parts[index + 1]
        if not is_mvc_id(value):
            continue
        if part == "runs":
            ids["run_id"] = value
        elif part == "jobs":
            ids["job_id"] = value
        elif part == "artifacts":
            ids["artifact_id"] = value

    endpoint = parts[-1] if parts else ""
    body_id = response_json.get("id")
    if is_mvc_id(body_id):
        if response_json.get("artifact_type"):
            ids["artifact_id"] = ids["artifact_id"] or body_id
        elif response_json.get("name") in {"infer_real", "preprocess_all", "eval_first_test", "ingest", "train_sovits"}:
            ids["job_id"] = ids["job_id"] or body_id
        elif endpoint == "runs" or response_json.get("links", {}).get("status"):
            ids["run_id"] = ids["run_id"] or body_id

    if is_mvc_id(response_json.get("run_id")):
        ids["run_id"] = ids["run_id"] or response_json["run_id"]
    return ids


class ApiAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        header_trace_id = request.headers.get("x-trace-id")
        trace_id = header_trace_id if is_mvc_id(header_trace_id) else new_id()
        request.state.trace_id = trace_id
        started = time.monotonic()
        request_body = await request.body()
        request_json = _safe_json(request_body)
        response = await call_next(request)

        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        response_json = _safe_json(response_body)
        duration_ms = int((time.monotonic() - started) * 1000)
        ids = _extract_ids(request.url.path, response_json)
        error_code = _extract_error_code(response_json, response.status_code)
        self._write_log(
            trace_id=trace_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            error_code=error_code,
            ids=ids,
            request_json=request_json,
            response_json=response_json,
            client_host=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            duration_ms=duration_ms,
        )

        headers = dict(response.headers)
        headers["x-trace-id"] = trace_id
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
            background=response.background,
        )

    def _write_log(
        self,
        *,
        trace_id: str,
        method: str,
        path: str,
        status_code: int,
        error_code: Optional[str],
        ids: Dict[str, Optional[str]],
        request_json: Dict[str, Any],
        response_json: Dict[str, Any],
        client_host: Optional[str],
        user_agent: Optional[str],
        duration_ms: int,
    ) -> None:
        try:
            conn = get_connection(resolve_db_path(), load_vec=True)
            try:
                conn.execute(
                    """
                    INSERT INTO api_request_logs (
                        id, trace_id, method, path, status_code, error_code,
                        run_id, job_id, artifact_id, request_json, response_json,
                        client_host, user_agent, finished_at, duration_ms
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?);
                    """,
                    (
                        new_id(),
                        trace_id,
                        method,
                        path,
                        status_code,
                        error_code,
                        ids.get("run_id"),
                        ids.get("job_id"),
                        ids.get("artifact_id"),
                        dict_to_json(request_json),
                        dict_to_json(response_json),
                        client_host,
                        user_agent,
                        duration_ms,
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception:
            # Audit logging must never break the API request path.
            return
