from abc import ABC, abstractmethod
from app.domain.entity.analysis import JobMetadata

class JobMetadataRepository(ABC):
    @abstractmethod
    def get_by_id(self, job_id: str) -> JobMetadata:
        pass
