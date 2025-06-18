from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..config.credentials import get_google_credentials, get_operating_review_document_id
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import re
from markgdoc import markgdoc
from typing import List, Dict

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


    def _write_markdown_to_tab(self, content_markdown: str, tab_id: str) -> None:
        """Write markdown content to a specific tab in the operating review document using markgdoc package."""
        # First preprocess numbered lists, then split the content into chunks every new line detected. 
        content_markdown = markgdoc.preprocess_numbered_lists(content_markdown)
        chunks = re.split(r"(?<=\n)", content_markdown)

        # Initializing variables, index = 1
        chunks = iter(chunks)
        index = 1
        text_requests = []
        style_requests = []

        # For each chunk detected: 
        for chunk in chunks:
            # Initialize a chunk by stripping it and splitting into requests per chunk
            chunk = chunk.strip()
            requests = []
            table_flag = False
            paragraph_flag = markgdoc.is_paragraph(chunk)

            # Then we preprocess any styles recognized in the chunks and store them into the style_requests
            received_styling, cleaned_chunk = markgdoc.preprocess_nested_styles(chunk, index, paragraph_flag, debug=False)
            style_requests.extend(received_styling)

            # Matches detected 
            header_match = re.match(r"^(#{1,6})\s+(.+)", cleaned_chunk)
            bullet_point_match = re.match(r"^-\s+(.+)", cleaned_chunk)
            numbered_list_match = re.match(r"^\d+\.\s+(.+)", cleaned_chunk)
            horizontal_line_match = re.match(r"^[-*_]{3,}$", cleaned_chunk)
            
            # If the chunk has header markdown syntax add the request
            if header_match:
                header_level = len(re.match(r"^#+", cleaned_chunk).group(0))
                text = cleaned_chunk[header_level:].strip()
                requests.extend(markgdoc.get_header_request(text, header_level, index, debug=False))
            
            # If the chunk has unordered list markdown syntax add the request
            elif bullet_point_match:
                text = cleaned_chunk[2:].strip()
                requests.extend(markgdoc.get_unordered_list_request(text, index, debug=False))

            # If the chunk has ordered list markdown syntax add the request
            elif numbered_list_match:
                text = re.sub(r"^\d+\.\s", "", cleaned_chunk).strip()
                requests.extend(markgdoc.get_ordered_list_request(text, index, debug=False))
            
            # If the chunk has horizontal line markdown syntax add the request
            elif horizontal_line_match:
                requests.extend(markgdoc.get_horizontal_line_request(index, debug=False))

            # If the chunk has none of those, then it is likely a paragraph
            else:
                requests.append(markgdoc.get_paragraph_request(cleaned_chunk, index, debug=False))
            
            #  Append the general requets into the all requests and then appropriately increment the index based on the request text
            for request in requests:
                text_requests.append(request)
                # Table automatically updates index due to monitoring hence, no need to update index if it's a table
                if "insertText" in request and not table_flag:
                    index += len(request["insertText"]["text"])

        # Add tab ID to all requests
        # Flatten style_requests if it's a list of lists
        if style_requests and isinstance(style_requests[0], list):
            style_requests = [item for sublist in style_requests for item in sublist]

        for request in text_requests + style_requests:
            if 'location' in request.get('insertText', {}):
                request['insertText']['location']['tabId'] = tab_id
            if 'range' in request.get('updateParagraphStyle', {}):
                request['updateParagraphStyle']['range']['tabId'] = tab_id
            if 'range' in request.get('createParagraphBullets', {}):
                request['createParagraphBullets']['range']['tabId'] = tab_id
            if 'range' in request.get('updateTextStyle', {}):
                request['updateTextStyle']['range']['tabId'] = tab_id

        # Send batch updates to insert the text into the google doc
        markgdoc.send_batch_update(self.service, self.document_id, text_requests)
        
        # After inserting the text, send a separate batch update for style requests
        markgdoc.send_batch_update(self.service, self.document_id, style_requests)

    def write_markdown(self, tab_name: str, content: str) -> None:
        """Write markdown content to a specific tab in the operating review document using markgdoc package."""
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
        
        # We need to specify the starting index for insertion
        self._write_markdown_to_tab(content, target_tab['tabProperties']['tabId'])