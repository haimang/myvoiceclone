from fastapi import FastAPI
from myvoiceclone.api.routes_recordings import router as recordings_router
from myvoiceclone.api.routes_segments import router as segments_router
from myvoiceclone.api.routes_datasets import router as datasets_router
from myvoiceclone.api.routes_jobs import router as jobs_router
from myvoiceclone.api.routes_training import router as training_router
from myvoiceclone.api.routes_inference import router as inference_router
from myvoiceclone.api.routes_reports import router as reports_router
from myvoiceclone.api.routes_runs import router as runs_router

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
    
    @app.get("/health")
    def health():
        return {"status": "healthy", "version": "1.0.0"}
        
    return app
