import click
import yaml
import requests
from datetime import datetime, timezone
from pathlib import Path
from ..clients.jira import JIRAClient
from ..team_manager import TeamManager
from .base import cli, get_default_time_range

def print_issue(issue) -> None:
    """Print JIRA issue details in a formatted way."""
    click.echo(f"\nKey: {issue.key}")
    click.echo(f"Summary: {issue.summary}")
    click.echo(f"Status: {issue.status}")
    click.echo(f"Created: {issue.created.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    click.echo(f"Updated: {issue.updated.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    click.echo(f"Components: {', '.join(issue.components)}")
    click.echo(f"Assignee: {issue.assignee}")
    click.echo(f"Reporter: {issue.reporter}")
    click.echo("-" * 80)

def get_time_range(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Get the time range for JIRA queries, handling defaults and UTC conversion."""
    # Use default time range if not specified
    if not start or not end:
        start, end = get_default_time_range()
        click.echo(f"Using default time range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    
    # Ensure times are UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    
    return start, end

@cli.command()
@click.argument('component')
@click.option('--start', type=click.DateTime(), help='Start time in UTC (YYYY-MM-DD HH:MM:SS)')
@click.option('--end', type=click.DateTime(), help='End time in UTC (YYYY-MM-DD HH:MM:SS)')
def list_arns(component: str, start: datetime, end: datetime):
    """List ARN project issues with the specified component."""
    start, end = get_time_range(start, end)
    
    # Get issues
    client = JIRAClient()
    issues = client.list_arns([component], start, end)
    
    if not issues:
        click.echo("No issues found for the specified component and time range.")
        return
    
    # Print issues
    click.echo(f"\nFound {len(issues)} ARN issues with component '{component}':")
    for issue in issues:
        print_issue(issue)

@cli.command()
@click.argument('team_key')
@click.option('--start', type=click.DateTime(), help='Start time in UTC (YYYY-MM-DD HH:MM:SS)')
@click.option('--end', type=click.DateTime(), help='End time in UTC (YYYY-MM-DD HH:MM:SS)')
@click.option('--config', default='src/health/config/team.yaml', help='Path to team configuration file')
def team_arns(team_key: str, start: datetime, end: datetime, config: str):
    """List ARN project issues for a team's components."""
    try:
        # Load team configuration
        team_manager = TeamManager(config)
        team = team_manager.by_key(team_key)
        if not team:
            click.echo(f"Error: Team '{team_key}' not found in configuration", err=True)
            return
        
        start, end = get_time_range(start, end)
        
        # Get issues
        client = JIRAClient()
        # Pass components as a list, just like in list_arns
        issues = client.list_arns(team.components, start, end)
        
        if not issues:
            click.echo(f"No issues found for team '{team_key}' components in the specified time range.")
            return
        
        # Print issues
        click.echo(f"\nFound {len(issues)} ARN issues for team {team.name}:")
        for issue in issues:
            print_issue(issue)
            
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        return
        