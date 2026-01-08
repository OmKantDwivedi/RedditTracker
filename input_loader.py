import re
from typing import List
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
from io import BytesIO, StringIO
import config

class InputLoader:
    @staticmethod
    def is_google_sheets_url(url: str) -> bool:
        """Check if URL is a Google Sheets link"""
        return 'docs.google.com/spreadsheets' in url
    
    @staticmethod
    def extract_sheet_id(url: str) -> str:
        """Extract Google Sheets ID from URL"""
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        raise ValueError(f"Invalid Google Sheets URL: {url}")
    
    @staticmethod
    def convert_to_export_url(sheets_url: str) -> str:
        """
        Convert Google Sheets sharing URL to CSV export URL
        This bypasses the need for credentials
        """
        sheet_id = InputLoader.extract_sheet_id(sheets_url)
        
        # Check for specific sheet GID
        gid_match = re.search(r'[?&#]gid=(\d+)', sheets_url)
        gid = gid_match.group(1) if gid_match else '0'
        
        # Use Google's CSV export endpoint
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        return export_url
    
    @staticmethod
    def load_from_google_sheets_with_credentials(url: str) -> pd.DataFrame:
        """Load data from Google Sheets using service account credentials"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]
            creds = Credentials.from_service_account_file(
                config.GOOGLE_CREDENTIALS_FILE, 
                scopes=scopes
            )
            client = gspread.authorize(creds)
            
            sheet_id = InputLoader.extract_sheet_id(url)
            sheet = client.open_by_key(sheet_id).sheet1
            
            data = sheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            raise Exception(f"Failed to load Google Sheets with credentials: {e}")
    
    @staticmethod
    def load_from_google_sheets_export(url: str) -> pd.DataFrame:
        """
        Load data from Google Sheets using public CSV export
        This works if the sheet is shared publicly
        """
        try:
            export_url = InputLoader.convert_to_export_url(url)
            
            # Download CSV
            response = requests.get(export_url, timeout=30)
            response.raise_for_status()
            
            # Check if we got HTML error page instead of CSV
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                raise Exception("Sheet is not publicly accessible. Please share the sheet: File → Share → Anyone with the link can view")
            
            # Parse CSV
            csv_content = response.content.decode('utf-8')
            return pd.read_csv(StringIO(csv_content))
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to download sheet: {e}")
        except Exception as e:
            raise Exception(f"Failed to load Google Sheets: {e}")
    
    @staticmethod
    def load_from_url(url: str) -> pd.DataFrame:
        """Download and load CSV/XLSX from URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            
            # Try XLSX first
            if '.xlsx' in url.lower() or 'excel' in content_type or 'spreadsheet' in content_type:
                try:
                    return pd.read_excel(BytesIO(response.content))
                except:
                    pass
            
            # Try CSV
            try:
                return pd.read_csv(BytesIO(response.content))
            except:
                # Try with different encoding
                return pd.read_csv(BytesIO(response.content), encoding='latin-1')
                
        except Exception as e:
            raise Exception(f"Failed to download file from URL: {e}")
    
    @staticmethod
    def load_from_file(filepath: str) -> pd.DataFrame:
        """Load from local file"""
        if filepath.endswith('.xlsx') or filepath.endswith('.xls'):
            return pd.read_excel(filepath)
        elif filepath.endswith('.csv'):
            return pd.read_csv(filepath)
        else:
            raise ValueError(f"Unsupported file format: {filepath}")
    
    @staticmethod
    def load(input_source: str) -> List[str]:
        """
        Load comment URLs from input source
        Returns list of valid comment URLs
        """
        df = None
        
        # Determine input type and load
        if InputLoader.is_google_sheets_url(input_source):
            print("📊 Detected Google Sheets URL")
            
            # Try public export first (doesn't require credentials)
            try:
                print("Attempting to load via public CSV export...")
                df = InputLoader.load_from_google_sheets_export(input_source)
                print("✓ Loaded via CSV export")
            except Exception as e1:
                print(f"CSV export failed: {e1}")
                
                # Try with credentials if available
                try:
                    import os
                    if os.path.exists(config.GOOGLE_CREDENTIALS_FILE):
                        print("Attempting to load with credentials...")
                        df = InputLoader.load_from_google_sheets_with_credentials(input_source)
                        print("✓ Loaded with credentials")
                    else:
                        raise Exception(
                            "Google Sheets is not publicly accessible and no credentials found. "
                            "Please either:\n"
                            "1. Share the sheet publicly (File → Share → Anyone with the link can view), or\n"
                            "2. Add credentials.json file for authentication"
                        )
                except Exception as e2:
                    raise Exception(
                        f"Failed to load Google Sheets:\n"
                        f"- Public export: {e1}\n"
                        f"- With credentials: {e2}\n\n"
                        f"Please ensure the sheet is shared: File → Share → Anyone with the link can view"
                    )
        
        elif input_source.startswith('http'):
            print("🔗 Detected download URL")
            df = InputLoader.load_from_url(input_source)
        
        else:
            print("📁 Loading from local file")
            df = InputLoader.load_from_file(input_source)
        
        # Validate required column
        if df is None:
            raise ValueError("Failed to load spreadsheet")
        
        print(f"Loaded spreadsheet with {len(df)} rows")
        print(f"Columns found: {df.columns.tolist()}")
        
        if 'comment_url' not in df.columns:
            available_columns = ', '.join(df.columns.tolist())
            raise ValueError(
                f"Spreadsheet must contain 'comment_url' column.\n"
                f"Found columns: {available_columns}\n"
                f"Please rename your column to exactly 'comment_url' (all lowercase, with underscore)"
            )
        
        # Extract and clean URLs
        urls = df['comment_url'].dropna().astype(str).tolist()
        print(f"Found {len(urls)} non-empty values in comment_url column")
        
        # Filter valid Reddit comment URLs
        valid_urls = []
        invalid_urls = []
        for url in urls:
            url = url.strip()
            if not url or url.lower() == 'nan':
                continue
            if 'reddit.com' in url and '/comments/' in url:
                valid_urls.append(url)
            else:
                invalid_urls.append(url)
        
        if invalid_urls:
            print(f"⚠️ Skipped {len(invalid_urls)} invalid URLs:")
            for inv_url in invalid_urls[:5]:  # Show first 5
                print(f"  - {inv_url}")
        
        if not valid_urls:
            raise ValueError(
                f"No valid Reddit comment URLs found.\n"
                f"Total rows: {len(urls)}\n"
                f"Invalid URLs: {len(invalid_urls)}\n"
                f"URLs must contain 'reddit.com' and '/comments/'"
            )
        
        print(f"✓ Found {len(valid_urls)} valid comment URLs")
        return valid_urls