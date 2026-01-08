from typing import List, Dict
import pandas as pd
from datetime import datetime
import config

class OutputWriter:
    @staticmethod
    def generate_output_filename() -> str:
        """Generate timestamped output filename"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f'reddit_tracker_output_{timestamp}.xlsx'
    
    @staticmethod
    def create_output_spreadsheet(results: List[Dict], output_path: str = None) -> str:
        """
        Create output spreadsheet with results
        Returns: path to created file
        """
        if not output_path:
            output_path = OutputWriter.generate_output_filename()
        
        # Ensure correct column order
        df = pd.DataFrame(results)
        df = df[config.OUTPUT_COLUMNS]
        
        # Write to Excel
        df.to_excel(output_path, index=False, engine='openpyxl')
        
        return output_path
    
    @staticmethod
    def create_csv_output(results: List[Dict], output_path: str = None) -> str:
        """
        Create output CSV with results
        Returns: path to created file
        """
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f'reddit_tracker_output_{timestamp}.csv'
        
        # Ensure correct column order
        df = pd.DataFrame(results)
        df = df[config.OUTPUT_COLUMNS]
        
        # Write to CSV
        df.to_csv(output_path, index=False)
        
        return output_path