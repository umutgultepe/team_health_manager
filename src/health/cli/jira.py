import click
from datetime import datetime, timezone
from ..clients.jira import JIRAClient
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

@cli.command()
@click.argument('component')
@click.option('--start', type=click.DateTime(), help='Start time in UTC (YYYY-MM-DD HH:MM:SS)')
@click.option('--end', type=click.DateTime(), help='End time in UTC (YYYY-MM-DD HH:MM:SS)')
def list_arns(component: str, start: datetime, end: datetime):
    """List ARN project issues with the specified component."""
    # Use default time range if not specified
    if not start or not end:
        start, end = get_default_time_range()
        click.echo(f"Using default time range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    
    # Ensure times are UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    
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
        