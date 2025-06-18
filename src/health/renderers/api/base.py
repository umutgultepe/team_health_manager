"""
Base API renderer class for Team Health Manager.

This module defines the base class for all API-based renderers,
providing structured data output capabilities.
"""

from ..base import BaseRenderer


class ApiRenderer(BaseRenderer):
    """
    Base class for all API renderers.
    
    Provides structured data output for API responses.
    All API renderers should inherit from this class and return dict/JSON structures.
    """
    
    def render_report(self, report, **kwargs) -> dict:
        """
        Render a report as structured data for API consumption.
        
        Args:
            report: The report data to render
            **kwargs: Additional rendering options
            
        Returns:
            dict: Structured data representation of the report
        """
        raise NotImplementedError("Subclasses must implement render_report") 