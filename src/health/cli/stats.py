import click
from ..stats_manager import StatsManager
from .base import cli

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