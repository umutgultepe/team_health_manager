from typing import List
from datetime import date, timedelta
import json
from jinja2 import Environment, FileSystemLoader
from .clients.jira import JIRAClient
from .clients.ai import AIClient
from .dataclass import Epic, ExecutionReport, TrackingProblem, ProblemType, IssueStatus, Issue, ExecutionStats, EpicStatusEvaluation, Evaluation, Vulnerability, VulnerabilityStats


class ExecutionAnalyzer:
    """Analyzer for execution-related JIRA data and reporting."""
    
    def __init__(self, jira_client: JIRAClient):
        """Initialize the ExecutionAnalyzer with a JIRA client.
        
        Args:
            jira_client: An instance of JIRAClient for interacting with JIRA
        """
        self.jira_client = jira_client
        self.ai_client = AIClient()

    def analyze_epics(self, epics: List[Epic]) -> ExecutionReport:
        """Analyze a list of epics and return an ExecutionReport.

        Args:
            epics: List of epics to analyze

        Returns:
            ExecutionReport containing the analysis results
        """
        problems = []
        all_stories = []
        evaluations = {}
        for epic in epics:
            problems.extend(self._analyze_status(epic))
            if epic.get_status() != IssueStatus.IN_PROGRESS:
                continue

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

            if not self._has_epic_update(epic):
                problems.append(TrackingProblem(
                    problem_type=ProblemType.MISSING_EPIC_UPDATE,
                    description=f"Epic {epic.key} is in progress but has no recent update (older than 7 days)",
                    issue=epic
                ))
            else:
                epic_status_evaluation = self.score_epic_update(epic)
                evaluations[epic.key] = epic_status_evaluation
                if epic_status_evaluation.average_score <= 3.5:
                    problems.append(TrackingProblem(
                        problem_type=ProblemType.LOW_EPIC_UPDATE_SCORE,
                        description=f"Epic {epic.key} has a low average score ({epic_status_evaluation.average_score})",
                        issue=epic
                    ))
        
        return ExecutionReport(epics=epics, problems=problems, stories=all_stories, evaluations=evaluations)

        

    def build_vulnerability_stats(self, vulnerabilities: List[Vulnerability]) -> VulnerabilityStats:
        """Analyze a list of vulnerabilities and return a VulnerabilityStats.
        
        Args:
            vulnerabilities: List of vulnerabilities to analyze
            
        Returns:
            VulnerabilityStats containing the analysis results
        """
        open_vulnerabilities = sum(1 for vulnerability in vulnerabilities 
                                 if vulnerability.get_status() in [IssueStatus.TODO, IssueStatus.IN_PROGRESS])
        past_due_date = sum(1 for vulnerability in vulnerabilities if vulnerability.due_date and vulnerability.due_date < date.today())

        return VulnerabilityStats(
            open_vulnerabilities=open_vulnerabilities,
            vulnerabilities_past_due_date=past_due_date,
            vulnerabilities=vulnerabilities
        )

    def build_statistics(self, epics: List[Epic]) -> ExecutionStats:
        """Build execution statistics from a list of epics.
        
        Args:
            epics: List of epics to analyze
            
        Returns:
            ExecutionStats containing calculated statistics
        """
        report = self.analyze_epics(epics)
        
        # Count epics by status
        in_progress_epics = sum(1 for epic in epics if epic.get_status() == IssueStatus.IN_PROGRESS)
        
        # Count problems by type
        missing_start_date = sum(1 for problem in report.problems if problem.problem_type == ProblemType.MISSING_START_DATE)
        missing_due_date = sum(1 for problem in report.problems if problem.problem_type == ProblemType.MISSING_DUE_DATE)
        past_due_date = sum(1 for problem in report.problems if problem.problem_type == ProblemType.PAST_DUE_DATE)
        in_progress_before_start_date = sum(1 for problem in report.problems if problem.problem_type == ProblemType.IN_PROGRESS_BEFORE_START_DATE)
        missing_epic_update = sum(1 for problem in report.problems if problem.problem_type == ProblemType.MISSING_EPIC_UPDATE)
        in_progress_epic_without_stories = sum(1 for problem in report.problems if problem.problem_type == ProblemType.IN_PROGRESS_EPIC_WITHOUT_STORIES)
        due_date_changed = sum(1 for problem in report.problems if problem.problem_type == ProblemType.DUE_DATE_CHANGED)
        
        return ExecutionStats(
            in_progress_epics=in_progress_epics,
            missing_start_date=missing_start_date,
            missing_due_date=missing_due_date,
            past_due_date=past_due_date,
            in_progress_before_start_date=in_progress_before_start_date,
            missing_epic_update=missing_epic_update,
            in_progress_epic_without_stories=in_progress_epic_without_stories,
            due_date_changed=due_date_changed
        )

    def _has_epic_update(self, epic: Epic) -> bool:
        if not epic.last_epic_update:
            return False
        if not epic.last_epic_update.updated:
            return False
        last_update_age = date.today() - epic.last_epic_update.updated.date()
        return last_update_age.days < 7

    def _analyze_status(self, issue: Issue) -> List[TrackingProblem]:
        problems = []
        issue_type_name = type(issue).__name__

        if issue.get_status() in [IssueStatus.TODO, IssueStatus.IN_PROGRESS] and not issue.due_date:
            problems.append(TrackingProblem(
                problem_type=ProblemType.MISSING_DUE_DATE,
                description=f"{issue_type_name} {issue.key} has no due date set",
                issue=issue
            ))
        if issue.get_status() == IssueStatus.TODO and not issue.start_date:
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

    def score_epic_update(self, epic: Epic) -> EpicStatusEvaluation:
        """Score an epic update using AI evaluation.
        
        Args:
            epic: Epic object containing the update to evaluate
            
        Returns:
            EpicStatusEvaluation: Evaluation scores and explanations
            
        Raises:
            ValueError: If epic has no last_epic_update or update content is empty
            Exception: If AI API call fails or response cannot be parsed
        """
        # Validate epic has an update
        if not epic.last_epic_update:
            raise ValueError(f"Epic {epic.key} has no epic update to evaluate")
        
        if not epic.last_epic_update.content or epic.last_epic_update.content.strip() == '':
            raise ValueError(f"Epic {epic.key} has empty update content")
        
        # Load the evaluation prompt template
        try:
            with open('src/health/config/epic_evaluation.txt', 'r') as f:
                prompt_template = f.read()
        except FileNotFoundError:
            raise FileNotFoundError("Evaluation prompt template not found at src/health/config/evaluation.txt")
        
        # Fill in the template variables
        prompt = prompt_template.replace('{{status}}', epic.last_epic_update.status.value)
        prompt = prompt.replace('{{update}}', epic.last_epic_update.content)
        
        # Make AI API call
        try:
            response = self.ai_client.call_api(prompt)
        except Exception as e:
            raise Exception(f"AI API call failed: {str(e)}")
        
        # Parse the JSON response
        try:
            # Extract JSON from response (in case there's extra text)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in AI response")
            
            json_str = response[json_start:json_end]
            evaluation_data = json.loads(json_str)
            
            # Create Evaluation objects from the response
            epic_status_clarity = Evaluation(
                score=evaluation_data["Epic Status Clarity"]["score"],
                explanation=evaluation_data["Epic Status Clarity"]["explanation"]
            )
            
            deliverables_defined = Evaluation(
                score=evaluation_data["Deliverables Defined"]["score"],
                explanation=evaluation_data["Deliverables Defined"]["explanation"]
            )
            
            risk_identification_and_mitigation = Evaluation(
                score=evaluation_data["Risk Identification And Mitigation"]["score"],
                explanation=evaluation_data["Risk Identification And Mitigation"]["explanation"]
            )
             
            status_enum_justification = Evaluation(
                score=evaluation_data["Status Enum Justification"]["score"],
                explanation=evaluation_data["Status Enum Justification"]["explanation"]
            )
            
            delivery_confidence = Evaluation(
                score=evaluation_data["Delivery Confidence"]["score"],
                explanation=evaluation_data["Delivery Confidence"]["explanation"]
            )
            
            average_score = evaluation_data["Average Score"]
            
            return EpicStatusEvaluation(
                epic_key=epic.key,
                epic_status_clarity=epic_status_clarity,
                deliverables_defined=deliverables_defined,
                risk_identification_and_mitigation=risk_identification_and_mitigation,
                status_enum_justification=status_enum_justification,
                delivery_confidence=delivery_confidence,
                average_score=average_score
            )
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise Exception(f"Failed to parse AI response: {str(e)}. Response: {response}")

    def render_report_context(self, report: ExecutionReport, vulnerability_stats: VulnerabilityStats = None) -> str:
        """Render an ExecutionReport using a Jinja2 template.
        
        Args:
            report: ExecutionReport object containing epics, problems, and stories
            vulnerability_stats: Optional VulnerabilityStats object containing vulnerability data
            
        Returns:
            str: Rendered template as a string
            
        Raises:
            Exception: If template loading or rendering fails
        """
        try:
            # Set up Jinja2 environment
            env = Environment(loader=FileSystemLoader('src/health/config'))
            template = env.get_template('execution_report_template.jinja2')
            
            # Prepare context data
            context = {
                'epics': report.epics,
                'problems': report.problems,
                'stories': report.stories,
                'evaluations': report.evaluations,
                'vulnerability_stats': vulnerability_stats,
                'today': date.today(),
                'timedelta': timedelta
            }
            
            # Render the template
            rendered = template.render(**context)
            return rendered
            
        except Exception as e:
            raise Exception(f"Failed to render report template: {str(e)}")

    def render_execution_report(self, report_context: str) -> str:
        """Generate an execution report using AI from the provided context.
        
        Args:
            report_context: String containing the execution report context data
            
        Returns:
            str: AI-generated execution report
        """
        # Set up Jinja2 environment for the prompt template
        env = Environment(loader=FileSystemLoader('src/health/config'))
        template = env.get_template('report_prompt.txt')
        
        # Import credentials to get template variables
        from .config.credentials import JIRA_DOMAIN, get_health_sheet_id, get_execution_sheet_id
        
        # Prepare template variables from credentials
        template_vars = {
            'JIRA_DOMAIN': f"https://{JIRA_DOMAIN}",
            'HEALTH_SHEET_ID': get_health_sheet_id(),
            'EXECUTION_SHEET_ID': get_execution_sheet_id()
        }
        
        # Render the prompt template with variables
        rendered_prompt = template.render(**template_vars)
        
        # Prepare the full prompt by appending the context to the rendered prompt
        full_prompt = f"{rendered_prompt}\n\nContext Document:\n{report_context}"
        
        # Make AI API call
        response = self.ai_client.call_api(full_prompt)
        return response