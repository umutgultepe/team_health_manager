import yaml
from pathlib import Path
from typing import Dict, Optional
from .dataclass import Team

class TeamManager:
    """
    Manages team configurations and provides lookup functionality.
    Teams are loaded from a YAML configuration file.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize TeamManager with a path to the team configuration file.
        
        Args:
            config_path (str): Path to the team configuration YAML file
        
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            yaml.YAMLError: If the configuration file is invalid YAML
        """
        self.config_path = Path(config_path)
        self.teams: Dict[str, Team] = {}
        self._load_teams()
    
    def _load_teams(self) -> None:
        """
        Load teams from the configuration file into the teams dictionary.
        
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            yaml.YAMLError: If the configuration file is invalid YAML
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Team configuration file not found: {self.config_path}")
            
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
            
        if not isinstance(config, dict):
            raise ValueError("Team configuration must be a dictionary")
            
        for key, team_config in config.items():
            if not isinstance(team_config, dict):
                raise ValueError(f"Team configuration for {key} must be a dictionary")
                
            self.teams[key] = Team(
                name=team_config.get('name', key),
                escalation_policy=team_config.get('escalation_policy')
            )
    
    def by_key(self, key: str) -> Optional[Team]:
        """
        Get a team by its key.
        
        Args:
            key (str): The team's key in the configuration
            
        Returns:
            Optional[Team]: The team if found, None otherwise
        """
        return self.teams.get(key) 