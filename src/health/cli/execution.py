import click
import sys
from typing import List
from ..dataclass import IssueStatus
from ..clients.jira import JIRAClient
from ..clients.drive import DriveClient
from ..execution_analyzer import ExecutionAnalyzer
from ..team_manager import TeamManager
from ..dataclass import Epic, Team
from .base import cli
from ..config.credentials import get_execution_sheet_id
from ..clients.sheets import SheetsClient
from ..statistics_generator import ExecutionStatistics
from ..stats_manager import StatsManager
from ..clients.docs import DocsClient

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
        click.echo("\n📋 Problems:")
        for i, problem in enumerate(report.problems):  # Show first 5 problems
            click.echo(f"  {i+1}. {problem.description}")
    
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
        ("Risk Identification And Mitigation", evaluation.risk_identification_and_mitigation),
        ("Status Enum Justification", evaluation.status_enum_justification),
        ("Delivery Confidence", evaluation.delivery_confidence)
    ]
    
    for criterion_name, evaluation_obj in criteria:
        score_bar = "★" * evaluation_obj.score + "☆" * (5 - evaluation_obj.score)
        click.echo(f"\n{criterion_name}: {evaluation_obj.score}/5 {score_bar}")
        click.echo(f"   💬 {evaluation_obj.explanation}")
    
    click.echo("\n" + "=" * 60)

