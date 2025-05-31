import click
import sys
from typing import List
from ..clients.jira import JIRAClient
from ..execution_analyzer import ExecutionAnalyzer
from ..team_manager import TeamManager
from ..dataclass import Epic
from .base import cli


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
