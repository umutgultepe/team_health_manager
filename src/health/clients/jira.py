import requests
from datetime import datetime
from typing import List
from ..dataclass import JIRAIssue
from ..config.credentials import JIRA_API_TOKEN, JIRA_EMAIL, JIRA_DOMAIN

class JIRAClient:
    def __init__(self):
        """Initialize JIRA client with API credentials."""
        self.base_url = f"https://{JIRA_DOMAIN}/rest/api/3"
        self.auth = (JIRA_EMAIL, JIRA_API_TOKEN)
        self.headers = {
            "Accept": "application/json"
        }

    def _parse_issue(self, issue_data: dict) -> JIRAIssue:
        """Parse raw issue data into a JIRAIssue object."""
        if not issue_data:
            raise ValueError("Empty issue data received")
            
        fields = issue_data.get('fields', {})
        if not fields:
            raise ValueError(f"Missing fields in issue data: {issue_data}")
        
        # Parse timestamps
        created_str = fields.get('created')
        updated_str = fields.get('updated')
        if not created_str or not updated_str:
            raise ValueError(f"Missing timestamp fields in issue: {issue_data}")
            
        try:
            created = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format in issue: {issue_data}") from e
        
        # Parse components
        components = [c.get('name', '') for c in fields.get('components', [])]
        
        # Parse assignee and reporter - handle None cases
        assignee_data = fields.get('assignee')
        assignee = assignee_data.get('displayName', 'Unassigned') if assignee_data else 'Unassigned'
        
        reporter_data = fields.get('reporter')
        reporter = reporter_data.get('displayName', 'Unknown') if reporter_data else 'Unknown'
        
        return JIRAIssue(
            key=issue_data.get('key', ''),
            summary=fields.get('summary', ''),
            description=fields.get('description', ''),
            created=created,
            updated=updated,
            status=fields.get('status', {}).get('name', ''),
            components=components,
            assignee=assignee,
            reporter=reporter
        )

    def list_arns(self, components: List[str], start_time: datetime, end_time: datetime) -> List[JIRAIssue]:
        """
        List ARN project issues with specified components within a time range.
        
        Args:
            components (List[str]): List of component names to filter by
            start_time (datetime): Start of the time range
            end_time (datetime): End of the time range
            
        Returns:
            List[JIRAIssue]: List of matching JIRA issues
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        try:
            # Convert components list to JQL format
            components_jql = " OR ".join([f'component = "{c}"' for c in components])
            
            # Build JQL query
            jql = (
                f'project = ARN AND '
                f'({components_jql}) AND '
                f'created >= "{start_time.strftime("%Y-%m-%d %H:%M")}" AND '
                f'created <= "{end_time.strftime("%Y-%m-%d %H:%M")}"'
            )
            
            # Prepare request parameters
            params = {
                'jql': jql,
                'maxResults': 100,  # Maximum results per page
                'fields': 'summary,description,created,updated,status,components,assignee,reporter'
            }
            
            issues = []
            start_at = 0
            
            while True:
                # Update start_at for pagination
                params['startAt'] = start_at
                
                # Make API request
                response = requests.get(
                    f"{self.base_url}/search",
                    auth=self.auth,
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    raise ValueError("Empty response from JIRA API")
                    
                # Process issues
                for issue_data in data.get('issues', []):
                    try:
                        issues.append(self._parse_issue(issue_data))
                    except ValueError as e:
                        print(f"Warning: Skipping invalid issue: {str(e)}")
                        continue
                
                # Check if we need to fetch more pages
                total = data.get('total', 0)
                start_at += len(data.get('issues', []))
                
                if start_at >= total:
                    break
            
            return issues
            
        except requests.exceptions.RequestException as e:
            if hasattr(e.response, 'text'):
                error_detail = e.response.text
            else:
                error_detail = str(e)
            raise Exception(f"Error fetching JIRA issues: {str(e)}") 