from pydantic import BaseModel
from typing import Optional


class DeepfakeResult(BaseModel):
    status: str
    is_deepfake: Optional[bool] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None


class EvidenceResponse(BaseModel):
    case_id: str
    sha256_hash: str
    captured_at: str
    source_url: Optional[str] = None
    filename: Optional[str] = None
    ots_status: Optional[str] = None
    deepfake_result: Optional[DeepfakeResult] = None


class ReportRequest(BaseModel):
    case_id: str
