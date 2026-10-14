"""
Data processing module for handling data transformations.
"""

import json
import csv
from typing import Dict, List, Any

class DataProcessor:
    """Processes data files and performs transformations."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the data processor.
        
        Args:
            config: Configuration dictionary with processing settings
        """
        self.config = config
        self.output_format = config.get('output_format', 'json')
    
    def load_data(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load data from a file.
        
        Args:
            file_path: Path to the input file
            
        Returns:
            List of dictionaries containing the data
        """
        if file_path.endswith('.json'):
            return self._load_json(file_path)
        elif file_path.endswith('.csv'):
            return self._load_csv(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
    
    def _load_json(self, file_path: str) -> List[Dict[str, Any]]:
        """Load JSON file."""
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def _load_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """Load CSV file."""
        data = []
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    
    def process(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process the data according to configuration.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed data
        """
        processed = []
        for item in data:
            processed_item = self._transform_item(item)
            processed.append(processed_item)
        return processed
    
    def _transform_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single data item."""
        transformed = {}
        for key, value in item.items():
            # Apply transformations based on config
            if self.config.get('uppercase_keys', False):
                key = key.upper()
            if self.config.get('normalize_strings', False) and isinstance(value, str):
                value = value.strip().lower()
            transformed[key] = value
        return transformed
    
    def save_result(self, data: List[Dict[str, Any]], file_path: str):
        """
        Save processed data to a file.
        
        Args:
            data: Data to save
            file_path: Output file path
        """
        if file_path.endswith('.json'):
            self._save_json(data, file_path)
        elif file_path.endswith('.csv'):
            self._save_csv(data, file_path)
        else:
            raise ValueError(f"Unsupported output format: {file_path}")
    
    def _save_json(self, data: List[Dict[str, Any]], file_path: str):
        """Save data as JSON."""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_csv(self, data: List[Dict[str, Any]], file_path: str):
        """Save data as CSV."""
        if not data:
            return
        with open(file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
