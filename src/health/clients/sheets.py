from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..config.credentials import get_google_credentials
from typing import Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class SheetsClient:
    """Client for interacting with Google Sheets."""
    
    def __init__(self, sheet_id: str):
        """Initialize the Sheets client with credentials."""
        self.credentials = get_google_credentials()
        self.sheet_id = sheet_id
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
            # Try to parse as float first
            try:
                num_value = float(text)
                # If it's an integer, write as integer
                if num_value.is_integer():
                    value = int(num_value)
                else:
                    value = num_value
            except (ValueError, TypeError):
                # If not a number, keep as string
                value = text
                
            # Convert coordinate to A1 notation with sheet name
            range_name = f"{tab_name}!{coordinate}"
            
            # Prepare the value range
            values = [[value]]
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

    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=5, min=4, max=60),
        retry=retry_if_exception_type(HttpError)
    )
    def _make_sheets_request(self, request_func):
        """Make a request to Google Sheets API with retry logic.
        
        Args:
            request_func: Function that makes the API request
            
        Returns:
            The API response
            
        Raises:
            HttpError: If the request fails after all retry attempts
        """
        try:
            return request_func().execute()
        except HttpError as error:
            if error.resp.status == 429:
                raise  # Retry on 429 errors
            raise Exception(f"An error occurred while accessing Google Sheets: {error}")

    def read_cell(self, sheet_name: str, cell_reference: str) -> Optional[str]:
        """Read a single cell's value from the specified sheet.
        
        Args:
            sheet_name: Name of the sheet to read from
            cell_reference: Cell reference (e.g., 'A1', 'B2')
            
        Returns:
            The cell's value as a string, or None if the cell is empty
        """
        # Convert coordinate to A1 notation with sheet name
        range_name = f"{sheet_name}!{cell_reference}"
        
        # Read the cell value with retry logic
        result = self._make_sheets_request(
            lambda: self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            )
        )
        
        # Extract the value from the response
        values = result.get('values', [])
        if not values or not values[0]:
            return None
            
        return values[0][0]

    def read_vertical_range(self, range_name: str) -> List[str]:
        """Read a vertical range of cells from the specified sheet.
        
        Args:
            range_name: Range in A1 notation (e.g., 'Sheet1!A3:A102')
            
        Returns:
            List of cell values from the range
        """
        # Read the range with retry logic
        result = self._make_sheets_request(
            lambda: self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            )
        )
        
        # Extract values from the response
        values = result.get('values', [])
        if not values:
            return []
            
        # Flatten the list since we're reading a vertical range
        column = []
        for value in values:
            if value:
                column.append(str(value[0]))
            else:
                column.append("")
        return column