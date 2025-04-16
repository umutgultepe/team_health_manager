from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..config.credentials import get_google_credentials, get_google_sheet_id

class SheetsClient:
    """Client for interacting with Google Sheets."""
    
    def __init__(self):
        """Initialize the Sheets client with credentials."""
        self.credentials = get_google_credentials()
        self.sheet_id = get_google_sheet_id()
        self.service = build('sheets', 'v4', credentials=self.credentials)
        
    def write_to_cell(self, tab_name: str, coordinate: str, text: str) -> None:
        """Write text to a specific cell in a Google Sheet.
        
        Args:
            tab_name: Name of the sheet tab
            coordinate: Cell coordinate (e.g., 'A1', 'B2')
            text: Text to write to the cell
            
        Raises:
            HttpError: If there's an error writing to the sheet
        """
        try:
            # Convert coordinate to A1 notation with sheet name
            range_name = f"{tab_name}!{coordinate}"
            
            # Prepare the value range
            values = [[text]]
            body = {
                'values': values
            }
            
            # Write to the sheet
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return result
            
        except HttpError as error:
            raise Exception(f"An error occurred while writing to Google Sheets: {error}") 