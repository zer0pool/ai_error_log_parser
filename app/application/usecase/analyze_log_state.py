from typing import TypedDict, List, Dict, Any, Optional
from app.domain.entity.analysis import AnalysisResult, JobMetadata

class AnalyzeLogState(TypedDict):
    # Input
    job_id: str
    trace_log: str
    
    # Processed Data (Accumulated)
    job_metadata: Optional[JobMetadata]
    regex_category: Optional[str]
    retrieved_docs: List[str]
    
    # Results
    analysis: Optional[AnalysisResult]
    email_body: Optional[str]
    
    # Flow
    errors: List[str]
