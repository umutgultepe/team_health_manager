"""
Base web renderer class for Team Health Manager.

This module defines the base class for all web-based renderers,
providing HTML output capabilities.
"""

from ..base import BaseRenderer


class WebRenderer(BaseRenderer):
    """
    Base class for all web renderers.
    
    Provides HTML output for web consumption.
    All web renderers should inherit from this class and return HTML strings.
    """
    
    def render_report(self, report, **kwargs) -> str:
        """
        Render a report as HTML for web consumption.
        
        Args:
            report: The report data to render
            **kwargs: Additional rendering options
            
        Returns:
            str: HTML representation of the report
        """
        raise NotImplementedError("Subclasses must implement render_report") 