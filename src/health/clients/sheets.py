from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..config.credentials import get_google_credentials, get_google_sheet_id
from typing import Optional

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

    def read_cell(self, sheet_name: str, cell_reference: str) -> Optional[str]:
        """Read a single cell's value from the specified sheet.
        
        Args:
            sheet_name: Name of the sheet to read from
            cell_reference: Cell reference (e.g., 'A1', 'B2')
            
        Returns:
            The cell's value as a string, or None if the cell is empty
        """
        try:
            # Convert coordinate to A1 notation with sheet name
            range_name = f"{sheet_name}!{cell_reference}"
            
            # Read the cell value
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()
            
            # Extract the value from the response
            values = result.get('values', [])
            if not values or not values[0]:
                return None
                
            return values[0][0]
            
        except Exception as e:
            print(f"Error reading cell {cell_reference} from sheet {sheet_name}: {e}")
            return None 