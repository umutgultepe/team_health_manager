from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


@dataclass
class Team:
    """Team configuration."""
    name: str
    help_channel: str
    oncall_handle: str
    components: List[str]
    escalation_policy: str


@dataclass
class Person:
    name: str
    email: str


@dataclass
class Incident:
    """Represents a PagerDuty incident."""
    raw: Dict[str, Any]
    raw_logs: List[Dict[str, Any]] = None
    title: str = None
    created: datetime = None
    first_acknowledge_time: datetime = None
    resolved_time: datetime = None
    resolution_type: str = None
    timed_out: bool = False
    
    @property
    def time_to_acknowledgement(self) -> Optional[timedelta]:
        """Calculate time between incident creation and first acknowledgment.
        
        Returns:
            Optional[timedelta]: Time to acknowledgment if acknowledged, None otherwise
        """
        if not self.first_acknowledge_time or not self.created:
            return None
        return self.first_acknowledge_time - self.created

    @property
    def time_to_acknowledgement_minutes(self) -> Optional[float]:
        """Calculate time between incident creation and first acknowledgment in minutes.
        
        Returns:
            Optional[float]: Time to acknowledgment in minutes if acknowledged, None otherwise
        """
        if not self.time_to_acknowledgement:
            return None
        return self.time_to_acknowledgement.total_seconds() / 60

    def __post_init__(self):
        # Parse fields from raw response
        incident_data = self.raw.get('incident', {})
        self.title = incident_data.get('title')
        created_at = incident_data.get('created_at')
        if created_at:
            self.created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        # Find first acknowledgment time from logs
        has_acknowledgment = False
        if self.raw_logs:
            for log in self.raw_logs:
                if log.get('type') == 'acknowledge_log_entry':
                    created_at = log.get('created_at')
                    if created_at:
                        self.first_acknowledge_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        has_acknowledgment = True
                        break

                # Find resolution time and determine resolution type
                if log.get('type') == 'resolve_log_entry':
                    created_at = log.get('created_at')
                    if created_at:
                        self.resolved_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        # Check if it's an auto-resolution
                        if (not has_acknowledgment and 
                            log.get('summary') == "Resolved through the API."):
                            self.resolution_type = "AUTO"
                        else:
                            self.resolution_type = "MANUAL"
                        break

                # Check for timeout escalations
                if (log.get('type') == 'escalate_log_entry' and 
                    log.get('channel', {}).get('type') == 'timeout'):
                    self.timed_out = True
                    break


@dataclass
class JIRAIssue:
    """Represents a JIRA issue."""
    key: str
    summary: str
    description: str
    created: datetime
    updated: datetime
    status: str
    components: List[str]
    assignee: str
    reporter: str


@dataclass
class PagerDutyStats:
    """Statistics for PagerDuty incidents."""
    total_incidents: int
    auto_resolved: int
    timed_out: int
    mean_time_to_acknowledgement: Optional[timedelta]
    total_response_time: timedelta
    
    @property
    def mean_time_to_acknowledgement_minutes(self) -> Optional[float]:
        """Get mean time to acknowledgment in minutes.
        
        Returns:
            Mean time in minutes if available, None otherwise
        """
        if not self.mean_time_to_acknowledgement:
            return None
        return self.mean_time_to_acknowledgement.total_seconds() / 60
        
    @property
    def total_response_time_hours(self) -> float:
        """Get total response time in hours.
        
        Returns:
            Total response time in hours
        """
        return self.total_response_time.total_seconds() / 3600

    @property
    def mtta_str(self) -> str:
        """Get mean time to acknowledgment as a formatted string in minutes.
        
        Returns:
            Formatted string with 2 decimal places, or "N/A" if not available
        """
        if not self.mean_time_to_acknowledgement_minutes:
            return "N/A"
        return f"{self.mean_time_to_acknowledgement_minutes:.2f}"

    @property
    def total_response_time_str(self) -> str:
        """Get total response time as a formatted string in hours.
        
        Returns:
            Formatted string with 2 decimal places, or "N/A" if not available
        """
        if not self.total_response_time_hours:
            return "N/A"
        return f"{self.total_response_time_hours:.2f}"


@dataclass
class JIRAIssueStats:
    """Statistics for JIRA issues."""
    total_arns: int