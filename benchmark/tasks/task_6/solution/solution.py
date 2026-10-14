#!/usr/bin/env python3
"""
Solution for CSV merge task.
Reads all CSV files in the current directory, merges them on shared columns,
and writes the merged result to merged_output.csv
"""

import pandas as pd
import glob
import os

def main():
    # Find all CSV files in current directory
    csv_files = glob.glob("*.csv")
    
    if not csv_files:
        print("No CSV files found in current directory")
        return
    
    print(f"Found {len(csv_files)} CSV files: {csv_files}")
    
    # Read all CSV files
    dataframes = []
    for csv_file in sorted(csv_files):  # Sort for deterministic order
        df = pd.read_csv(csv_file)
        dataframes.append(df)
        print(f"  {csv_file}: {len(df)} rows, columns: {list(df.columns)}")
    
    # Find common columns (join keys)
    if not dataframes:
        print("No dataframes to merge")
        return
    
    common_columns = set(dataframes[0].columns)
    for df in dataframes[1:]:
        common_columns = common_columns.intersection(set(df.columns))
    
    if not common_columns:
        print("ERROR: No common columns found across CSV files")
        return
    
    join_key = list(common_columns)[0]  # Use first common column as join key
    print(f"Using '{join_key}' as join key")
    
    # Merge dataframes on the common column
    merged = dataframes[0]
    for df in dataframes[1:]:
        merged = merged.merge(df, on=join_key, how='outer')
    
    # Write merged result
    output_file = "merged_output.csv"
    merged.to_csv(output_file, index=False)
    print(f"✓ Merged {len(dataframes)} files into {output_file}")
    print(f"  Output: {len(merged)} rows, {len(merged.columns)} columns")

if __name__ == "__main__":
    main()
