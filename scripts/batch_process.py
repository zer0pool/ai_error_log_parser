import pandas as pd
import sys
import os
import glob

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.domain.service.log_preprocessor import LogPreprocessor

def main(input_dir: str, output_csv: str):
    if not os.path.exists(input_dir):
        print(f"Error: Input directory {input_dir} not found.")
        return

    # Find all CSV files in the input directory
    csv_files = glob.glob(os.path.join(input_dir, "*.csv"))
    if not csv_files:
        print(f"No CSV files found in {input_dir}")
        return

    print(f"Loading {len(csv_files)} log files from {input_dir}...")
    
    # Concatenate all dataframes
    all_dfs = []
    for f in csv_files:
        temp_df = pd.read_csv(f)
        all_dfs.append(temp_df)
    
    df = pd.concat(all_dfs, ignore_index=True)
    print(f"Total logs to process: {len(df)}")
    
    preprocessor = LogPreprocessor()
    print("Processing logs... This might take a while for large datasets.")
    
    processed_df = preprocessor.process_dataframe(df)
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    processed_df.to_csv(output_csv, index=False)
    print(f"Success! Processed {len(df)} logs into {len(processed_df)} unique patterns.")
    print(f"Results saved to {output_csv}")

if __name__ == "__main__":
    # Default paths
    input_dir = "data/raw"
    output_path = "data/processed_patterns.csv"
    main(input_dir, output_path)
