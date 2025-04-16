import click
from ..clients.sheets import SheetsClient
from .base import cli

@cli.command()
@click.argument('tab_name')
@click.argument('coordinate')
@click.argument('text')
def fill_cell(tab_name: str, coordinate: str, text: str):
    """Write text to a specific cell in the Google Sheet.
    
    Args:
        tab_name: Name of the sheet tab
        coordinate: Cell coordinate (e.g., 'A1', 'B2')
        text: Text to write to the cell
    """
    try:
        client = SheetsClient()
        result = client.write_to_cell(tab_name, coordinate, text)
        click.echo(f"Successfully wrote to cell {coordinate} in tab '{tab_name}'")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        return 