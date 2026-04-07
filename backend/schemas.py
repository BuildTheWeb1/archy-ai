from enum import Enum
from pydantic import BaseModel


class DrawingStatus(str, Enum):
    uploading = "uploading"
    processing = "processing"
    ready = "ready"
    error = "error"


class LayoutSchema(BaseModel):
    index: int
    name: str


class DrawingSchema(BaseModel):
    id: str
    filename: str
    status: DrawingStatus
    error: str | None = None
    layouts: list[LayoutSchema] = []


class UploadResponse(BaseModel):
    id: str
    status: DrawingStatus
