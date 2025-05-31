import click
from ..stats_manager import StatsManager
from ..statistics_generator import HealthStatistics
from ..clients.sheets import SheetsClient
from ..clients.pagerduty import PagerDutyClient
from ..clients.jira import JIRAClient
from ..config.credentials import get_health_sheet_id
from .base import cli
from typing import Optional


def get_stats_manager(team_config: str = 'src/health/config/team.yaml', stats_config: str = 'src/health/config/stats.yaml'):
    sheets_client = SheetsClient(get_health_sheet_id())
    pagerduty_client = PagerDutyClient()
    jira_client = JIRAClient()
    statistics_generator = HealthStatistics(pagerduty_client, jira_client)
    return StatsManager(sheets_client, statistics_generator, team_config)

@cli.command()
@click.argument('team_key')
@click.option('--team-config', default='src/health/config/team.yaml', help='Path to team configuration file')
@click.option('--stats-config', default='src/health/config/stats.yaml', help='Path to stats configuration file')
def write_headers(team_key: str, team_config: str, stats_config: str):
    """Write headers for a team's statistics in the Google Sheet.
    
    Args:
        team_key: Key of the team to write headers for
        team_config: Path to team configuration file
        stats_config: Path to stats configuration file
    """
    manager = get_stats_manager(team_config, stats_config)
    manager.write_headers_for_team(team_key)
    click.echo(f"Successfully wrote headers for team {team_key}")

@cli.command()
@click.argument('team_key')
@click.option('--section', default=None, help='Section to write statistics for (e.g., PagerDuty)')
@click.option('--team-config', default='src/health/config/team.yaml', help='Path to team configuration file')
@click.option('--stats-config', default='src/health/config/stats.yaml', help='Path to stats configuration file')
def write_stats(team_key: str, section: str, team_config: str, stats_config: str):
    """Write statistics for a team to the Google Sheet.
    
    Args:
        team_key: Key of the team to write statistics for
        section: Optional section name to limit writing to
        team_config: Path to team configuration file
        stats_config: Path to stats configuration file
    """
    manager = get_stats_manager(team_config, stats_config)
    manager.write_stats_for_team(team_key, section)
    click.echo(f"Successfully wrote statistics for team {team_key}")

@cli.command()
@click.argument('section')
@click.argument('header') # 'Header to overwrite. Should be a key in the stats config (e.g. mtta_str).'
@click.option('--team-key', default=None, help='Team key to overwrite statistics for. If not provided, processes all teams.')
@click.option('--team-config', default='src/health/config/team.yaml', help='Path to team configuration file')
@click.option('--stats-config', default='src/health/config/stats.yaml', help='Path to stats configuration file')
def overwrite(section: str, header: str, team_key: Optional[str], team_config: str, stats_config: str):
    """Overwrite statistics for a specific section and header.
    
    Args:
        section: Section name to overwrite (e.g., PagerDuty)
        header: Header name to overwrite
        team_key: Optional team key. If not provided, processes all teams
        team_config: Path to team configuration file
        stats_config: Path to stats configuration file
    """
    manager = get_stats_manager(team_config, stats_config)
    
    if team_key:
        # Process single team
        manager.write_stats_for_team(team_key, section, header)
        click.echo(f"Successfully overwrote {section}/{header} for team {team_key}")
    else:
        # Process all teams
        teams = manager.team_manager.teams
        for current_team_key, team in teams.items():
            if not team:
                continue
            click.echo(f"Processing team: {team.name}")
            manager.write_stats_for_team(current_team_key, section, header)
        click.echo(f"Successfully overwrote {section}/{header} for all teams")

@cli.command()
@click.argument('team_key', required=False)
def fill_dates(team_key: Optional[str] = None) -> None:
    """Fill date ranges in the Google Sheet for a team.
    
    Args:
        team_key: Optional team key. If not provided, fills dates for all teams.
    """
    stats_manager = get_stats_manager()
    stats_manager.fill_dates(team_key)
    click.echo("Successfully filled dates")

@cli.command()
@click.option('--skip-date-fill', is_flag=True, help='Skip filling dates before writing statistics')
def refresh_all(skip_date_fill: bool) -> None:
    """Refresh statistics for all teams.
    
    Args:
        skip_date_fill: If True, skip filling dates before writing statistics
    """
    stats_manager = get_stats_manager()
    
    # Get all teams
    teams = stats_manager.team_manager.teams
    
    for team_key, team in teams.items():
        if not team:
            continue
            
        click.echo(f"Processing team: {team.name}")
        
        # Fill dates unless skipped
        if not skip_date_fill:
            click.echo("  Filling dates...")
            stats_manager.fill_dates(team_key)
            
        # Write statistics for all sections
        click.echo("  Writing statistics...")
        stats_manager.write_stats_for_team(team_key)
            
    click.echo("Successfully refreshed all teams")