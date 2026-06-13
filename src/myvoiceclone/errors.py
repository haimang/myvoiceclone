from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class VoiceCloneError(Exception):
    message: str
    code: str = "voiceclone_error"
    status_code: int = 500
    detail: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        return self.message


class AdapterError(VoiceCloneError):
    def __init__(self, message: str, *, code: str = "adapter_error", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code=code, status_code=502, detail=detail)


class PipelineError(VoiceCloneError):
    def __init__(self, message: str, *, code: str = "pipeline_error", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code=code, status_code=500, detail=detail)


class StorageError(VoiceCloneError):
    def __init__(self, message: str, *, code: str = "storage_error", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code=code, status_code=500, detail=detail)


class ValidationError(VoiceCloneError):
    def __init__(self, message: str, *, code: str = "validation_error", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code=code, status_code=400, detail=detail)


class ResourceNotFoundError(VoiceCloneError):
    def __init__(self, message: str, *, code: str = "resource_not_found", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code=code, status_code=404, detail=detail)
