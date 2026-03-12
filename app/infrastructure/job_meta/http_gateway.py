import httpx
from app.domain.entity.analysis import JobMetadata
from app.domain.repository.job_metadata_repository import JobMetadataRepository

class HttpJobMetadataGateway(JobMetadataRepository):
    """
    Fetches job metadata from an external scheduling service API.
    Replace base_url and auth logic to match the actual API.
    """

    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def get_by_id(self, job_id: str) -> JobMetadata:
        """
        Calls GET /jobs/{job_id} and maps the response to JobMetadata.
        Falls back to a sensible default if the API is unreachable.
        """
        url = f"{self.base_url}/job-manager/api/v1/job/{job_id}"
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()

                return JobMetadata(
                    job_id=job_id,
                    # Map these field names to match your actual API response shape
                    job_type=data.get("job_type", "Unknown"),
                    owner=data.get("owner", "Unknown"),
                    historical_fail_rate=data.get("fail_rate", 0.0),
                    last_success=data.get("last_success_dt"),
                )

        except httpx.HTTPStatusError as e:
            raise ValueError(f"Job metadata API returned {e.response.status_code} for job_id={job_id}") from e

        except (httpx.RequestError, httpx.TimeoutException):
            # Graceful degradation: return minimal info so analysis can still run
            print(f"[warn] Job metadata API unreachable for {job_id}. Using default metadata.")
            return JobMetadata(
                job_id=job_id,
                job_type="Unknown",
                owner="Unknown",
                historical_fail_rate=0.0,
            )
