import click
import sys
from typing import List
from ..dataclass import IssueStatus
from ..clients.jira import JIRAClient
from ..execution_analyzer import ExecutionAnalyzer
from ..team_manager import TeamManager
from ..dataclass import Epic
from .base import cli
from ..config.credentials import get_execution_sheet_id
from ..clients.sheets import SheetsClient
from ..statistics_generator import ExecutionStatistics
from ..stats_manager import StatsManager

def get_stats_manager(label: str, team_config: str = 'src/health/config/team.yaml', stats_config: str = 'src/health/config/execution_stats.yaml'):
    sheets_client = SheetsClient(get_execution_sheet_id())
    jira_client = JIRAClient()
    statistics_generator = ExecutionStatistics(jira_client, label)
    return StatsManager(sheets_client, statistics_generator, team_config)


def print_execution_report(report):
    """Print the execution report in a formatted way."""
    click.echo(f"\n📊 Execution Report")
    click.echo("=" * 50)
    
    # Print epic summary
    epic_count = len(report.epics)
    click.echo(f"📋 Total Epics: {epic_count}")
    
    if epic_count > 0:
        # Group epics by status
        status_counts = {}
        for epic in report.epics:
            status = epic.get_status().value if hasattr(epic, 'get_status') else epic.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        click.echo("\n📈 Epic Status Breakdown:")
        for status, count in status_counts.items():
            percentage = (count / epic_count) * 100
            click.echo(f"  {status}: {count} ({percentage:.1f}%)")
    
    # Print story summary
    story_count = len(report.stories) if hasattr(report, 'stories') and report.stories else 0
    click.echo(f"\n📝 Total Stories: {story_count}")
    
    # Print problems summary
    problem_count = len(report.problems) if hasattr(report, 'problems') and report.problems else 0
    click.echo(f"\n⚠️  Total Problems Found: {problem_count}")
    
    if problem_count > 0:
        # Group problems by type
        problem_types = {}
        for problem in report.problems:
            problem_type = problem.problem_type.value if hasattr(problem.problem_type, 'value') else str(problem.problem_type)
            problem_types[problem_type] = problem_types.get(problem_type, 0) + 1
        
        click.echo("\n🔍 Problem Breakdown:")
        for problem_type, count in problem_types.items():
            click.echo(f"  {problem_type}: {count}")
        
        # Show first few problems as examples
        click.echo("\n📋 Sample Problems:")
        for i, problem in enumerate(report.problems[:5]):  # Show first 5 problems
            click.echo(f"  {i+1}. {problem.description}")
        
        if problem_count > 5:
            click.echo(f"  ... and {problem_count - 5} more problems")
    
    click.echo("\n" + "=" * 50)

