import yaml
import os
from typing import Dict, Any
from .clients.sheets import SheetsClient
from .team_manager import TeamManager

class StatsManager:
    """Manager for handling statistics and writing them to Google Sheets."""
    
    def __init__(self, team_config_path: str = 'src/health/config/team.yaml',
                 stats_config_path: str = 'src/health/config/stats.yaml'):
        """Initialize the StatsManager.
        
        Args:
            team_config_path: Path to team configuration file
            stats_config_path: Path to stats configuration file
        """
        self.team_manager = TeamManager(team_config_path)
        self.sheets_client = SheetsClient()
        self.stats_config = self._load_stats_config(stats_config_path)
        
    def _load_stats_config(self, config_path: str) -> Dict[str, Dict[str, str]]:
        """Load statistics configuration from YAML file.
        
        Args:
            config_path: Path to the stats configuration file
            
        Returns:
            Dictionary containing the stats configuration
        """
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
            
    def write_headers_for_team(self, team_key: str) -> None:
        """Write headers for a team's statistics in the Google Sheet.
        
        Args:
            team_key: Key of the team to write headers for
        """
        # Get team information
        team = self.team_manager.by_key(team_key)
        if not team:
            raise ValueError(f"Team '{team_key}' not found in configuration")
            
        # Start at row 3
        current_row = 3
        
        # Write section headers and row headers
        for section_name, stats in self.stats_config.items():
            # Write section header
            self.sheets_client.write_to_cell(team.name, f"A{current_row}", section_name)
            current_row += 1
            
            # Write row headers
            for stat_key, header in stats.items():
                self.sheets_client.write_to_cell(team.name, f"A{current_row}", header)
                current_row += 1
                
            # Skip a row after section
            current_row += 1 