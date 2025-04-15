import click
import json
from datetime import datetime
from ..clients.slack import SlackClient
from .base import cli, get_default_time_range, ensure_utc_time

@cli.command()
@click.argument('channel')
@click.option('--start', type=click.DateTime(), help='Start time in UTC (YYYY-MM-DD HH:MM:SS)')
@click.option('--end', type=click.DateTime(), help='End time in UTC (YYYY-MM-DD HH:MM:SS)')
@click.option('--raw', is_flag=True, help='Show raw message data')
def get_slack_messages(channel: str, start: datetime, end: datetime, raw: bool):
    """Fetch messages from a Slack channel within the specified time range."""
    try:
        # Use default time range if not specified
        if not start or not end:
            start, end = get_default_time_range()
            click.echo(f"Using default time range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        
        # Ensure times are UTC
        start = ensure_utc_time(start)
        end = ensure_utc_time(end)
        
        # Initialize Slack client and get messages
        client = SlackClient()
        messages = client.get_messages(channel, start, end)
        
        if not messages:
            click.echo("No messages found for the specified time range.")
            return
        
        click.echo(f"\nFound {len(messages)} messages in #{channel}:")
        
        for message in messages:
            if raw:
                click.echo("\n" + "=" * 80)
                click.echo(json.dumps(message, indent=2, sort_keys=True))
            else:
                click.echo("\n" + "=" * 80)
                # Format timestamp to readable date
                ts = datetime.fromtimestamp(float(message['ts']))
                click.echo(f"Time: {ts.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                click.echo(f"User: {message.get('user', 'Unknown')}")
                click.echo(f"Text: {message.get('text', '')}")
                
                # Show thread information if available
                if message.get('thread_ts'):
                    click.echo(f"Thread: {message['thread_ts']}")
                    if message.get('reply_count'):
                        click.echo(f"Replies: {message['reply_count']}")
                
                # Show reactions if any
                if message.get('reactions'):
                    click.echo("\nReactions:")
                    for reaction in message['reactions']:
                        click.echo(f":{reaction['name']}: x{reaction['count']}")
                
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        return 