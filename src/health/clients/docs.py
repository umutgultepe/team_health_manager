from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..config.credentials import get_google_credentials, get_operating_review_document_id
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import re

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

    def _convert_markdown_to_docs_format(self, content: str) -> list:
        """Convert markdown content to Google Docs formatting requests.
        
        Args:
            content: Markdown content to convert
            
        Returns:
            List of Google Docs formatting requests
        """
        requests = []
        lines = content.split('\n')
        current_index = 1  # Start after the initial newline
        
        for line in lines:
            # Handle horizontal line
            if line.strip() == '---' or line.strip() == '***':
                requests.extend([
                    {
                        'insertText': {
                            'location': {'index': current_index},
                            'text': '\n'
                        }
                    },
                    {
                        'insertText': {
                            'location': {'index': current_index + 1},
                            'text': ' '  # Empty paragraph for the line
                        }
                    },
                    {
                        'updateParagraphStyle': {
                            'range': {
                                'startIndex': current_index + 1,
                                'endIndex': current_index + 2
                            },
                            'paragraphStyle': {
                                'borderBottom': {
                                    'color': {
                                        'color': {
                                            'rgbColor': {
                                                'red': 0.5,
                                                'green': 0.5,
                                                'blue': 0.5
                                            }
                                        }
                                    },
                                    'width': {
                                        'magnitude': 1,
                                        'unit': 'PT'
                                    },
                                    'dashStyle': 'SOLID',
                                    'padding': {
                                        'magnitude': 6,
                                        'unit': 'PT'
                                    }
                                }
                            },
                            'fields': 'borderBottom'
                        }
                    },
                    {
                        'insertText': {
                            'location': {'index': current_index + 2},
                            'text': '\n'
                        }
                    }
                ])
                current_index += 3
                continue

            # Handle headers
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2)
                requests.extend([
                    {
                        'insertText': {
                            'location': {'index': current_index},
                            'text': text + '\n'
                        }
                    },
                    {
                        'updateParagraphStyle': {
                            'range': {
                                'startIndex': current_index,
                                'endIndex': current_index + len(text)
                            },
                            'paragraphStyle': {
                                'namedStyleType': f'HEADING_{level}'
                            },
                            'fields': 'namedStyleType'
                        }
                    }
                ])
                current_index += len(text) + 1
                continue

            # Handle links first (to avoid conflicts with bold/italic)
            line = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: f'<link url="{m.group(2)}">{m.group(1)}</link>', line)
            
            # Handle bold
            line = re.sub(r'\*\*([^*]+)\*\*', lambda m: f'<b>{m.group(1)}</b>', line)
            
            # Handle italic
            line = re.sub(r'\*([^*]+)\*', lambda m: f'<i>{m.group(1)}</i>', line)
            
            # Handle code blocks
            line = re.sub(r'`([^`]+)`', lambda m: f'<code>{m.group(1)}</code>', line)
            
            # Handle lists
            list_match = re.match(r'^[-*]\s+(.+)$', line)
            if list_match:
                text = list_match.group(1)
                requests.extend([
                    {
                        'insertText': {
                            'location': {'index': current_index},
                            'text': '• ' + text + '\n'
                        }
                    },
                    {
                        'createParagraphBullets': {
                            'range': {
                                'startIndex': current_index,
                                'endIndex': current_index + len(text) + 3
                            },
                            'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                        }
                    }
                ])
                current_index += len(text) + 3
                continue

            # Regular text
            if line.strip():
                # Process text formatting
                text = line
                formatting_requests = []
                
                # Handle bold tags
                bold_matches = re.finditer(r'<b>(.*?)</b>', text)
                for match in bold_matches:
                    start = match.start()
                    end = match.end()
                    content = match.group(1)
                    formatting_requests.append({
                        'updateTextStyle': {
                            'range': {
                                'startIndex': current_index + start,
                                'endIndex': current_index + start + len(content)
                            },
                            'textStyle': {
                                'bold': True
                            },
                            'fields': 'bold'
                        }
                    })
                    text = text[:start] + content + text[end:]
                
                # Handle link tags
                link_matches = re.finditer(r'<link url="([^"]+)">(.*?)</link>', text)
                for match in link_matches:
                    start = match.start()
                    end = match.end()
                    url = match.group(1)
                    content = match.group(2)
                    formatting_requests.append({
                        'updateTextStyle': {
                            'range': {
                                'startIndex': current_index + start,
                                'endIndex': current_index + start + len(content)
                            },
                            'textStyle': {
                                'link': {
                                    'url': url
                                }
                            },
                            'fields': 'link'
                        }
                    })
                    text = text[:start] + content + text[end:]
                
                # Insert the text
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': text + '\n'
                    }
                })
                
                # Add formatting requests
                requests.extend(formatting_requests)
                
                current_index += len(text) + 1
            else:
                requests.append({
                    'insertText': {
                        'location': {'index': current_index},
                        'text': '\n'
                    }
                })
                current_index += 1

        return requests
    
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
        
        # Convert markdown to Google Docs formatting
        formatting_requests = self._convert_markdown_to_docs_format(content)
        
        # Add tab ID to all requests
        for request in formatting_requests:
            if 'location' in request.get('insertText', {}):
                request['insertText']['location']['tabId'] = target_tab['tabProperties']['tabId']
            if 'range' in request.get('updateParagraphStyle', {}):
                request['updateParagraphStyle']['range']['tabId'] = target_tab['tabProperties']['tabId']
            if 'range' in request.get('createParagraphBullets', {}):
                request['createParagraphBullets']['range']['tabId'] = target_tab['tabProperties']['tabId']
        
        # Execute the request
        self._make_docs_request(
            lambda: self.service.documents().batchUpdate(
                documentId=self.document_id,
                body={'requests': formatting_requests}
            )
        ) 