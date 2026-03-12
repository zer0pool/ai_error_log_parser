from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class AnalysisResult(BaseModel):
    category: str
    cause: str
    guide: str
    confidence: float
    logic: Optional[str] = None

class JobMetadata(BaseModel):
    job_id: str
    job_type: str
    owner: str
    historical_fail_rate: float
    last_success: Optional[str] = None
