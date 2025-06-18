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
from ..renderers.cli.jira_execution_cli_renderer import JiraExecutionCliRenderer

def get_stats_manager(label: str, team_config: str = 'src/health/config/team.yaml', stats_config: str = 'src/health/config/execution_stats.yaml'):
    sheets_client = SheetsClient(get_execution_sheet_id())
    jira_client = JIRAClient()
    statistics_generator = ExecutionStatistics(jira_client, label)
    return StatsManager(sheets_client, statistics_generator, team_config)


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
    
    click.echo(f"🔍 Generating report context for team: {team.name}")
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
    click.echo("🔬 Analyzing epics and generating report...")
    analyzer = ExecutionAnalyzer(jira_client)
    report = analyzer.analyze_epics(all_epics)
    
    # Collect vulnerabilities from all project keys
    click.echo("🔒 Fetching vulnerabilities...")
    all_vulnerabilities = []
    
    for project_key in team.project_keys:
        vulnerabilities = jira_client.get_vulnerabilities_for_project(project_key)
        all_vulnerabilities.extend(vulnerabilities)
        click.echo(f"    Found {len(vulnerabilities)} vulnerabilities in {project_key}")
    
    # Analyze vulnerabilities
    vulnerability_stats = None
    if all_vulnerabilities:
        vulnerability_stats = analyzer.build_vulnerability_stats(all_vulnerabilities)
        click.echo(f"✅ Total vulnerabilities found: {len(all_vulnerabilities)}")
    else:
        click.echo("ℹ️  No vulnerabilities found in any project")
    
    # Render the report context
    try:
        rendered_context = analyzer.render_report_context(report, vulnerability_stats)
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
@click.option('--watch', is_flag=True, help='Enable watch mode with live updates every 60 seconds')
@click.option('--refresh-interval', default=60, help='Refresh interval in seconds for watch mode (default: 60)')
def team_execution_report(team_key: str, label: str, team_config: str, watch: bool, refresh_interval: int):
    """Generate an execution report for a team's epics with a specific label.
    
    This command:
    1. Looks up the team and gets their project keys
    2. Fetches all epics with the specified label from each project
    3. Analyzes the epics for execution problems and metrics
    4. Displays a comprehensive report
    5. With --watch flag, continuously updates the report in real-time
    
    Args:
        team_key: Key of the team to analyze (e.g., 'app_foundations')
        label: Label to filter epics by (e.g., 'Q4-2024')
        team_config: Path to team configuration file
        watch: Enable continuous monitoring with live updates
        refresh_interval: How often to refresh in watch mode (seconds)
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
    
    if watch:
        _run_watch_mode(team, label, refresh_interval)
    else:
        _run_single_report(team, label)

def _run_single_report(team, label: str):
    """Run a single execution report."""
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
    
    # Use the new renderer instead of the old print function
    renderer = JiraExecutionCliRenderer()
    renderer.render_report(report)

def _run_watch_mode(team, label: str, refresh_interval: int):
    """Run continuous watch mode with live updates."""
    import time
    import os
    from datetime import datetime
    
    click.echo(f"🔄 Starting Live Watch Mode for team: {team.name}")
    click.echo(f"📋 Label: {label}")
    click.echo(f"🎯 Project keys: {', '.join(team.project_keys)}")
    click.echo(f"⏱️  Refresh interval: {refresh_interval} seconds")
    click.echo(f"💡 Press Ctrl+C to exit watch mode\n")
    
    # Initialize JIRA client and renderer
    jira_client = JIRAClient()
    analyzer = ExecutionAnalyzer(jira_client)
    renderer = JiraExecutionCliRenderer()
    
    previous_report = None
    iteration = 0
    
    try:
        while True:
            iteration += 1
            
            # Clear screen for better readability
            os.system('clear' if os.name == 'posix' else 'cls')
            
            # Collect and analyze current data
            all_epics: List[Epic] = []
            for project_key in team.project_keys:
                epics = jira_client.get_epics_by_label(project_key, label)
                all_epics.extend(epics)
            
            if not all_epics:
                click.echo(f"❌ No epics found with label '{label}' in any of the team's projects")
                time.sleep(refresh_interval)
                continue
            
            current_report = analyzer.analyze_epics(all_epics)
            
            # Use renderer for watch mode display
            renderer.render_watch_mode(current_report, previous_report, iteration, refresh_interval)
            
            previous_report = current_report
            
            # Wait for next refresh
            for remaining in range(refresh_interval, 0, -1):
                print(f"\r🔄 Next refresh in: {remaining:2d}s (Press Ctrl+C to exit)", end="", flush=True)
                time.sleep(1)
            print()  # New line after countdown
            
    except KeyboardInterrupt:
        click.echo(f"\n\n👋 Watch mode stopped. Final iteration: {iteration}")
        click.echo("📊 Run without --watch flag for a static report.")

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