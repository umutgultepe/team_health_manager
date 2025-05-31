import requests
from datetime import datetime, date, timezone
from typing import List, Union, Optional
from jira import JIRA
from ..dataclass import ARN, ARNStats, Epic, Story, EpicUpdate, EpicUpdateStatus
from ..config.credentials import JIRA_API_TOKEN, JIRA_EMAIL, JIRA_DOMAIN

class JIRAClient:
    def __init__(self):
        """Initialize JIRA client with API credentials."""
        self.server_url = f"https://{JIRA_DOMAIN}/rest/api/3"
        self.auth = (JIRA_EMAIL, JIRA_API_TOKEN)
        self.headers = {
            "Accept": "application/json"
        }
        self.jira = JIRA(
            server=f"https://{JIRA_DOMAIN}/",
            basic_auth=self.auth
        )

    def _parse_issue(self, issue_data: dict) -> ARN:
        """Parse raw issue data into an ARN object."""
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
        
        # Parse dates
        due_date = self._parse_due_date(fields.get('duedate'))
        start_date = self._parse_start_date(fields.get('customfield_10014'))
        
        return ARN(
            project_key=issue_data.get('key', '').split('-')[0],
            key=issue_data.get('key', ''),
            summary=fields.get('summary', ''),
            description=fields.get('description', ''),
            status=fields.get('status', {}).get('name', ''),
            due_date=due_date,
            start_date=start_date,
            created=created,
            updated=updated,
            components=components,
            assignee=assignee,
            reporter=reporter
        )

    def get_epics_by_label(self, project_key: str, label: str) -> List[Epic]:
        """
        Retrieve all epics in a project that have a specific label.
        
        Args:
            project_key (str): The project key (e.g., 'PROJ')
            label (str): The label to filter by
            
        Returns:
            List[Epic]: List of Epic objects matching the criteria
            
        Raises:
            JIRAError: If there's an error communicating with JIRA
        """
        # Construct JQL query to find epics with the given label in the project
        jql = f'project = {project_key} AND issuetype = Epic AND labels = {label}'
        
        # Search for issues matching our criteria
        issues = self.jira.search_issues(
            jql,
            fields='summary,description,status,assignee,fixVersions,duedate,issuetype,customfield_10014,customfield_10386,customfield_10387,customfield_10379'
        )
        
        epics = []
        for issue in issues:
            epic = self._create_issue_from_response(issue, project_key)
            epics.append(epic)
        
        return epics
    
    def get_stories_by_epic(self, epic_key: str) -> List[Story]:
        """
        Retrieve all stories under a specific epic.
        
        Args:
            epic_key (str): The epic's key (e.g., 'PROJ-123')
            
        Returns:
            List[Story]: List of Story objects under the epic
            
        Raises:
            JIRAError: If there's an error communicating with JIRA
        """
        jql = f'parent = {epic_key} AND issuetype = Story'
        issues = self.jira.search_issues(
            jql,
            fields='summary,description,status,assignee,fixVersions,customfield_10016,priority,created,updated,duedate,issuetype,customfield_10014'  # 10016 is story points
        )
        
        stories = []
        for issue in issues:
            story = self._create_issue_from_response(issue)
            stories.append(story)
        
        return stories 


    def list_arns(self, components: List[str], start_time: datetime, end_time: datetime) -> List[ARN]:
        """
        List ARN project issues with specified components within a time range.
        
        Args:
            components (List[str]): List of component names to filter by
            start_time (datetime): Start of the time range
            end_time (datetime): End of the time range
            
        Returns:
            List[ARN]: List of matching ARN issues
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        # Ensure components is a list and not empty
        if not isinstance(components, list):
            raise ValueError("Components must be a list")
        if not components:
            raise ValueError("Components list cannot be empty")
        
        # Convert components list to JQL format using IN statement
        components_list = ", ".join([f'"{c}"' for c in components])
        components_jql = f'component IN ({components_list})'
        
        # Build JQL query
        jql = (
            f'project = ARN AND '
            f'{components_jql} AND '
            f'created >= "{start_time.strftime("%Y-%m-%d %H:%M")}" AND '
            f'created <= "{end_time.strftime("%Y-%m-%d %H:%M")}"'
        )
        
        # Prepare request parameters
        params = {
            'jql': jql,
            'maxResults': 100,  # Maximum results per page
            'fields': 'summary,description,created,updated,status,components,assignee,reporter,duedate,issuetype,customfield_10014'
        }
        
        issues = []
        start_at = 0
        
        while True:
            # Update start_at for pagination
            params['startAt'] = start_at
            
            # Make API request
            response = requests.get(
                f"{self.server_url}/search",
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
        

    def jira_statistics(self, components: List[str], start_time: datetime, end_time: datetime) -> ARNStats:
        """Calculate statistics for ARN issues.
        
        Args:
            components: List of components to filter issues by
            start_time: Start time for the statistics
            end_time: End time for the statistics
            
        Returns:
            ARNStats object containing the statistics
        """
        # Get all ARN issues for the components and time range
        arns = self.list_arns(components, start_time, end_time)
        
        # Calculate statistics
        total_arns = len(arns)
        return ARNStats(
            total_arns=total_arns
        ) 

    def _create_issue_from_response(self, issue, project_key: str = None) -> Union[Epic, Story]:
        """
        Create an Epic or Story object from a JIRA issue response.
        
        Args:
            issue: JIRA issue object
            project_key (Optional[str]): Project key. If None, extracted from issue key
            
        Returns:
            Union[Epic, Story]: Created issue object
        """
        due_date = self._parse_due_date(issue.fields.duedate)
        start_date = self._parse_start_date(getattr(issue.fields, 'customfield_10014', None))
        
        common_args = {
            'project_key': project_key or issue.key.split('-')[0],
            'key': issue.key,
            'summary': issue.fields.summary,
            'description': issue.fields.description,
            'status': issue.fields.status.name,
            'due_date': due_date,
            'start_date': start_date
        }
        
        if getattr(issue.fields.issuetype, 'name', None) == 'Epic':
            # Parse epic update if present
            epic_update = self._parse_epic_update(issue)
            return Epic(**common_args, last_epic_update=epic_update)
        else:
            return Story(**common_args)

    def _parse_due_date(self, due_date_str: Optional[str]) -> Optional[datetime.date]:
        """Parse a JIRA due date string into a date object."""
        if not due_date_str:
            return None
        return datetime.strptime(due_date_str, '%Y-%m-%d').date()

    def _parse_start_date(self, start_date_str: Optional[str]) -> Optional[datetime.date]:
        """Parse a JIRA start date string into a date object."""
        if not start_date_str:
            return None
        return datetime.strptime(start_date_str, '%Y-%m-%d').date()

    def _parse_epic_update(self, issue) -> Optional[EpicUpdate]:
        """Parse epic update fields from a JIRA issue.
        
        Args:
            issue: JIRA issue object
            
        Returns:
            EpicUpdate object if epic update data is present and content is not empty, None otherwise
        """
        # Get epic update fields
        update_date_str = getattr(issue.fields, 'customfield_10386', None)
        content = getattr(issue.fields, 'customfield_10387', None)
        status_str = getattr(issue.fields, 'customfield_10379', None)
        
        # Only create EpicUpdate if content is not empty
        if not content or content.strip() == '':
            return None
        
        # Parse update date
        updated = None
        if update_date_str:
            try:
                if 'T' in update_date_str:
                    # ISO format with time
                    updated = datetime.fromisoformat(update_date_str.replace('Z', '+00:00'))
                else:
                    # Simple date format - assume midnight UTC
                    updated = datetime.strptime(update_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                updated = None
        
        # Parse status
        status = EpicUpdateStatus.ON_TRACK  # Default status
        if status_str:
            try:
                # Handle different possible status formats
                status_lower = status_str.value.lower().strip()
                if 'at risk' in status_lower or 'at_risk' in status_lower:
                    status = EpicUpdateStatus.AT_RISK
                elif 'off track' in status_lower or 'off_track' in status_lower:
                    status = EpicUpdateStatus.OFF_TRACK
                elif 'on track' in status_lower or 'on_track' in status_lower:
                    status = EpicUpdateStatus.ON_TRACK
            except (ValueError, TypeError):
                status = EpicUpdateStatus.ON_TRACK
        
        return EpicUpdate(
            updated=updated,
            content=content.strip(),
            status=status
        )