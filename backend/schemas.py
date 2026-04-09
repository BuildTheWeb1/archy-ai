from enum import Enum
from pydantic import BaseModel


class DrawingStatus(str, Enum):
    uploading   = "uploading"
    processing  = "processing"
    ready       = "ready"
    error       = "error"


class DrawingSchema(BaseModel):
    id:       str
    filename: str
    status:   DrawingStatus
    error:    str | None = None


class UploadResponse(BaseModel):
    id:     str
    status: DrawingStatus
