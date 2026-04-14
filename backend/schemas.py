from enum import Enum

from pydantic import BaseModel


class PDFStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    error = "error"


class ProjectStatus(str, Enum):
    active = "active"
    processing = "processing"
    ready = "ready"
    error = "error"


# ── Schedule rows ──────────────────────────────────────────────────────────


class ScheduleRow(BaseModel):
    id: str
    mark: int | None = None
    diameter: int
    steel_type: str = "BST500"
    count: int
    length: float
    total_length: float
    weight_per_meter: float
    weight: float
    confidence: str = "medium"  # high | medium | low
    warnings: list[str] = []


class ScheduleResponse(BaseModel):
    id: str
    project_id: str
    status: str  # processing | ready | error
    rows: list[ScheduleRow] = []
    warnings: list[str] = []
    generated_at: str | None = None
    last_edited_at: str | None = None


class ScheduleUpdate(BaseModel):
    rows: list[ScheduleRow]


# ── PDFs ───────────────────────────────────────────────────────────────────


class PDFInfo(BaseModel):
    id: str
    filename: str
    status: PDFStatus
    error: str | None = None
    uploaded_at: str | None = None


# ── Projects ───────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str
    project_number: str | None = None
    beneficiary: str | None = None
    location: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    project_number: str | None = None
    beneficiary: str | None = None
    location: str | None = None
    status: ProjectStatus
    pdfs: list[PDFInfo] = []
    schedule: ScheduleResponse | None = None
    created_at: str


class UploadPDFResponse(BaseModel):
    uploaded: list[PDFInfo]
