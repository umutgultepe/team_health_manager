from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, date
from enum import Enum

@dataclass
class Team:
    """Team configuration."""
    key: str
    name: str
    help_channel: str
    oncall_handle: str
    components: List[str]
    escalation_policy: str
    project_keys: List[str]


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
    high_urgency: bool = False
    
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
        self.high_urgency = incident_data.get('urgency', {}) == "high"
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
class PagerDutyStats:
    """Statistics for PagerDuty incidents."""
    total_incidents: int
    auto_resolved: int
    timed_out: int
    high_urgency_incidents: int
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

class IssueStatus(Enum):
    TODO = "TODO"
    IN_PROGRESS = "In Progress"
    DONE = "Done"
    INVALID = "Invalid"


STATUS_MAP = {
    "backlog": IssueStatus.TODO,
    "todo": IssueStatus.TODO,
    "to do": IssueStatus.TODO,
    "in progress": IssueStatus.IN_PROGRESS,
    "assigned": IssueStatus.IN_PROGRESS,
    "blocked": IssueStatus.IN_PROGRESS,
    "in review": IssueStatus.IN_PROGRESS,
    "pending product/design input": IssueStatus.IN_PROGRESS,
    "done": IssueStatus.DONE,
    "abandoned": IssueStatus.INVALID,
    "duplicate": IssueStatus.INVALID,
    "wont fix": IssueStatus.INVALID,
    "won't fix": IssueStatus.INVALID,
    "code review / pending push": IssueStatus.IN_PROGRESS,
    "ready for deployment": IssueStatus.IN_PROGRESS,
}

@dataclass
class Issue:
    """Base class for JIRA issues."""
    project_key: str
    key: str
    summary: str
    description: Optional[str]
    status: str

    def get_status(self) -> IssueStatus:
        return STATUS_MAP[self.status.lower()]


@dataclass
class ARN(Issue):
    """Represents an ARN (Action Required Now) issue."""
    created: datetime
    updated: datetime
    components: List[str]
    assignee: str
    reporter: str

class EpicUpdateStatus(Enum):
    ON_TRACK = "On Track"
    AT_RISK = "At Risk"
    OFF_TRACK = "Off Track"

@dataclass
class EpicUpdate:
    updated: datetime # customfield_10386
    content: str # customfield_10387
    status: EpicUpdateStatus # customfield_10379


@dataclass
class Epic(Issue):
    """Represents a JIRA epic."""
    due_date: Optional[datetime.date] = None
    start_date: Optional[datetime.date] = None
    last_epic_update: Optional[EpicUpdate] = None

@dataclass
class Vulnerability(Issue):
    """Represents a JIRA epic."""
    due_date: Optional[datetime.date] = None

@dataclass
class Story(Issue):
    """Represents a JIRA story."""
    due_date: Optional[datetime.date] = None
    start_date: Optional[datetime.date] = None

@dataclass
class ARNStats:
    """Statistics for ARN (Action Required Now) issues."""
    total_arns: int




class ProblemType(Enum):
    MISSING_START_DATE = "No start date"
    MISSING_DUE_DATE = "No due date"
    PAST_DUE_DATE = "Past due date"
    IN_PROGRESS_BEFORE_START_DATE = "In progress before start date"
    MISSING_EPIC_UPDATE = "Missing epic update"
    IN_PROGRESS_EPIC_WITHOUT_STORIES = "In progress epic without stories"
    DUE_DATE_CHANGED = "Due date changed"
    LOW_EPIC_UPDATE_SCORE = "Low epic update score"


@dataclass
class TrackingProblem:
    problem_type: ProblemType
    description: str
    issue: Issue

@dataclass
class ExecutionStats:
    in_progress_epics: int
    missing_epic_update: int
    missing_start_date: int
    missing_due_date: int
    past_due_date: int
    in_progress_before_start_date: int
    in_progress_epic_without_stories: int
    due_date_changed: int


@dataclass
class Evaluation:
    score: int
    explanation: str

@dataclass
class EpicStatusEvaluation:
    epic_key: str
    epic_status_clarity: Evaluation
    deliverables_defined: Evaluation
    risk_identification_and_mitigation: Evaluation
    status_enum_justification: Evaluation
    delivery_confidence: Evaluation
    average_score: float

@dataclass
class VulnerabilityStats:
    open_vulnerabilities: int
    vulnerabilities_past_due_date: int
    vulnerabilities: List[Vulnerability]

@dataclass
class ExecutionReport:
    """Statistics for JIRA issues."""
    epics: List[Epic]
    problems: List[TrackingProblem]
    stories: List[Story]
    evaluations: Dict[str, EpicStatusEvaluation]