from typing import List
from datetime import date
from .clients.jira import JIRAClient
from .dataclass import Epic, ExecutionReport, TrackingProblem, ProblemType, IssueStatus, Issue


class ExecutionAnalyzer:
    """Analyzer for execution-related JIRA data and reporting."""
    
    def __init__(self, jira_client: JIRAClient):
        """Initialize the ExecutionAnalyzer with a JIRA client.
        
        Args:
            jira_client: An instance of JIRAClient for interacting with JIRA
        """
        self.jira_client = jira_client

    def analyze_epics(self, epics: List[Epic]) -> ExecutionReport:
        """Analyze a list of epics and return an ExecutionReport.

        Args:
            epics: List of epics to analyze

        Returns:
            ExecutionReport containing the analysis results
        """
        problems = []
        all_stories = []
        for epic in epics:
            problems.extend(self._analyze_status(epic))
            if epic.get_status() == IssueStatus.IN_PROGRESS:
                stories = self.jira_client.get_stories_by_epic(epic.key)
                if not stories:
                    problems.append(TrackingProblem(
                        problem_type=ProblemType.IN_PROGRESS_EPIC_WITHOUT_STORIES,
                        description=f"Epic {epic.key} is in IN_PROGRESS status but has no stories",
                        issue=epic
                    ))
                else:
                    for story in stories:
                        problems.extend(self._analyze_status(story))
                        all_stories.append(story)
        return ExecutionReport(epics=epics, problems=problems, stories=all_stories)
    
    def _analyze_status(self, issue: Issue) -> List[TrackingProblem]:
        problems = []
        issue_type_name = type(issue).__name__

        if not issue.due_date:
            problems.append(TrackingProblem(
                problem_type=ProblemType.MISSING_DUE_DATE,
                description=f"{issue_type_name} {issue.key} has no due date set",
                issue=issue
            ))
        if not issue.start_date:
            problems.append(TrackingProblem(
                problem_type=ProblemType.MISSING_START_DATE,
                description=f"{issue_type_name} {issue.key} has no start date set",
                issue=issue
            ))

        if issue.get_status() == IssueStatus.TODO and issue.start_date and issue.start_date < date.today():
            problems.append(TrackingProblem(
                problem_type=ProblemType.IN_PROGRESS_BEFORE_START_DATE,
                description=f"{issue_type_name} {issue.key} is in TODO status but has a start date in the past",
                issue=issue
            ))

        if issue.get_status() == IssueStatus.IN_PROGRESS and issue.start_date and issue.start_date > date.today():
            problems.append(TrackingProblem(
                problem_type=ProblemType.IN_PROGRESS_BEFORE_START_DATE,
                description=f"{issue_type_name} {issue.key} is in IN_PROGRESS status but has a start date in the future",
                issue=issue
            ))  
        
        if issue.get_status() not in  [IssueStatus.DONE, IssueStatus.INVALID] and issue.due_date and issue.due_date < date.today():
            problems.append(TrackingProblem(
                problem_type=ProblemType.PAST_DUE_DATE,
                description=f"{issue_type_name} {issue.key} is in {issue.get_status().value} status but has a due date in the past",
                issue=issue
            ))

        return problems