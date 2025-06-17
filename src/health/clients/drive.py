from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
from ..config.credentials import get_google_credentials
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import io

class DriveClient:
    """Client for interacting with Google Drive."""
    
    def __init__(self):
        """Initialize the Drive client with credentials."""
        self.credentials = get_google_credentials()
        self.service = build('drive', 'v3', credentials=self.credentials)
        
    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=5, min=4, max=60),
        retry=retry_if_exception_type(HttpError)
    )
    def _make_drive_request(self, request_func):
        """Make a request to Google Drive API with retry logic.
        
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
            raise Exception(f"An error occurred while accessing Google Drive: {error}")

    def write(self, file_path: str, content: str) -> None:
        """Write content to a file in Google Drive.
        
        Args:
            file_path: Path of the file in Google Drive (e.g., 'folder/subfolder/file.txt')
            content: Content to write to the file
            
        Raises:
            HttpError: If there's an error writing to Drive
        """
        # Split the path into parts
        path_parts = file_path.split('/')
        file_name = path_parts[-1]
        parent_folders = path_parts[:-1]
        
        # Start from root folder
        current_parent_id = 'root'
        
        # Navigate through the folder structure
        for folder_name in parent_folders:
            # Search for the folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{current_parent_id}' in parents and trashed=false"
            results = self._make_drive_request(
                lambda: self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name)'
                )
            )
            
            files = results.get('files', [])
            if not files:
                # Create the folder if it doesn't exist
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [current_parent_id]
                }
                folder = self._make_drive_request(
                    lambda: self.service.files().create(
                        body=folder_metadata,
                        fields='id'
                    )
                )
                current_parent_id = folder.get('id')
            else:
                current_parent_id = files[0]['id']
        
        # Check if file exists
        query = f"name='{file_name}' and '{current_parent_id}' in parents and trashed=false"
        results = self._make_drive_request(
            lambda: self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            )
        )
        
        # Create a file-like object from the content
        content_bytes = content.encode('utf-8')
        fh = io.BytesIO(content_bytes)
        media = MediaIoBaseUpload(fh, mimetype='text/plain', resumable=True)
        
        files = results.get('files', [])
        if files:
            # Update existing file
            file_id = files[0]['id']
            self._make_drive_request(
                lambda: self.service.files().update(
                    fileId=file_id,
                    media_body=media
                )
            )
        else:
            # Create new file
            file_metadata = {
                'name': file_name,
                'parents': [current_parent_id]
            }
            self._make_drive_request(
                lambda: self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                )
            )

    def read(self, file_path: str) -> Optional[str]:
        """Read content from a file in Google Drive.
        
        Args:
            file_path: Path of the file in Google Drive (e.g., 'folder/subfolder/file.txt')
            
        Returns:
            The file's content as a string, or None if the file doesn't exist
            
        Raises:
            HttpError: If there's an error reading from Drive
        """
        # Split the path into parts
        path_parts = file_path.split('/')
        file_name = path_parts[-1]
        parent_folders = path_parts[:-1]
        
        # Start from root folder
        current_parent_id = 'root'
        
        # Navigate through the folder structure
        for folder_name in parent_folders:
            # Search for the folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{current_parent_id}' in parents and trashed=false"
            results = self._make_drive_request(
                lambda: self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name)'
                )
            )
            
            files = results.get('files', [])
            if not files:
                return None
                
            current_parent_id = files[0]['id']
        
        # Search for the file
        query = f"name='{file_name}' and '{current_parent_id}' in parents and trashed=false"
        results = self._make_drive_request(
            lambda: self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            )
        )
        
        files = results.get('files', [])
        if not files:
            return None
            
        # Download the file content
        file_id = files[0]['id']
        request = self.service.files().get_media(fileId=file_id)
        file_content = self._make_drive_request(lambda: request)
        
        return file_content.decode('utf-8') 