import click
import json
from datetime import datetime, timezone
from ..clients.pagerduty import PagerDutyClient
from ..team_manager import TeamManager
from ..dataclass import Incident
from .base import cli, get_default_time_range

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
    try:
        client = PagerDutyClient()
        incident = client.get_incident(incident_id)
        print_incident(incident, raw)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        return 