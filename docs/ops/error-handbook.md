# MyVoiceClone Error Handbook

Scope: first-test runtime/API error contract.

## Error Response Shape

API errors return the legacy `detail` field plus a structured `error` object:

```json
{
  "detail": "Recording not found",
  "error": {
    "code": "http_error",
    "message": "Recording not found",
    "trace_id": "request-trace-id",
    "detail": {"status_code": 404}
  }
}
```

The `x-trace-id` response header mirrors `error.trace_id`.

## Error Code Families

| Code | Source | Typical action |
|---|---|---|
| `request_validation_error` | FastAPI request parsing | Fix request body/query parameters. |
| `http_error` | Route-level HTTPException | Inspect `detail` and route contract. |
| `validation_error` | Domain validation | Fix caller input or payload shape. |
| `resource_not_found` | Domain lookup | Verify referenced DB/artifact ID exists. |
| `adapter_error` | External adapter/tool | Check preflight, binary/model cache, and `MOCK_ADAPTERS`. |
| `pipeline_error` | Pipeline execution | Inspect job_events for the failed step and traceback. |
| `storage_error` | DB/artifact store | Check migrations, write permissions, and artifact root. |

## Runtime Evidence

`job_events.metadata_json` stores `error`, `error_type`, and `traceback` for failed jobs and failed steps. Evidence packs export these events through `trace.json`.