@cli.command()
@click.argument('team_key')
@click.argument('label')
@click.option('--team-config', default='src/health/config/team.yaml', help='Path to team configuration file')
def render_report_context(team_key: str, label: str, team_config: str):
    """Render a detailed execution report context for AI summarization.
    
    This command:
    1. Looks up the team and gets their project keys
    2. Fetches all epics with the specified label from each project
    3. Analyzes the epics for execution problems and metrics
    4. Renders a comprehensive report using Jinja2 template
    5. Prints the rendered context for further processing
    
    Args:
        team_key: Key of the team to analyze (e.g., 'app_foundations')
        label: Label to filter epics by (e.g., 'Q4-2024')
        team_config: Path to team configuration file
    """
    try:
        # Get stats manager and use its generator to render the context
        team_manager = TeamManager(team_config)
        team = team_manager.by_key(team_key)
        manager = get_stats_manager(label, team_config)
        rendered_context = manager.generator.render_context(team)
        
        click.echo("\n📄 Rendered Report Context:")
        click.echo("=" * 80)
        click.echo(rendered_context)
        click.echo("=" * 80)
        
    except Exception as e:
        click.echo(f"❌ Error rendering report: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('context_file_path')
def render_from_context(context_file_path: str):
    """Generate an execution report from a context file using AI.
    
    This command:
    1. Reads the execution report context from the specified file
    2. Uses AI to generate a formatted execution report
    3. Prints the rendered report
    
    Args:
        context_file_path: Path to the file containing the execution report context
    """
    click.echo(f"📄 Reading context from: {context_file_path}")
    
    # Read the context file
    try:
        with open(context_file_path, 'r') as f:
            context_content = f.read()
        
        if not context_content.strip():
            click.echo(f"❌ Error: Context file is empty", err=True)
            sys.exit(1)
            
        click.echo(f"✅ Successfully read {len(context_content)} characters from context file")
        
    except FileNotFoundError:
        click.echo(f"❌ Error: Context file not found: {context_file_path}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error reading context file: {e}", err=True)
        sys.exit(1)
    
    # Initialize ExecutionAnalyzer (no JIRA client needed for this operation)
    jira_client = JIRAClient()  # Still needed for the analyzer constructor
    analyzer = ExecutionAnalyzer(jira_client)
    
    # Generate the execution report
    click.echo("🤖 Generating execution report using AI...")
    rendered_report = analyzer.render_execution_report(context_content)
    
    click.echo(rendered_report)
        

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
    try:
        # Get team and stats manager
        team_manager = TeamManager(team_config)
        team = team_manager.by_key(team_key)
        if not team:
            click.echo(f"Error: Team '{team_key}' not found in configuration", err=True)
            sys.exit(1)
            
        manager = get_stats_manager(label, team_config)
        
        # Get and print the report
        report = manager.generator.get_report(team)
        print_execution_report(report)
        
    except Exception as e:
        click.echo(f"❌ Error generating report: {e}", err=True)
        sys.exit(1)


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
    """List all vulnerabilities for a team's projects.
    
    This command:
    1. Looks up the team and gets their project keys
    2. Fetches all vulnerabilities from each project
    3. Displays a comprehensive list with status breakdown
    
    Args:
        team_key: Key of the team to analyze (e.g., 'app_foundations')
        team_config: Path to team configuration file
    """
    try:
        # Get team and stats manager
        team_manager = TeamManager(team_config)
        team = team_manager.by_key(team_key)
        if not team:
            click.echo(f"Error: Team '{team_key}' not found in configuration", err=True)
            sys.exit(1)
            
        manager = get_stats_manager("no_label", team_config)
        
        # Get vulnerabilities
        all_vulnerabilities = manager.generator.get_vulnerabilities(team)
        
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
        
    except Exception as e:
        click.echo(f"❌ Error listing vulnerabilities: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('team_key')
@click.argument('label')
@click.option('--team-config', default='src/health/config/team.yaml', help='Path to team configuration file')
def refresh_execution_for_team(team_key: str, label: str, team_config: str):
    """Refresh execution data for a team and upload the report context to Google Drive.
    
    This command:
    1. Initializes a stats manager for the given team and label
    2. Fills dates for the team
    3. Writes stats for the team
    4. Renders the execution context
    5. Uploads the context to Google Drive
    
    Args:
        team_key: Key of the team to analyze (e.g., 'app_foundations')
        label: Label to filter epics by (e.g., 'Q4-2024')
        team_config: Path to team configuration file
    """
    # Get team and stats manager
    team_manager = TeamManager(team_config)
    team = team_manager.by_key(team_key)
    if not team:
        click.echo(f"Error: Team '{team_key}' not found in configuration", err=True)
        sys.exit(1)

    _refresh_execution_for_team(team, label, team_config)
        

def _refresh_execution_for_team(team: Team, label: str, team_config: str):
    manager = get_stats_manager(label, team_config)
    
    # Fill dates and write stats
    click.echo(f"📊 Filling dates for team {team.key}...")
    manager.fill_dates(team.key)
    
    click.echo(f"📝 Writing stats for team {team.key}...")
    manager.write_stats_for_team(team.key)
    
    # Get the report and render context
    click.echo(f"📄 Rendering execution context...")
    generator = manager.generator
    analyzer = generator.analyzer
    report = generator.get_report(team)
    vulnerability_stats = generator.get_vulnerability_stats(team)
    rendered_context = analyzer.render_report_context(report, vulnerability_stats)
    
    # Get remote path and upload to Google Drive
    remote_path = analyzer.get_remote_path_for_context(team)
    click.echo(f"📤 Uploading context to Google Drive at '{remote_path}'...")
    
    # Write to Google Drive
    drive_client = DriveClient()
    drive_client.write(remote_path, rendered_context)
    
    click.echo("✅ Successfully refreshed execution data and uploaded context")

@cli.command()
@click.argument('label')
@click.option('--team-config', default='src/health/config/team.yaml', help='Path to team configuration file')
@click.option('--skip-teams', help='Comma-separated list of team keys to skip (e.g., "team1,team2")')
def refresh_all_execution(label: str, team_config: str, skip_teams: str):
    """Refresh execution data for all teams and upload their report contexts to Google Drive.
    
    This command:
    1. Gets all teams from the team configuration
    2. For each team, calls refresh_execution_for_team with the given label
    3. Shows progress for each team being processed
    
    Args:
        label: Label to filter epics by (e.g., 'Q4-2024')
        team_config: Path to team configuration file
        skip_teams: Comma-separated list of team keys to skip
    """
    # Get all teams
    team_manager = TeamManager(team_config)
    teams = team_manager.get_all_teams()
    
    if not teams:
        click.echo("❌ No teams found in configuration", err=True)
        sys.exit(1)
    
    # Parse skip teams if provided
    skip_team_keys = set()
    if skip_teams:
        skip_team_keys = {key.strip() for key in skip_teams.split(',')}
        click.echo(f"⏭️  Skipping teams: {', '.join(skip_team_keys)}")
    
    # Filter out skipped teams
    teams_to_process = [team for team in teams if team.key not in skip_team_keys]
    
    if not teams_to_process:
        click.echo("❌ No teams remaining after applying skip filter", err=True)
        sys.exit(1)
    
    click.echo(f"🔄 Starting execution refresh for {len(teams_to_process)} teams...")
    
    # Process each team
    for i, team in enumerate(teams_to_process, 1):
        click.echo(f"\n📋 Processing team {i}/{len(teams_to_process)}: {team.key}")
        _refresh_execution_for_team(team, label, team_config)
    
    click.echo("\n✅ Successfully refreshed execution data for all teams")

@cli.command()
@click.argument('team_key')
@click.option('--team-config', default='src/health/config/team.yaml', help='Path to team configuration file')
def write_report_for_team(team_key: str, team_config: str):
    """Write an execution report for a team to Google Docs.
    
    This command:
    1. Gets the team information
    2. Downloads the context from Google Drive
    3. Renders the report content using AI
    4. Writes the content to Google Docs using the team name as the tab name
    
    Args:
        team_key: Key of the team to analyze (e.g., 'app_foundations')
        team_config: Path to team configuration file
    """
    # Initialize clients
    jira_client = JIRAClient()
    drive_client = DriveClient()
    docs_client = DocsClient()
    analyzer = ExecutionAnalyzer(jira_client)
    
    # Get team information
    team_manager = TeamManager(team_config)
    team = team_manager.by_key(team_key)
    
    # Get the remote path for the context
    remote_path = analyzer.get_remote_path_for_context(team)

    if True:
        # Download the context from Google Drive
        click.echo(f"📥 Downloading context from: {remote_path}")
        context_content = drive_client.read(remote_path)
        
        if not context_content:
            click.echo(f"❌ Error: Could not read context from {remote_path}", err=True)
            sys.exit(1)
            
        # Render the report content
        click.echo("🤖 Generating execution report using AI...")
        report_content = analyzer.render_execution_report(context_content)
    else:
        # Read report content from file
        import os
        report_path = os.path.expanduser('~/dev/tmp/af_report.md')
        click.echo(f"📥 Reading report from: {report_path}")
        with open(report_path, 'r') as f:
            report_content = f.read()
    
    # Write to Google Docs
    click.echo(f"📝 Writing report to Google Docs tab: {team.name}")
    docs_client.write_markdown(team.name, report_content)
    
    click.echo("✅ Successfully wrote execution report to Google Docs")