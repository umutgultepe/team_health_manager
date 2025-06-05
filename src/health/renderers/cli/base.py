"""
Base CLI renderer class for Team Health Manager.

This module defines the base class for all CLI-based renderers,
providing common utilities for console output.
"""

import click
from datetime import datetime
from ..base import BaseRenderer


class CliRenderer(BaseRenderer):
    """
    Base class for all CLI renderers.
    
    Provides common utilities for console output and formatting.
    All CLI renderers should inherit from this class.
    """
    
    def __init__(self):
        """Initialize the CLI renderer with console utilities."""
        self.console = click
    
    def _print_separator(self, char="═", length=80):
        """
        Print a separator line to the console.
        
        Args:
            char: Character to use for the separator
            length: Length of the separator line
        """
        click.echo(char * length)
    
    def _format_timestamp(self, dt: datetime) -> str:
        """
        Format a datetime object for CLI display.
        
        Args:
            dt: Datetime object to format
            
        Returns:
            Formatted timestamp string
        """
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    def _print_header(self, title: str, emoji: str = "🎯"):
        """
        Print a formatted header to the console.
        
        Args:
            title: Header title text
            emoji: Emoji to display with the header
        """
        click.echo(f"\n{emoji} {title}")
        self._print_separator()
    
    def _print_section(self, title: str, emoji: str = "📊"):
        """
        Print a formatted section header.
        
        Args:
            title: Section title text
            emoji: Emoji to display with the section
        """
        click.echo(f"\n{emoji} {title}:") 