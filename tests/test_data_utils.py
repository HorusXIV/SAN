"""Unit tests for data utilities."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import json
import tempfile

from src.common.data_utils import (
    fix_unicode_escapes,
    load_json_fixed,
    extract_positions,
    extract_positions_vectorized,
    extract_start_positions_vectorized,
    extract_start_position
)


class TestFixUnicodeEscapes:
    """Tests for fix_unicode_escapes function."""
    
    def test_string_with_unicode(self):
        """Test fixing unicode escapes in string."""
        input_str = r"M\u00fcller"
        result = fix_unicode_escapes(input_str)
        assert "ü" in result
    
    def test_string_without_unicode(self):
        """Test string without unicode escapes."""
        input_str = "Mueller"
        result = fix_unicode_escapes(input_str)
        assert result == "Mueller"
    
    def test_list_with_unicode(self):
        """Test fixing unicode in list."""
        input_list = [r"M\u00fcller", "Smith"]
        result = fix_unicode_escapes(input_list)
        assert "ü" in result[0]
        assert result[1] == "Smith"
    
    def test_dict_with_unicode(self):
        """Test fixing unicode in dictionary."""
        input_dict = {"name": r"M\u00fcller", "team": "Bayern"}
        result = fix_unicode_escapes(input_dict)
        assert "ü" in result["name"]
        assert result["team"] == "Bayern"
    
    def test_nested_structure(self):
        """Test fixing unicode in nested structure."""
        input_data = {
            "players": [
                {"name": r"M\u00fcller"},
                {"name": "Smith"}
            ]
        }
        result = fix_unicode_escapes(input_data)
        assert "ü" in result["players"][0]["name"]


class TestLoadJsonFixed:
    """Tests for load_json_fixed function."""
    
    def test_load_valid_json(self):
        """Test loading valid JSON file."""
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({"test": "data"}, f)
            temp_path = f.name
        
        try:
            result = load_json_fixed(temp_path)
            assert result == {"test": "data"}
        finally:
            Path(temp_path).unlink()
    
    def test_load_json_with_unicode(self):
        """Test loading JSON with unicode escapes."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({"name": r"M\u00fcller"}, f)
            temp_path = f.name
        
        try:
            result = load_json_fixed(temp_path)
            assert "ü" in result.get("name", "")
        finally:
            Path(temp_path).unlink()


class TestExtractPositions:
    """Tests for position extraction functions."""
    
    def test_extract_positions_single_row(self):
        """Test extract_positions for single row."""
        row = pd.Series({
            'positions': [
                {'x': 10.0, 'y': 20.0},
                {'x': 30.0, 'y': 40.0}
            ]
        })
        
        result = extract_positions(row)
        
        assert result['start_x'] == 10.0
        assert result['start_y'] == 20.0
        assert result['end_x'] == 30.0
        assert result['end_y'] == 40.0
    
    def test_extract_positions_missing_data(self):
        """Test extract_positions with missing data."""
        row = pd.Series({'positions': []})
        result = extract_positions(row)
        
        assert pd.isna(result['start_x'])
        assert pd.isna(result['start_y'])
        assert pd.isna(result['end_x'])
        assert pd.isna(result['end_y'])
    
    def test_extract_positions_vectorized(self):
        """Test vectorized position extraction."""
        df = pd.DataFrame({
            'positions': [
                [{'x': 10.0, 'y': 20.0}, {'x': 30.0, 'y': 40.0}],
                [{'x': 15.0, 'y': 25.0}, {'x': 35.0, 'y': 45.0}],
            ]
        })
        
        result = extract_positions_vectorized(df)
        
        assert result.loc[0, 'start_x'] == 10.0
        assert result.loc[1, 'start_x'] == 15.0
        assert result.loc[0, 'end_y'] == 40.0
        assert result.loc[1, 'end_y'] == 45.0
    
    def test_extract_start_positions_vectorized(self):
        """Test extracting only start positions."""
        df = pd.DataFrame({
            'positions': [
                [{'x': 10.0, 'y': 20.0}],
                [{'x': 15.0, 'y': 25.0}],
            ]
        })
        
        result = extract_start_positions_vectorized(df)
        
        assert result.loc[0, 'start_x'] == 10.0
        assert result.loc[1, 'start_x'] == 15.0
        assert 'end_x' not in result.columns
    
    def test_extract_start_position(self):
        """Test extract_start_position helper."""
        positions = [{'x': 10.0, 'y': 20.0}]
        x, y = extract_start_position(positions)
        
        assert x == 10.0
        assert y == 20.0
    
    def test_extract_start_position_empty(self):
        """Test extract_start_position with empty list."""
        x, y = extract_start_position([])
        
        assert x is None
        assert y is None


class TestDataProcessing:
    """Integration tests for data processing pipeline."""
    
    def test_full_pipeline(self):
        """Test complete data processing pipeline."""
        # Create sample data
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            data = [
                {
                    'eventId': 8,
                    'playerId': 123,
                    'positions': [
                        {'x': 10.0, 'y': 20.0},
                        {'x': 30.0, 'y': 40.0}
                    ]
                }
            ]
            json.dump(data, f)
            temp_path = f.name
        
        try:
            # Load
            events = load_json_fixed(temp_path)
            
            # Convert to DataFrame
            df = pd.DataFrame(events)
            
            # Extract positions
            positions = extract_positions_vectorized(df)
            
            # Verify
            assert positions.loc[0, 'start_x'] == 10.0
            assert positions.loc[0, 'end_x'] == 30.0
            
        finally:
            Path(temp_path).unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
