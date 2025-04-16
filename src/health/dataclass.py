from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class Team:
    """Represents a team configuration."""
    name: str
    help_channel: str
    oncall_handle: str
    escalation_policy: str
    components: List[str]


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

