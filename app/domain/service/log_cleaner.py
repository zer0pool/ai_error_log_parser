import re

class LogCleaner:
    @staticmethod
    def clean(log_text: str) -> str:
        # Remove timestamps (YYYY-MM-DD HH:MM:SS)
        log_text = re.sub(r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}', '[TS]', log_text)
        # Remove Hex addresses (0x...)
        log_text = re.sub(r'0x[0-9a-fA-F]+', '[HEX]', log_text)
        # Remove UUIDs
        log_text = re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '[UUID]', log_text)
        # Remove numeric IDs in common patterns (e.g., job_123 -> job_[ID])
        log_text = re.sub(r'(_)\d+', r'\1[ID]', log_text)
        # Normalize whitespace
        log_text = re.sub(r'\s+', ' ', log_text).strip()
        return log_text
