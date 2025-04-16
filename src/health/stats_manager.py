import yaml
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from .clients.sheets import SheetsClient
from .clients.pagerduty import PagerDutyClient
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
        self.pagerduty_client = PagerDutyClient()
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
            
    def _build_header_map(self, team_name: str, section: str) -> Dict[str, int]:
        """Build a map of header text to row number for a team's tab.
        
        Args:
            team_name: Name of the team (tab name)
            section: Name of the section to get headers for (e.g., 'PagerDuty')
            
        Returns:
            Dictionary mapping header text to row number
        """
        header_map = {}
        current_row = 3  # Start at row 3
        max_rows = 100  # Maximum number of rows to check
        
        # Get the headers we need to find for this section
        section_headers = set(self.stats_config.get(section, {}).values())
        
        # Read headers until we find all required headers or reach max rows
        while current_row <= max_rows:
            header = self.sheets_client.read_cell(team_name, f"A{current_row}")
            if not header:
                break
                
            header_map[header] = current_row
            
            # Check if we've found all required headers for this section
            if all(header in header_map for header in section_headers):
                break
                
            current_row += 1
            
        return header_map
        
    def write_stats_for_team(self, team_key: str, section: str) -> None:
        """Write statistics for a team to the Google Sheet.
        
        Args:
            team_key: Key of the team to write statistics for
            section: Optional section name to limit writing to (e.g., 'PagerDuty')
        """
        # Get team information
        team = self.team_manager.by_key(team_key)
        if not team:
            raise ValueError(f"Team '{team_key}' not found in configuration")
            
        # Build header map
        header_map = self._build_header_map(team.name, section)
        
        # Start from column B
        current_col = 'B'
        
        while True:
            # Check if column has start and end dates
            start_date_str = self.sheets_client.read_cell(team.name, f"{current_col}1")
            end_date_str = self.sheets_client.read_cell(team.name, f"{current_col}2")
            
            if not start_date_str or not end_date_str:
                break
                
            # Parse dates
            start_date = datetime.strptime(start_date_str, '%m/%d/%Y').replace(
                hour=0, minute=0, second=0, tzinfo=timezone.utc
            )
            end_date = datetime.strptime(end_date_str, '%m/%d/%Y').replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            
            # Get PagerDuty statistics
            stats = self.pagerduty_client.policy_statistics(
                team.escalation_policy,
                start_date,
                end_date
            )
            
            # Write statistics
            if section is None or section == 'PagerDuty':
                # Write total incidents
                if 'Incident Count' in header_map:
                    self.sheets_client.write_to_cell(
                        team.name,
                        f"{current_col}{header_map['Incident Count']}",
                        str(stats.total_incidents)
                    )
                    
                # Write auto resolved
                if 'Auto Resolved' in header_map:
                    self.sheets_client.write_to_cell(
                        team.name,
                        f"{current_col}{header_map['Auto Resolved']}",
                        str(stats.auto_resolved)
                    )
                    
                # Write timed out
                if 'Missed Response (Escalated)' in header_map:
                    self.sheets_client.write_to_cell(
                        team.name,
                        f"{current_col}{header_map['Missed Response (Escalated)']}",
                        str(stats.timed_out)
                    )
                    
                # Write mean time to acknowledgment
                if 'Mean Time to Acknowledgment' in header_map:
                    value = f"{stats.mean_time_to_acknowledgement_minutes:.2f}" if stats.mean_time_to_acknowledgement_minutes else "N/A"
                    self.sheets_client.write_to_cell(
                        team.name,
                        f"{current_col}{header_map['Mean Time to Acknowledgment']}",
                        value
                    )
                    
                # Write total response time
                if 'Total Incident Window' in header_map:
                    self.sheets_client.write_to_cell(
                        team.name,
                        f"{current_col}{header_map['Total Incident Window']}",
                        f"{stats.total_response_time_hours:.2f}"
                    )
            
            # Move to next column
            current_col = chr(ord(current_col) + 1) 