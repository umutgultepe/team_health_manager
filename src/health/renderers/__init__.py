"""
Renderer package for Team Health Manager.

This package contains all presentation layer implementations following
a hierarchical pattern: BaseRenderer -> SpecificRenderer -> OutputRenderer
"""

from .base import BaseRenderer

__all__ = ['BaseRenderer'] 