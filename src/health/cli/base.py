import click
from datetime import datetime, timedelta, time, timezone

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

def ensure_utc_time(dt: datetime) -> datetime:
    """Ensure a datetime is UTC-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

@click.group()
def cli():
    """Team Health Reporter - A CLI tool for reporting team health metrics."""
    pass

@cli.command()
def report():
    """Generate a team health report."""
    click.echo("Generating team health report...")

# Import all subcommands
from . import slack  # noqa
from . import pagerduty  # noqa
from . import jira  # noqa 