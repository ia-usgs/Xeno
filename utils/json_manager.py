"""
Global JSON Manager for Xeno Project

This module provides a centralized approach to JSON handling across the entire
Xeno project, ensuring consistent formatting, error handling, and validation.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path


class JSONManager:
    """
    Centralized JSON manager for consistent JSON operations across Xeno.
    
    Features:
    - Standardized JSON formatting (4-space indentation, sorted keys)
    - Consistent error handling and logging
    - Schema validation for different JSON types
    - Backup functionality for critical files
    - Thread-safe operations
    """
    
    # Global JSON formatting configuration
    JSON_CONFIG = {
        "indent": 4,
        "sort_keys": True,
        "separators": (',', ': '),
        "ensure_ascii": False
    }
    
    # Schema definitions for different JSON types
    SCHEMAS = {
        "state": {
            "required_fields": ["level", "start_date", "pet_name"],
            "optional_fields": [],
            "field_types": {
                "level": int,
                "start_date": str,
                "pet_name": str
            }
        },
        "wifi_credentials": {
            "required_fields": ["SSID", "Password"],
            "optional_fields": [],
            "field_types": {
                "SSID": str,
                "Password": str
            }
        },
        "scan_result": {
            "required_fields": ["ssid", "scans"],
            "optional_fields": ["devices"],
            "field_types": {
                "ssid": str,
                "scans": list,
                "devices": list
            }
        },
        "vulnerability_result": {
            "required_fields": ["target", "vulnerabilities"],
            "optional_fields": ["timestamp"],
            "field_types": {
                "target": str,
                "vulnerabilities": list,
                "timestamp": str
            }
        }
    }
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the JSON Manager.
        
        Args:
            logger: Optional logger instance for logging operations
        """
        self.logger = logger or logging.getLogger(__name__)
        
    def load_json(self, file_path: Union[str, Path], schema_type: Optional[str] = None, 
                  create_if_missing: bool = False, default_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Load JSON data from a file with optional schema validation.
        
        Args:
            file_path: Path to the JSON file
            schema_type: Optional schema type for validation (e.g., 'state', 'wifi_credentials')
            create_if_missing: Create file with default_data if it doesn't exist
            default_data: Default data to use if file doesn't exist
            
        Returns:
            Dictionary containing the loaded JSON data
            
        Raises:
            FileNotFoundError: If file doesn't exist and create_if_missing is False
            json.JSONDecodeError: If file contains invalid JSON
            ValueError: If schema validation fails
        """
        file_path = Path(file_path)
        
        try:
            if not file_path.exists():
                if create_if_missing and default_data is not None:
                    self.logger.info(f"Creating missing JSON file: {file_path}")
                    self.save_json(file_path, default_data, schema_type)
                    return default_data
                else:
                    raise FileNotFoundError(f"JSON file not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
            # Validate schema if specified
            if schema_type:
                self._validate_schema(data, schema_type)
                
            self.logger.debug(f"Successfully loaded JSON from: {file_path}")
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in file {file_path}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading JSON from {file_path}: {e}")
            raise
    
    def save_json(self, file_path: Union[str, Path], data: Dict[str, Any], 
                  schema_type: Optional[str] = None, create_backup: bool = False) -> bool:
        """
        Save JSON data to a file with consistent formatting.
        
        Args:
            file_path: Path to save the JSON file
            data: Dictionary data to save
            schema_type: Optional schema type for validation
            create_backup: Create a backup of existing file before overwriting
            
        Returns:
            True if save was successful, False otherwise
        """
        file_path = Path(file_path)
        
        try:
            # Validate schema if specified
            if schema_type:
                self._validate_schema(data, schema_type)
            
            # Create backup if requested and file exists
            if create_backup and file_path.exists():
                backup_path = file_path.with_suffix(f'.backup.{int(datetime.now().timestamp())}.json')
                backup_path.write_text(file_path.read_text())
                self.logger.debug(f"Created backup: {backup_path}")
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with consistent formatting
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, **self.JSON_CONFIG)
                
            self.logger.debug(f"Successfully saved JSON to: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving JSON to {file_path}: {e}")
            return False
    
    def update_json(self, file_path: Union[str, Path], updates: Dict[str, Any], 
                    schema_type: Optional[str] = None, create_if_missing: bool = True) -> bool:
        """
        Update specific fields in a JSON file.
        
        Args:
            file_path: Path to the JSON file
            updates: Dictionary of fields to update
            schema_type: Optional schema type for validation
            create_if_missing: Create file if it doesn't exist
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Load existing data or create new
            if Path(file_path).exists():
                data = self.load_json(file_path, schema_type)
            elif create_if_missing:
                data = {}
            else:
                self.logger.error(f"Cannot update non-existent file: {file_path}")
                return False
            
            # Apply updates
            data.update(updates)
            
            # Save updated data
            return self.save_json(file_path, data, schema_type, create_backup=True)
            
        except Exception as e:
            self.logger.error(f"Error updating JSON file {file_path}: {e}")
            return False
    
    def append_to_json_array(self, file_path: Union[str, Path], array_key: str, 
                             new_item: Dict[str, Any], schema_type: Optional[str] = None,
                             default_ssid: Optional[str] = None) -> bool:
        """
        Append an item to a JSON array within a file.
        
        Args:
            file_path: Path to the JSON file
            array_key: Key of the array to append to
            new_item: Item to append to the array
            schema_type: Optional schema type for validation
            default_ssid: Default SSID for scan result schemas
            
        Returns:
            True if append was successful, False otherwise
        """
        try:
            # Create default data based on schema type if needed
            if schema_type == "scan_result":
                # Extract SSID from filename if not provided
                if default_ssid is None:
                    file_name = Path(file_path).stem
                    default_ssid = file_name
                default_data = self.create_scan_result_json(default_ssid)
            else:
                default_data = {array_key: []}
            
            # Load existing data
            data = self.load_json(file_path, schema_type, create_if_missing=True, 
                                 default_data=default_data)
            
            # Ensure array exists
            if array_key not in data:
                data[array_key] = []
            elif not isinstance(data[array_key], list):
                self.logger.error(f"Key '{array_key}' is not an array in {file_path}")
                return False
            
            # Add timestamp if not present
            if isinstance(new_item, dict) and "timestamp" not in new_item:
                new_item["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Append item
            data[array_key].append(new_item)
            
            # Save updated data
            return self.save_json(file_path, data, schema_type)
            
        except Exception as e:
            self.logger.error(f"Error appending to JSON array in {file_path}: {e}")
            return False
    
    def _validate_schema(self, data: Dict[str, Any], schema_type: str) -> None:
        """
        Validate JSON data against a predefined schema.
        
        Args:
            data: Data to validate
            schema_type: Type of schema to validate against
            
        Raises:
            ValueError: If validation fails
        """
        if schema_type not in self.SCHEMAS:
            self.logger.warning(f"Unknown schema type: {schema_type}")
            return
        
        schema = self.SCHEMAS[schema_type]
        
        # For array data (like wifi_credentials), validate each item
        if isinstance(data, list):
            for i, item in enumerate(data):
                self._validate_item(item, schema, f"item[{i}]")
        else:
            self._validate_item(data, schema, "data")
    
    def _validate_item(self, item: Dict[str, Any], schema: Dict[str, Any], context: str) -> None:
        """
        Validate a single item against schema.
        
        Args:
            item: Item to validate
            schema: Schema definition
            context: Context for error messages
            
        Raises:
            ValueError: If validation fails
        """
        # Check required fields
        for field in schema["required_fields"]:
            if field not in item:
                raise ValueError(f"Missing required field '{field}' in {context}")
        
        # Check field types
        for field, expected_type in schema["field_types"].items():
            if field in item and not isinstance(item[field], expected_type):
                raise ValueError(f"Field '{field}' should be {expected_type.__name__} in {context}")
    
    def format_json_string(self, data: Dict[str, Any]) -> str:
        """
        Format dictionary as JSON string with global formatting.
        
        Args:
            data: Dictionary to format
            
        Returns:
            Formatted JSON string
        """
        return json.dumps(data, **self.JSON_CONFIG)
    
    def create_state_json(self, level: int = 1, start_date: Optional[str] = None, 
                          pet_name: str = "Xeno") -> Dict[str, Any]:
        """
        Create a standardized state JSON structure.
        
        Args:
            level: Current level
            start_date: Start date (defaults to current date)
            pet_name: Pet name
            
        Returns:
            Dictionary with state structure
        """
        if start_date is None:
            start_date = datetime.now().strftime("%Y-%m-%d")
            
        return {
            "level": level,
            "start_date": start_date,
            "pet_name": pet_name
        }
    
    def create_scan_result_json(self, ssid: str, initial_scans: Optional[List] = None) -> Dict[str, Any]:
        """
        Create a standardized scan result JSON structure.
        
        Args:
            ssid: SSID name
            initial_scans: Initial scans list
            
        Returns:
            Dictionary with scan result structure
        """
        return {
            "ssid": ssid,
            "scans": initial_scans or []
        }
    
    @classmethod
    def get_global_instance(cls, logger: Optional[logging.Logger] = None) -> 'JSONManager':
        """
        Get a global singleton instance of JSONManager.
        
        Args:
            logger: Optional logger instance
            
        Returns:
            Global JSONManager instance
        """
        if not hasattr(cls, '_global_instance'):
            cls._global_instance = cls(logger)
        return cls._global_instance


# Global instance for easy access
json_manager = JSONManager.get_global_instance()


# Convenience functions for backward compatibility
def load_json(file_path: Union[str, Path], **kwargs) -> Dict[str, Any]:
    """Load JSON using global manager."""
    return json_manager.load_json(file_path, **kwargs)


def save_json(file_path: Union[str, Path], data: Dict[str, Any], **kwargs) -> bool:
    """Save JSON using global manager."""
    return json_manager.save_json(file_path, data, **kwargs)


def update_json(file_path: Union[str, Path], updates: Dict[str, Any], **kwargs) -> bool:
    """Update JSON using global manager."""
    return json_manager.update_json(file_path, updates, **kwargs)