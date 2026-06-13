import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from myvoiceclone.api.routes_recordings import router as recordings_router
from myvoiceclone.api.routes_segments import router as segments_router
from myvoiceclone.api.routes_datasets import router as datasets_router
from myvoiceclone.api.routes_jobs import router as jobs_router
from myvoiceclone.api.routes_training import router as training_router
from myvoiceclone.api.routes_inference import router as inference_router
from myvoiceclone.api.routes_reports import router as reports_router
from myvoiceclone.api.routes_runs import router as runs_router
from myvoiceclone.errors import VoiceCloneError

def create_app() -> FastAPI:
    app = FastAPI(
        title="MyVoiceClone API",
        version="1.0.0",
        description="Local engineering workbench for high-fidelity voice cloning"
    )
    
    # Register routers
    app.include_router(recordings_router, prefix="/api")
    app.include_router(segments_router, prefix="/api")
    app.include_router(datasets_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(training_router, prefix="/api")
    app.include_router(inference_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(runs_router, prefix="/api")

    @app.exception_handler(VoiceCloneError)
    async def voiceclone_error_handler(request: Request, exc: VoiceCloneError):
        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.message,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "trace_id": trace_id,
                    "detail": exc.detail or {},
                },
            },
            headers={"x-trace-id": trace_id},
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException):
        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex
        message = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error": {
                    "code": "http_error",
                    "message": message,
                    "trace_id": trace_id,
                    "detail": {"status_code": exc.status_code},
                },
            },
            headers={"x-trace-id": trace_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex
        return JSONResponse(
            status_code=422,
            content={
                "detail": exc.errors(),
                "error": {
                    "code": "request_validation_error",
                    "message": "Request validation failed",
                    "trace_id": trace_id,
                    "detail": {"errors": exc.errors()},
                },
            },
            headers={"x-trace-id": trace_id},
        )
    
    @app.get("/health")
    def health():
        return {"status": "healthy", "version": "1.0.0"}
        
    return app
