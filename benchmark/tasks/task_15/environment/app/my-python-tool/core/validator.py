"""
Data validation module for checking data integrity.
"""

from typing import Dict, List, Any

class DataValidator:
    """Validates data according to specified rules."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the data validator.
        
        Args:
            config: Configuration dictionary with validation rules
        """
        self.config = config
        self.required_fields = config.get('required_fields', [])
        self.field_types = config.get('field_types', {})
    
    def validate(self, data: List[Dict[str, Any]]) -> bool:
        """
        Validate a list of data items.
        
        Args:
            data: List of data dictionaries to validate
            
        Returns:
            True if all items are valid, False otherwise
        """
        if not isinstance(data, list):
            return False
        
        for item in data:
            if not self.validate_item(item):
                return False
        return True
    
    def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validate a single data item.
        
        Args:
            item: Data dictionary to validate
            
        Returns:
            True if item is valid, False otherwise
        """
        # Check required fields
        for field in self.required_fields:
            if field not in item:
                return False
        
        # Check field types
        for field, expected_type in self.field_types.items():
            if field in item:
                if not isinstance(item[field], expected_type):
                    return False
        
        return True
    
    def get_validation_errors(self, data: List[Dict[str, Any]]) -> List[str]:
        """
        Get list of validation errors.
        
        Args:
            data: List of data items to check
            
        Returns:
            List of error messages
        """
        errors = []
        if not isinstance(data, list):
            errors.append("Data must be a list")
            return errors
        
        for i, item in enumerate(data):
            # Check required fields
            for field in self.required_fields:
                if field not in item:
                    errors.append(f"Item {i}: Missing required field '{field}'")
            
            # Check field types
            for field, expected_type in self.field_types.items():
                if field in item:
                    if not isinstance(item[field], expected_type):
                        errors.append(
                            f"Item {i}: Field '{field}' must be of type {expected_type.__name__}"
                        )
        
        return errors