@cli.command()
@click.argument('epic_key')
def evaluate_epic_update(epic_key: str):
    """Evaluate an epic update using AI scoring.
    
    This command:
    1. Fetches the specified epic from JIRA
    2. Uses AI to evaluate the epic's latest update
    3. Displays detailed scoring and explanations
    
    Args:
        epic_key: The epic key to evaluate (e.g., 'PROJ-123')
    """
    click.echo(f"🔍 Evaluating epic update for: {epic_key}")
    
    # Initialize JIRA client and ExecutionAnalyzer
    jira_client = JIRAClient()
    analyzer = ExecutionAnalyzer(jira_client)
    
    try:
        # Get the epic
        click.echo(f"📋 Fetching epic from JIRA...")
        epic = jira_client.get_epic(epic_key)
        
        # Evaluate the epic update
        click.echo(f"🤖 Evaluating epic update using AI...")
        evaluation = analyzer.score_epic_update(epic)
        
        # Display results
        click.echo(f"\n🎯 Epic Update Evaluation Results")
        click.echo("=" * 60)
        click.echo(f"Epic: {epic.key} - {epic.summary}")
        
        if epic.last_epic_update:
            click.echo(f"Update Date: {epic.last_epic_update.updated.strftime('%Y-%m-%d %H:%M:%S UTC') if epic.last_epic_update.updated else 'Unknown'}")
            click.echo(f"Update Status: {epic.last_epic_update.status.value}")
        
        click.echo(f"\n⭐ Overall Average Score: {evaluation.average_score:.1f}/5")
        click.echo("\n📊 Detailed Scoring:")
        click.echo("-" * 40)
        
        # Display each evaluation criterion
        criteria = [
            ("Epic Status Clarity", evaluation.epic_status_clarity),
            ("Deliverables Defined", evaluation.deliverables_defined),
            ("Risk Identification", evaluation.risk_identification),
            ("Mitigation Measures", evaluation.mitigation_measures),
            ("Status Enum Justification", evaluation.status_enum_justification),
            ("Delivery Confidence", evaluation.delivery_confidence)
        ]
        
        for criterion_name, evaluation_obj in criteria:
            score_bar = "★" * evaluation_obj.score + "☆" * (5 - evaluation_obj.score)
            click.echo(f"\n{criterion_name}: {evaluation_obj.score}/5 {score_bar}")
            click.echo(f"   💬 {evaluation_obj.explanation}")
        
        click.echo("\n" + "=" * 60)
        
    except ValueError as e:
        click.echo(f"❌ Validation Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('team_key')
@click.option('--team-config', default='src/health/config/team.yaml', help='Path to team configuration file')
@click.option('--stats-config', default='src/health/config/stats.yaml', help='Path to stats configuration file')
def write_execution_headers(team_key: str, team_config: str, stats_config: str):
    """Write headers for a team's statistics in the Google Sheet.
    
    Args:
        team_key: Key of the team to write headers for
        team_config: Path to team configuration file
        stats_config: Path to stats configuration file
    """
    manager = get_stats_manager("no_label", team_config, stats_config)
    manager.write_headers_for_team(team_key)
    click.echo(f"Successfully wrote headers for team {team_key}")

@cli.command()
@click.argument('team_key')
@click.argument('label')
@click.option('--section', default=None, help='Section to write statistics for (e.g., PagerDuty)')
@click.option('--team-config', default='src/health/config/team.yaml', help='Path to team configuration file')
@click.option('--stats-config', default='src/health/config/stats.yaml', help='Path to stats configuration file')
def write_execution_stats(team_key: str, label: str, section: str, team_config: str, stats_config: str):
    """Write statistics for a team to the Google Sheet.
    
    Args:
        team_key: Key of the team to write statistics for
        section: Optional section name to limit writing to
        team_config: Path to team configuration file
        stats_config: Path to stats configuration file
    """
    manager = get_stats_manager(label, team_config, stats_config)
    manager.write_stats_for_team(team_key, section)
    click.echo(f"Successfully wrote statistics for team {team_key}")

@cli.command()
@click.argument('team_key')
@click.argument('label')
@click.option('--team-config', default='src/health/config/team.yaml', help='Path to team configuration file')
def team_execution_report(team_key: str, label: str, team_config: str):
    """Generate an execution report for a team's epics with a specific label.
    
    This command:
    1. Looks up the team and gets their project keys
    2. Fetches all epics with the specified label from each project
    3. Analyzes the epics for execution problems and metrics
    4. Displays a comprehensive report
    
    Args:
        team_key: Key of the team to analyze (e.g., 'app_foundations')
        label: Label to filter epics by (e.g., 'Q4-2024')
        team_config: Path to team configuration file
    """
    # Load team configuration
    team_manager = TeamManager(team_config)
    team = team_manager.by_key(team_key)
    
    if not team:
        click.echo(f"Error: Team '{team_key}' not found in configuration", err=True)
        sys.exit(1)
    
    # Check if team has project keys
    if not hasattr(team, 'project_keys') or not team.project_keys:
        click.echo(f"Error: Team '{team.name}' has no project keys configured", err=True)
        sys.exit(1)
    
    click.echo(f"🔍 Analyzing execution for team: {team.name}")
    click.echo(f"📋 Label: {label}")
    click.echo(f"🎯 Project keys: {', '.join(team.project_keys)}")
    
    # Initialize JIRA client
    jira_client = JIRAClient()
    
    # Collect epics from all project keys
    all_epics: List[Epic] = []
    
    for project_key in team.project_keys:
        click.echo(f"  ↳ Fetching epics from project {project_key}...")
        epics = jira_client.get_epics_by_label(project_key, label)
        all_epics.extend(epics)
        click.echo(f"    Found {len(epics)} epics in {project_key}")
    
    if not all_epics:
        click.echo(f"\n❌ No epics found with label '{label}' in any of the team's projects")
        return
    
    click.echo(f"\n✅ Total epics collected: {len(all_epics)}")
    
    # Initialize ExecutionAnalyzer and analyze epics
    click.echo("🔬 Analyzing epics for execution problems...")
    analyzer = ExecutionAnalyzer(jira_client)
    report = analyzer.analyze_epics(all_epics)
    
    # Print the report
    print_execution_report(report)


@cli.command()
@click.argument('team_key')
@click.argument('label')
@click.option('--team-config', default='src/health/config/team.yaml', help='Path to team configuration file')
def epic_updates(team_key: str, label: str, team_config: str):
    """Show epic updates for in-progress epics of a team with a specific label.
    
    This command:
    1. Looks up the team and gets their project keys
    2. Fetches all epics with the specified label from each project
    3. Shows epic updates for epics that are in IN_PROGRESS status
    
    Args:
        team_key: Key of the team to analyze (e.g., 'app_foundations')
        label: Label to filter epics by (e.g., 'Q4-2024')
        team_config: Path to team configuration file
    """
    # Load team configuration
    team_manager = TeamManager(team_config)
    team = team_manager.by_key(team_key)
    
    if not team:
        click.echo(f"Error: Team '{team_key}' not found in configuration", err=True)
        sys.exit(1)
    
    # Check if team has project keys
    if not hasattr(team, 'project_keys') or not team.project_keys:
        click.echo(f"Error: Team '{team.name}' has no project keys configured", err=True)
        sys.exit(1)
    
    click.echo(f"🔍 Fetching epic updates for team: {team.name}")
    click.echo(f"📋 Label: {label}")
    click.echo(f"🎯 Project keys: {', '.join(team.project_keys)}")
    
    # Initialize JIRA client
    jira_client = JIRAClient()
    
    # Collect epics from all project keys
    all_epics: List[Epic] = []
    
    for project_key in team.project_keys:
        click.echo(f"  ↳ Fetching epics from project {project_key}...")
        epics = jira_client.get_epics_by_label(project_key, label)
        all_epics.extend(epics)
        click.echo(f"    Found {len(epics)} epics in {project_key}")
    
    if not all_epics:
        click.echo(f"\n❌ No epics found with label '{label}' in any of the team's projects")
        return
    
    # Filter for IN_PROGRESS epics
    in_progress_epics = [epic for epic in all_epics if epic.get_status() == IssueStatus.IN_PROGRESS]
    
    if not in_progress_epics:
        click.echo(f"\n📋 No in-progress epics found with label '{label}'")
        return
    
    click.echo(f"\n🚧 Found {len(in_progress_epics)} in-progress epics:")
    click.echo("=" * 80)
    
    for epic in in_progress_epics:
        click.echo(f"\n🎯 Epic: {epic.key} - {epic.summary}")
        click.echo(f"📊 Status: {epic.status}")
        if epic.due_date:
            click.echo(f"📅 Due Date: {epic.due_date.strftime('%Y-%m-%d')}")
        else:
            click.echo("📅 Due Date: Not set")
        
        # Show epic update if available
        if epic.last_epic_update and epic.last_epic_update.content:
            click.echo(f"\n📝 Latest Epic Update:")
            if epic.last_epic_update.updated:
                click.echo(f"   🕒 Updated: {epic.last_epic_update.updated.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            click.echo(f"   🚦 Status: {epic.last_epic_update.status.value}")
            click.echo(f"   💬 Content:")
            # Indent the content for better readability
            content_lines = epic.last_epic_update.content.split('\n')
            for line in content_lines:
                click.echo(f"      {line}")
        else:
            click.echo("\n⚠️  No epic update available")
        
        click.echo("-" * 80)

@cli.command()
@click.argument('team_key')
@click.option('--team-config', default='src/health/config/team.yaml', help='Path to team configuration file')
def list_vulnerabilities(team_key: str, team_config: str):
    """List all vulnerabilities for a team across all their projects.
    
    This command:
    1. Looks up the team and gets their project keys
    2. Fetches all vulnerabilities from each project
    3. Displays a summary of vulnerabilities found
    
    Args:
        team_key: Key of the team to analyze (e.g., 'app_foundations')
        team_config: Path to team configuration file
    """
    # Load team configuration
    team_manager = TeamManager(team_config)
    team = team_manager.by_key(team_key)
    
    if not team:
        click.echo(f"Error: Team '{team_key}' not found in configuration", err=True)
        sys.exit(1)
    
    # Check if team has project keys
    if not hasattr(team, 'project_keys') or not team.project_keys:
        click.echo(f"Error: Team '{team.name}' has no project keys configured", err=True)
        sys.exit(1)
    
    click.echo(f"🔍 Listing vulnerabilities for team: {team.name}")
    click.echo(f"🎯 Project keys: {', '.join(team.project_keys)}")
    
    # Initialize JIRA client
    jira_client = JIRAClient()
    
    # Collect vulnerabilities from all project keys
    all_vulnerabilities = []
    
    for project_key in team.project_keys:
        click.echo(f"\n  ↳ Fetching vulnerabilities from project {project_key}...")
        vulnerabilities = jira_client.get_vulnerabilities_for_project(project_key)
        all_vulnerabilities.extend(vulnerabilities)
        click.echo(f"    Found {len(vulnerabilities)} vulnerabilities in {project_key}")
        
        # Show individual vulnerabilities for this project
        if vulnerabilities:
            for vuln in vulnerabilities:
                status_emoji = "🔴" if vuln.get_status() in [IssueStatus.TODO, IssueStatus.IN_PROGRESS] else "🟢"
                due_date_str = vuln.due_date.strftime('%Y-%m-%d') if vuln.due_date else "No due date"
                click.echo(f"      {status_emoji} {vuln.key}: {vuln.summary}")
                click.echo(f"        Status: {vuln.status} | Due: {due_date_str}")
    
    if not all_vulnerabilities:
        click.echo(f"\n✅ No vulnerabilities found in any of the team's projects")
        return
    
    # Print summary
    click.echo(f"\n📊 Vulnerability Summary")
    click.echo("=" * 50)
    click.echo(f"📋 Total Vulnerabilities: {len(all_vulnerabilities)}")
    
    # Group by status
    status_counts = {}
    for vuln in all_vulnerabilities:
        status = vuln.get_status().value if hasattr(vuln, 'get_status') else vuln.status
        status_counts[status] = status_counts.get(status, 0) + 1
    
    click.echo(f"\n📈 Status Breakdown:")
    for status, count in status_counts.items():
        percentage = (count / len(all_vulnerabilities)) * 100
        click.echo(f"  {status}: {count} ({percentage:.1f}%)")
    
    # Group by project
    project_counts = {}
    for vuln in all_vulnerabilities:
        project_counts[vuln.project_key] = project_counts.get(vuln.project_key, 0) + 1
    
    click.echo(f"\n🎯 Project Breakdown:")
    for project, count in project_counts.items():
        percentage = (count / len(all_vulnerabilities)) * 100
        click.echo(f"  {project}: {count} ({percentage:.1f}%)")
    
    click.echo("\n" + "=" * 50)
