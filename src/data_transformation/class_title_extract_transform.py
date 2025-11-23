"""
Extract unique class_title values from all 13F-HR Excel files.

This script scans all folders in data/extracted_13F_HR/, finds all .xlsx files,
extracts the 'class_title' column from each, and saves unique values to a CSV file.
"""

import pandas as pd
from pathlib import Path
from typing import List


class ClassTitleExtractor:
    """
    Extractor class for extracting unique class_title values from 13F-HR Excel files.
    """
    
    def __init__(self):
        """Initialize the ClassTitleExtractor with default paths."""
        self.base_dir = Path(__file__).parent.parent.parent
        self.extracted_data_dir = self.base_dir / "data" / "extracted_13F_HR"
        self.output_dir = self.base_dir / "data" / "metadata"
        self.output_file = self.output_dir / "unique_class_title.csv"
        self.all_class_titles = []
    
    def _get_xlsx_files(self, folder: Path) -> List[Path]:
        """
        Get all valid Excel files from a folder.
        
        Args:
            folder: Path to the folder to scan
            
        Returns:
            List of Path objects for valid Excel files
        """
        xlsx_files = list(folder.glob("*.xlsx"))
        # Filter out temporary files (starting with ~$)
        return [f for f in xlsx_files if not f.name.startswith("~$")]
    
    def _extract_from_file(self, xlsx_file: Path) -> int:
        """
        Extract class_title values from a single Excel file.
        
        Args:
            xlsx_file: Path to the Excel file
            
        Returns:
            Number of class_title values extracted
        """
        try:
            print(f"    Reading: {xlsx_file.name}")
            
            # Read the Excel file
            df = pd.read_excel(xlsx_file)
            
            # Check if 'class_title' column exists
            if 'class_title' in df.columns:
                # Extract class_title values (drop NaN values)
                class_titles = df['class_title'].dropna().tolist()
                self.all_class_titles.extend(class_titles)
                print(f"      Extracted {len(class_titles)} class_title values")
                return len(class_titles)
            else:
                print(f"      Warning: 'class_title' column not found in {xlsx_file.name}")
                print(f"      Available columns: {', '.join(df.columns)}")
                return 0
                
        except Exception as e:
            print(f"      Error reading {xlsx_file.name}: {str(e)}")
            return 0
    
    def extract(self) -> pd.DataFrame:
        """
        Extract unique class_title values from all Excel files in extracted_13F_HR folders.
        
        Returns:
            pd.DataFrame: DataFrame containing unique class_title values
        """
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Reset class_titles list
        self.all_class_titles = []
        
        print(f"Scanning directory: {self.extracted_data_dir}")
        
        # Iterate through all subdirectories in extracted_13F_HR
        for folder in self.extracted_data_dir.iterdir():
            if folder.is_dir():
                print(f"\nProcessing folder: {folder.name}")
                
                # Find all .xlsx files in the folder
                xlsx_files = self._get_xlsx_files(folder)
                print(f"  Found {len(xlsx_files)} Excel files")
                
                # Process each Excel file
                for xlsx_file in xlsx_files:
                    self._extract_from_file(xlsx_file)
        
        # Get unique class_title values
        unique_class_titles = sorted(set(self.all_class_titles))
        
        print(f"\n{'='*60}")
        print(f"Total class_title values found: {len(self.all_class_titles)}")
        print(f"Unique class_title values: {len(unique_class_titles)}")
        print(f"{'='*60}")
        
        # Create DataFrame with unique values
        result_df = pd.DataFrame({
            'class_title': unique_class_titles
        })
        
        # Save to CSV
        result_df.to_csv(self.output_file, index=False)
        print(f"\nSaved unique class_title values to: {self.output_file}")
        
        # Display first few unique values
        print(f"\nFirst 10 unique class_title values:")
        for i, title in enumerate(unique_class_titles[:10], 1):
            print(f"  {i}. {title}")
        
        return result_df


if __name__ == "__main__":
    extractor = ClassTitleExtractor()
    extractor.extract()
