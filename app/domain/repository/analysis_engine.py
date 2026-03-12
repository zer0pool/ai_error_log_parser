from abc import ABC, abstractmethod
from app.domain.entity.analysis import AnalysisResult, JobMetadata
from typing import List

class AnalysisEngine(ABC):
    @abstractmethod
    def analyze(
        self, 
        trace_log: str, 
        regex_category: str, 
        job_metadata: JobMetadata, 
        context_docs: List[str]
    ) -> AnalysisResult:
        pass
