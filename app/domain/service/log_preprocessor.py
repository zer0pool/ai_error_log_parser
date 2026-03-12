import re
import pandas as pd
from app.domain.service.log_cleaner import LogCleaner

class LogPreprocessor:
    """
    Groups identical patterns and calculates frequency.
    """
    
    def process_dataframe(self, df: pd.DataFrame, log_column: str = 'trace_log') -> pd.DataFrame:
        """
        Groups identical patterns and calculates frequency.
        """
        df['cleaned_pattern'] = df[log_column].apply(LogCleaner.clean)
        
        # Group by pattern and keep representative original log and count
        grouped = df.groupby('cleaned_pattern').agg({
            log_column: 'first',
            'id': 'count'
        }).rename(columns={
            log_column: 'representative_log',
            'id': 'occurrence_count'
        }).reset_index()
        
        return grouped.sort_values(by='occurrence_count', ascending=False)
