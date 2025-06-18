"""
Base renderer classes for Team Health Manager.

This module defines the abstract base classes that all renderers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseRenderer(ABC):
    """
    Abstract base class for all renderers.
    
    All renderers must implement the render_report method to handle
    the presentation of data in their specific format.
    """
    
    @abstractmethod
    def render_report(self, report, **kwargs) -> Any:
        """
        Render a report in the specific format supported by this renderer.
        
        Args:
            report: The report data to render (type varies by renderer)
            **kwargs: Additional rendering options specific to the renderer
            
        Returns:
            Any: The rendered output (varies by renderer - could be None for CLI,
                 dict for API, str for web, etc.)
        """
        pass 