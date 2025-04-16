import click
import json
from datetime import datetime, timezone, timedelta
from ..clients.pagerduty import PagerDutyClient
from ..team_manager import TeamManager
from ..dataclass import Incident
from .base import cli, get_default_time_range

def get_time_range(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Get the time range for incident queries.
    
    Args:
        start: Optional start time
        end: Optional end time
        
    Returns:
        Tuple of (start_time, end_time) in UTC
    """
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
        
        # Get time range
        start, end = get_time_range(start, end)
        
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
@click.argument('team_key')
@click.option('--start', type=click.DateTime(), help='Start time in UTC (YYYY-MM-DD HH:MM:SS)')
@click.option('--end', type=click.DateTime(), help='End time in UTC (YYYY-MM-DD HH:MM:SS)')
@click.option('--config', default='src/health/config/team.yaml', help='Path to team configuration file')
def pager_stats(team_key: str, start: datetime, end: datetime, config: str):
    """Show incident statistics for a team."""
    try:
        # Load team configuration
        team_manager = TeamManager(config)
        team = team_manager.by_key(team_key)
        if not team:
            click.echo(f"Error: Team '{team_key}' not found in configuration", err=True)
            return
        
        if not team.escalation_policy:
            click.echo(f"Error: No escalation policy configured for team '{team_key}'", err=True)
            return
        
        # Get time range
        start, end = get_time_range(start, end)
        
        # Get incidents
        client = PagerDutyClient()
        incidents = client.get_incidents_for_policy(
            team.escalation_policy,
            start,
            end
        )
        
        if not incidents:
            click.echo(f"No incidents found for team {team.name} in the specified time range.")
            return
        
        # Calculate statistics
        total_incidents = len(incidents)
        auto_resolved = sum(1 for i in incidents if i.resolution_type == "AUTO")
        timed_out = sum(1 for i in incidents if i.timed_out)
        
        # Calculate mean time to acknowledgment
        acknowledgment_times = [i.time_to_acknowledgement for i in incidents if i.time_to_acknowledgement is not None]
        mean_time_to_ack = sum(acknowledgment_times, timedelta()) / len(acknowledgment_times) if acknowledgment_times else None
        
        # Print statistics
        click.echo(f"\nIncident Statistics for {team.name}:")
        click.echo("=" * 40)
        click.echo(f"Total Incidents: {total_incidents}")
        click.echo(f"Auto Resolved: {auto_resolved}")
        click.echo(f"Missed Response: {timed_out}")
        if mean_time_to_ack:
            hours = mean_time_to_ack.total_seconds() / 3600
            click.echo(f"Mean Time to Acknowledgment: {hours:.2f} hours")
        else:
            click.echo("Mean Time to Acknowledgment: No acknowledged incidents")
        click.echo("=" * 40)
            
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