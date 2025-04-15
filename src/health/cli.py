#!/usr/bin/env python3

import click
import json
from datetime import datetime, timedelta, time, timezone
from .clients.pagerduty import PagerDutyClient
from .team_manager import TeamManager
from .dataclass import Incident

def get_default_time_range() -> tuple[datetime, datetime]:
    """
    Get the default time range for reports: Monday 00:00 to Sunday 23:59 UTC of the most recent complete week.
    
    Returns:
        tuple[datetime, datetime]: A tuple of (start_time, end_time) where:
            - end_time is 23:59:59 UTC of the most recent Sunday
            - start_time is 00:00:00 UTC of the Monday before that
    """
    # Get current time in UTC
    now = datetime.now(timezone.utc)
    
    # Find the most recent Sunday
    days_since_sunday = now.weekday() + 1  # +1 because weekday() has Monday=0, Sunday=6
    last_sunday = now - timedelta(days=days_since_sunday)
    
    # Set time to 23:59:59 UTC for end time
    end_time = datetime.combine(last_sunday.date(), time(23, 59, 59), tzinfo=timezone.utc)
    
    # Get Monday of that week (6 days before Sunday)
    start_time = datetime.combine(
        (last_sunday - timedelta(days=6)).date(), 
        time.min, 
        tzinfo=timezone.utc
    )
    
    return start_time, end_time

def print_incident(incident: Incident, raw: bool = False) -> None:
    """
    Print incident details in either raw or formatted form.
    
    Args:
        incident: The incident to print
        raw: If True, print raw JSON data. If False, print formatted output
    """
    if raw:
        click.echo("Incident Details:")
        click.echo(json.dumps(incident.raw, indent=2, sort_keys=True))
        
        if incident.raw_logs:
            click.echo("\nLog Entries (chronological order):")
            for log in incident.raw_logs:
                click.echo(json.dumps(log, indent=2, sort_keys=True))
                click.echo("-" * 80)  # Separator between logs
    else:
        click.echo(f"Title: {incident.title}")
        click.echo(f"Created: {incident.created.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        if incident.first_acknowledge_time:
            click.echo(f"First Acknowledged: {incident.first_acknowledge_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        else:
            click.echo("First Acknowledged: Not acknowledged yet")
        
        if incident.resolved_time:
            click.echo(f"Resolved: {incident.resolved_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            click.echo(f"Resolution Type: {incident.resolution_type}")
        else:
            click.echo("Resolved: Not resolved yet")
        
        click.echo(f"Timed Out: {'Yes' if incident.timed_out else 'No'}")

@click.group()
def cli():
    """Team Health Reporter - A CLI tool for reporting team health metrics."""
    pass

@cli.command()
def report():
    """Generate a team health report."""
    click.echo("Generating team health report...")

@cli.command()
@click.argument('team_key')
@click.option('--start', type=click.DateTime(), help='Start time in UTC (YYYY-MM-DD HH:MM:SS)')
@click.option('--end', type=click.DateTime(), help='End time in UTC (YYYY-MM-DD HH:MM:SS)')
@click.option('--config', default='src/health/config/team.yaml', help='Path to team configuration file')
@click.option('--raw', is_flag=True, help='Show raw incident data and logs')
def list_incidents_for_team(team_key: str, start: datetime, end: datetime, config: str, raw: bool):
    """List all incidents for a team within the specified time range."""
    # Load team configuration
    try:
        team_manager = TeamManager(config)
        team = team_manager.by_key(team_key)
        if not team:
            click.echo(f"Error: Team '{team_key}' not found in configuration", err=True)
            return
        
        if not team.escalation_policy:
            click.echo(f"Error: No escalation policy configured for team '{team_key}'", err=True)
            return
        
        # Use default time range if not specified
        if not start or not end:
            start, end = get_default_time_range()
            click.echo(f"Using default time range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        
        # Ensure times are UTC
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        
        # Get incidents
        client = PagerDutyClient()
        incidents = client.get_incidents_for_policy(
            team.escalation_policy,
            start,
            end
        )
        
        if not incidents:
            click.echo("No incidents found for the specified time range.")
            return
        
        # Print incidents
        click.echo(f"\nFound {len(incidents)} incidents for team {team.name}:")
        for incident in incidents:
            click.echo("\n" + "=" * 80)
            print_incident(incident, raw)
            
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        return

@cli.command()
@click.argument('incident_id')
@click.option('--raw', is_flag=True, help='Show raw incident data and logs')
def describe_incident(incident_id, raw):
    """Describe a specific incident."""
    client = PagerDutyClient()
    incident = client.get_incident(incident_id)
    print_incident(incident, raw)

if __name__ == "__main__":
    cli() 