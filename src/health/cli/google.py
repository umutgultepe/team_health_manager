import click
from ..clients.sheets import SheetsClient
from ..clients.drive import DriveClient
from .base import cli
from ..config.credentials import get_health_sheet_id

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
        client = SheetsClient(get_health_sheet_id())
        result = client.write_to_cell(tab_name, coordinate, text)
        click.echo(f"Successfully wrote to cell {coordinate} in tab '{tab_name}'")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        return

@cli.command()
@click.argument('local_path', type=click.Path(exists=True))
@click.argument('remote_path')
def write_file(local_path: str, remote_path: str):
    """Write a local file to Google Drive.
    
    Args:
        local_path: Path to the local file to be uploaded
        remote_path: Path where the file should be written in Google Drive
    """
    try:
        # Read the local file
        with open(local_path, 'r') as f:
            content = f.read()
            
        # Write to Google Drive
        client = DriveClient()
        client.write(remote_path, content)
        click.echo(f"Successfully wrote file to Google Drive at '{remote_path}'")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        return

@cli.command()
@click.argument('remote_path')
def read_file(remote_path: str):
    """Read a file from Google Drive and print its contents.
    
    Args:
        remote_path: Path of the file in Google Drive
    """
    try:
        client = DriveClient()
        content = client.read(remote_path)
        if content is None:
            click.echo(f"Error: File not found at '{remote_path}'", err=True)
            return
        click.echo(content)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        return 