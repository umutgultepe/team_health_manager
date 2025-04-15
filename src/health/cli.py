#!/usr/bin/env python3

import click
import json
from datetime import datetime
from .clients.pagerduty import PagerDutyClient

@click.group()
def cli():
    """Team Health Reporter - A CLI tool for reporting team health metrics."""
    pass

@cli.command()
def report():
    """Generate a team health report."""
    click.echo("Generating team health report...")

@cli.command()
@click.argument('incident_id')
@click.option('--raw', is_flag=True, help='Show raw incident data and logs')
def describe_incident(incident_id, raw):
    """Describe a specific incident."""
    client = PagerDutyClient()
    incident = client.get_incident(incident_id)
    
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

if __name__ == "__main__":
    cli() 