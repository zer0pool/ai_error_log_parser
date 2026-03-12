from pydantic import BaseModel
from typing import Optional

class AnalysisRequest(BaseModel):
    job_id: str
    trace_log: str

class AnalysisResponse(BaseModel):
    job_id: str
    category: str
    cause: str
    guide: str
    confidence: float
    logic: Optional[str] = None
