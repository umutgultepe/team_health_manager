import yaml
import os
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone, timedelta
from .clients.sheets import SheetsClient
from .clients.pagerduty import PagerDutyClient
from .clients.jira import JIRAClient
from .team_manager import TeamManager
from .dataclass import PagerDutyStats, JIRAIssueStats, Team
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
        self.jira_client = JIRAClient()
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
        max_rows = 100  # Maximum number of rows to check
        
        # Get the headers we need to find for this section
        section_headers = set(self.stats_config.get(section, {}).values())
        # Read all rows at once
        range_name = f"{team_name}!A3:A{3 + max_rows - 1}"
        headers = self.sheets_client.read_vertical_range(range_name)
        
        # Build the header map
        for i, header in enumerate(headers, start=3):
            if not header:
                continue
                
            header_map[header] = i
            
            # Check if we've found all required headers for this section
            if all(header in header_map for header in section_headers):
                break
                
        return header_map
        
    def _write_stats(self, team: Team, section: str, getter: Callable[[], Any], current_col: str) -> None:
        """Write statistics for a team to the Google Sheet.
        
        Args:
            team: Team to write statistics for
            section: Section to write statistics for
            stats: Statistics to write
            current_col: Current column to write to
        """
        # Build header map
        header_map = self._build_header_map(team.name, section)
            
        # Get section headers from config
        section_headers = self.stats_config.get(section, {})
        if not section_headers:
            return

        # Check if first header is already filled
        first_header = list(section_headers.values())[0]
        if first_header in header_map:
            existing_value = self.sheets_client.read_cell(team.name, f"{current_col}{header_map[first_header]}")
            if existing_value and existing_value.strip():
                return

        stats = getter()        
        
        # Write statistics based on config headers
        for stat_key, header in section_headers.items():
            if header not in header_map:
                continue
                
            # Get the value from the stats object using the stat_key
            value = getattr(stats, stat_key, None)
            if value is None:
                continue
                
            self.sheets_client.write_to_cell(
                team.name,
                f"{current_col}{header_map[header]}",
                value
            )

    def write_stats_for_team(self, team_key: str, section: Optional[str] = None) -> None:
        """Write statistics for a team to the Google Sheet.
        
        Args:
            team_key: Key of the team to write statistics for
            section: Optional section name to limit writing to (e.g., 'PagerDuty')
        """
        # Get team information
        team = self.team_manager.by_key(team_key)
        if not team:
            raise ValueError(f"Team '{team_key}' not found in configuration")

        if section:
            self._write_stats_for_section(team, section)
        else:
            for section in self.stats_config.keys():
                self._write_stats_for_section(team, section)
            
    def _write_stats_for_section(self, team: Team, section: str) -> None:
        # Start from column B
        current_col = 'B'
        
        while True:
            # Check if column has start and end dates
            start_end_dates = self.sheets_client.read_vertical_range(f"{team.name}!{current_col}1:{current_col}2")
            if not start_end_dates or not start_end_dates[0] or not start_end_dates[1]:
                break

            start_date_str = start_end_dates[0]
            end_date_str = start_end_dates[1]
                
            # Parse dates
            start_date = datetime.strptime(start_date_str, '%m/%d/%Y').replace(
                hour=0, minute=0, second=0, tzinfo=timezone.utc
            )
            end_date = datetime.strptime(end_date_str, '%m/%d/%Y').replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            
            # Write statistics based on section
            if section == 'PagerDuty':
                # Get PagerDuty statistics
                def getter():
                    return self.pagerduty_client.policy_statistics(
                        team.escalation_policy,
                        start_date,
                        end_date
                    )
                self._write_stats(team, section, getter, current_col)
            elif section == 'JIRA' and team.components:
                # Get JIRA statistics
                def getter():
                    return self.jira_client.jira_statistics(
                        team.components,
                        start_date,
                        end_date
                    )
                self._write_stats(team, section, getter, current_col)
            
            # Move to next column
            current_col = chr(ord(current_col) + 1) 

    def fill_dates(self, team_key: Optional[str] = None) -> None:
        """Fill date ranges in the Google Sheet for a team.
        
        Args:
            team_key: Optional team key. If not provided, fills dates for all teams.
        """
        # Get teams to process
        teams = [self.team_manager.by_key(team_key)] if team_key else self.team_manager.teams
        
        for team in teams:
            if not team:
                continue
                
            # Start from column B
            current_col = 'B'
            last_start_date = None
            
            # Find the last filled column
            while True:
                start_date_str = self.sheets_client.read_cell(team.name, f"{current_col}1")
                if not start_date_str:
                    break
                    
                # Parse the date
                last_start_date = datetime.strptime(start_date_str, '%m/%d/%Y')
                current_col = chr(ord(current_col) + 1)
                
            # If we found a last date, check if we need to fill more dates
            if last_start_date:
                # Get the Monday before last
                last_monday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                while last_monday.weekday() != 0:  # 0 is Monday
                    last_monday -= timedelta(days=1)
                last_monday -= timedelta(weeks=1)  # Go back one more week
                
                # If the last date is before the Monday before last, fill more dates
                if last_start_date < last_monday:
                    # Calculate how many weeks we need to add
                    weeks_to_add = (last_monday - last_start_date).days // 7
                    
                    # Fill dates for each week
                    for i in range(weeks_to_add):
                        # Calculate new dates
                        new_start = last_start_date + timedelta(weeks=i+1)
                        new_end = new_start + timedelta(days=6)
                        
                        # Write the dates
                        self.sheets_client.write_to_cell(
                            team.name,
                            f"{current_col}1",
                            new_start.strftime('%m/%d/%Y')
                        )
                        self.sheets_client.write_to_cell(
                            team.name,
                            f"{current_col}2",
                            new_end.strftime('%m/%d/%Y')
                        )
                        
                        # Move to next column
                        current_col = chr(ord(current_col) + 1) 