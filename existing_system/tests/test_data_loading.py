# tests/test_data_loading.py

import unittest
import pandas as pd
from src.data_loader import load_and_preprocess_data, load_all_leagues

class TestDataLoading(unittest.TestCase):
    
    def test_load_single_league(self):
        """Test loading a single league dataset."""
        df = load_and_preprocess_data('../data/SpanishLaliga.csv')
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn('Home Team', df.columns)
        self.assertIn('Away Team', df.columns)
    
    def test_load_multiple_leagues(self):
        """Test loading multiple leagues from the data directory."""
        combined_df = load_all_leagues('../data/')
        self.assertIsInstance(combined_df, pd.DataFrame)
        self.assertIn('League', combined_df.columns)
    
    def test_missing_file(self):
        """Test handling of missing files."""
        with self.assertRaises(FileNotFoundError):
            load_and_preprocess_data('../data/MissingLeague.csv')
            
if __name__ == '__main__':
    unittest.main()
