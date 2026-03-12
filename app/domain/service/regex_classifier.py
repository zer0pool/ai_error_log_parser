import re

class RegexClassifier:
    def classify(self, log: str) -> str:
        patterns = {
            r"fin_history_sensor_.*failed": "SENSOR_TIMEOUT",
            r"google\.cloud\.bigquery\.dbapi\.OperationalError: 400 Provided Schema does not match": "BQ_SCHEMA_MISMATCH",
            r"BigQuery .* 403 .* access denied": "BQ_AUTH_ERROR",
            r"Job execution exceeded .* limit of 6 hours": "BQ_6HR_TIMEOUT",
            r"pandas.*MemoryError": "GKE_OOM",
            r"pyspark.*MemoryError": "GKE_OOM",
            r"DataFrame.*columns mismatch": "SCHEMA_MISMATCH",
            r"Connection reset by peer": "NETWORK_RESET",
            r"Permission denied \(publickey\)": "AUTH_ERROR",
            r"ModuleNotFoundError": "LIBRARY_MISSING"
        }
        
        for pattern, cat in patterns.items():
            if re.search(pattern, log, re.IGNORECASE):
                return cat
        return "Unknown"
