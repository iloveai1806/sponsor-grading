import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pandas as pd
from typing import List, Dict, Any, Optional
import logging
from config import config

logger = logging.getLogger(__name__)

class SheetsHandler:
    """Handler for Google Sheets operations using OAuth2 credentials"""
    
    SHEET_TYPES = {
        'media': {
            'columns': [
                'Timestamp', 'Company Name', 'Website URL', 'Company Description', 
                'Industry / Category', 'Funding Status', 'Amount Raised to Date',
                'What channels are you interested in sponsoring?', 'Desired Start Date',
                'Contact Name', 'Email', 'Telegram Handle', 
                'How did you hear about Token Metrics?', 'Research Notes', 'Decision'
            ]
        },
        'blog': {
            'columns': [
                'Timestamp', 'Company Name', 'Website URL',
                'What kind of collaboration are you interested in?',
                'Example of a blog you\'d like to feature on Token Metrics',
                'Example of a backlink you\'d like to promote',
                'Is the project you\'re promoting through our blogs and backlinks VC-backed?',
                'Telegram Handle', 'How did you hear about Token Metrics Blogs?',
                'Research Notes', 'Decision'
            ]
        }
    }
    
    def __init__(self, sheet_type='media'):
        self.sheet_type = sheet_type
        self.gc = None
        self.worksheet = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Google Sheets using OAuth2"""
        try:
            # Create credentials from refresh token
            creds = Credentials(
                token=None,
                refresh_token=config.GOOGLE_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=config.GOOGLE_CLIENT_ID,
                client_secret=config.GOOGLE_CLIENT_SECRET
            )
            
            # Refresh the token
            creds.refresh(Request())
            
            # Authorize gspread
            self.gc = gspread.authorize(creds)
            
            # Open the worksheet based on sheet type
            if self.sheet_type == 'media':
                sheet_id = config.MEDIA_SHEET_ID
            elif self.sheet_type == 'blog':
                sheet_id = config.BLOG_SHEET_ID
            else:
                raise ValueError(f"Unknown sheet type: {self.sheet_type}")
                
            if sheet_id:
                self.worksheet = self.gc.open_by_key(sheet_id).sheet1
            else:
                raise ValueError(f"No {self.sheet_type} sheet ID found")
                
            logger.info(f"Successfully connected to {self.sheet_type} Google Sheet")
            
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            raise
    
    def get_all_records(self) -> List[Dict[str, Any]]:
        """Get all records from the sheet as a list of dictionaries"""
        try:
            records = self.worksheet.get_all_records()
            
            # Filter out records with empty Timestamp or Project Name
            valid_records = []
            for record in records:
                timestamp = str(record.get('Timestamp', '')).strip()
                project_name = str(record.get('Company Name', '') or record.get('Company Name ', '')).strip()
                
                if timestamp and project_name:
                    valid_records.append(record)
            
            logger.info(f"Retrieved {len(valid_records)} valid records from {len(records)} total records")
            return valid_records
        except Exception as e:
            logger.error(f"Error getting records: {e}")
            raise
    
    def get_unprocessed_records(self) -> List[Dict[str, Any]]:
        """Get records that haven't been processed yet (empty Research Notes and Decision)"""
        try:
            all_records = self.get_all_records()
            unprocessed = []
            
            for i, record in enumerate(all_records):
                research_notes = record.get('Research Notes', '').strip()
                decision = record.get('Decision', '').strip()
                
                # Record is unprocessed if both Research Notes and Decision are empty
                if research_notes == '' and decision == '':
                    record['_row_index'] = i + 2  # +2 because sheets are 1-indexed and have header
                    unprocessed.append(record)
            
            logger.info(f"Found {len(unprocessed)} unprocessed records")
            return unprocessed
            
        except Exception as e:
            logger.error(f"Error getting unprocessed records: {e}")
            raise
    
    def update_record(self, row_index: int, updates: Dict[str, Any]) -> bool:
        """Update specific fields in a record"""
        try:
            # Get all headers to find column positions
            headers = self.worksheet.row_values(1)
            
            for field, value in updates.items():
                if field in headers:
                    col_index = headers.index(field) + 1  # +1 for 1-indexed columns
                    self.worksheet.update_cell(row_index, col_index, str(value))
                else:
                    logger.warning(f"Field '{field}' not found in sheet headers")
            
            logger.info(f"Updated row {row_index} with {len(updates)} fields")
            return True
            
        except Exception as e:
            logger.error(f"Error updating record at row {row_index}: {e}")
            return False
    
    def add_columns_if_missing(self, required_columns: List[str]) -> bool:
        """Add columns to the sheet if they don't exist"""
        try:
            headers = self.worksheet.row_values(1)
            
            for column in required_columns:
                if column not in headers:
                    # Add column to the end
                    col_index = len(headers) + 1
                    self.worksheet.update_cell(1, col_index, column)
                    headers.append(column)
                    logger.info(f"Added column '{column}' to sheet")
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding columns: {e}")
            return False
    
    def get_record_by_row(self, row_index: int) -> Optional[Dict[str, Any]]:
        """Get a specific record by row index"""
        try:
            headers = self.worksheet.row_values(1)
            values = self.worksheet.row_values(row_index)
            
            # Pad values with empty strings if needed
            while len(values) < len(headers):
                values.append('')
            
            record = dict(zip(headers, values))
            record['_row_index'] = row_index
            
            return record
            
        except Exception as e:
            logger.error(f"Error getting record at row {row_index}: {e}")
            return None
    
    def setup_required_columns(self):
        """Ensure all required columns exist in the sheet"""
        required_columns = ['Research Notes', 'Decision']
        success = self.add_columns_if_missing(required_columns)
        if success:
            logger.info(f"All required columns are present in the {self.sheet_type} sheet")
        return success
    
    def get_dataframe(self) -> pd.DataFrame:
        """Get all data as a pandas DataFrame"""
        try:
            records = self.get_all_records()
            df = pd.DataFrame(records)
            logger.info(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
            return df
        except Exception as e:
            logger.error(f"Error creating DataFrame: {e}")
            raise

# Example usage functions
def test_sheets_connection(sheet_type='media'):
    """Test the sheets connection and basic operations"""
    try:
        config.validate_config()
        handler = SheetsHandler(sheet_type=sheet_type)
        
        # Setup required columns
        handler.setup_required_columns()
        
        # Get unprocessed records
        unprocessed = handler.get_unprocessed_records()
        print(f"Found {len(unprocessed)} unprocessed records in {sheet_type} sheet")
        
        # Show first few records
        for i, record in enumerate(unprocessed[:3]):
            print(f"Record {i+1}: {record.get('Company Name', 'No Name')}")
        
        return True
        
    except Exception as e:
        print(f"Error testing {sheet_type} sheets connection: {e}")
        return False

def test_both_sheets():
    """Test both media and blog sheets"""
    print("Testing Media Sheet:")
    media_success = test_sheets_connection('media')
    
    print("\nTesting Blog Sheet:")
    blog_success = test_sheets_connection('blog')
    
    return media_success and blog_success

if __name__ == "__main__":
    test_both_sheets() 