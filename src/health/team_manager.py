import yaml
from pathlib import Path
from typing import Dict, Optional, List
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
                
            # Validate required fields
            required_fields = ['name', 'help_channel', 'oncall_handle', 'escalation_policy']
            missing_fields = [field for field in required_fields if field not in team_config]
            if missing_fields:
                raise ValueError(f"Missing required fields for team {key}: {', '.join(missing_fields)}")
            
            # Validate components is a list
            if team_config.get('components', None) and not isinstance(team_config['components'], list):
                raise ValueError(f"Components for team {key} must be a list")
            
            self.teams[key] = Team(
                key=key,
                name=team_config['name'],
                help_channel=team_config['help_channel'],
                oncall_handle=team_config['oncall_handle'],
                escalation_policy=team_config['escalation_policy'],
                components=team_config.get("components", []),
                project_keys=team_config.get("project_keys", [])
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