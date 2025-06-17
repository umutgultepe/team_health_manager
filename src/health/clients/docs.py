from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..config.credentials import get_google_credentials, get_operating_review_document_id
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class DocsClient:
    """Client for interacting with Google Docs."""
    
    def __init__(self):
        """Initialize the Docs client with credentials."""
        self.credentials = get_google_credentials()
        self.service = build('docs', 'v1', credentials=self.credentials)
        self.drive_service = build('drive', 'v3', credentials=self.credentials)
        self.document_id = get_operating_review_document_id()
        
    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=5, min=4, max=60),
        retry=retry_if_exception_type(HttpError)
    )
    def _make_docs_request(self, request_func):
        """Make a request to Google Docs API with retry logic.
        
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
            raise Exception(f"An error occurred while accessing Google Docs: {error}")
    
    def write_markdown(self, tab_name: str, content: str) -> None:
        """Write markdown content to a specific tab in the operating review document.
        
        Args:
            tab_name: Name of the tab to write to
            content: Markdown content to write
            
        Raises:
            HttpError: If there's an error writing to Docs
            Exception: If the tab is not found
        """
        # Get the document with all tabs content
        document = self._make_docs_request(
            lambda: self.service.documents().get(
                documentId=self.document_id,
                includeTabsContent=True
            )
        )
        
        # Find the tab by name
        target_tab = None
        found_tabs = []
        
        def find_tab(tabs):
            for tab in tabs:
                tab_properties = tab.get('tabProperties', {})
                tab_title = tab_properties.get('title', '')
                found_tabs.append(tab_title)
                
                if tab_title == tab_name:
                    return tab
                
                # Check child tabs recursively
                child_tabs = tab.get('childTabs', [])
                if child_tabs:
                    result = find_tab(child_tabs)
                    if result:
                        return result
            return None
        
        target_tab = find_tab(document.get('tabs', []))
        
        if target_tab is None:
            raise Exception(f"Tab '{tab_name}' not found in the document. Available tabs: {', '.join(found_tabs)}")
        
        # Get the document tab content
        document_tab = target_tab.get('documentTab', {})
        body = document_tab.get('body', {})
        
        # Create the request to insert content
        requests = [{
            'insertText': {
                'location': {
                    'tabId': target_tab['tabProperties']['tabId'],
                    'index': body.get('endIndex', 1)
                },
                'text': f"\n{content}\n"
            }
        }]
        
        # Execute the request
        self._make_docs_request(
            lambda: self.service.documents().batchUpdate(
                documentId=self.document_id,
                body={'requests': requests}
            )
        ) 