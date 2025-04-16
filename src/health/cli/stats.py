import click
from ..stats_manager import StatsManager
from .base import cli
from typing import Optional

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
    try:
        manager = StatsManager(team_config, stats_config)
        manager.write_headers_for_team(team_key)
        click.echo(f"Successfully wrote headers for team {team_key}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        return

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
    manager = StatsManager(team_config, stats_config)
    manager.write_stats_for_team(team_key, section)
    click.echo(f"Successfully wrote statistics for team {team_key}")

@cli.command()
@click.argument('team_key', required=False)
def fill_dates(team_key: Optional[str] = None) -> None:
    """Fill date ranges in the Google Sheet for a team.
    
    Args:
        team_key: Optional team key. If not provided, fills dates for all teams.
    """
    try:
        stats_manager = StatsManager()
        stats_manager.fill_dates(team_key)
        click.echo("Successfully filled dates")
    except Exception as e:
        click.echo(f"Error filling dates: {e}", err=True)
        raise click.Abort()