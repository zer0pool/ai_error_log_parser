from app.domain.entity.analysis import JobMetadata
from app.domain.repository.job_metadata_repository import JobMetadataRepository

class MockJobMetadataRepository(JobMetadataRepository):
    def get_by_id(self, job_id: str) -> JobMetadata:
        # Mocking logic
        job_type = "SQL" if "sql" in job_id.lower() else "Notebook"
        return JobMetadata(
            job_id=job_id,
            job_type=job_type,
            owner="data_platform_team",
            historical_fail_rate=0.12,
            last_success="2024-03-12 10:00:00"
        )
