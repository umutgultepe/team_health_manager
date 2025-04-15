from ..dataclass import Incident
from ..config.pagerduty import PAGERDUTY_API_KEY, PAGERDUTY_EMAIL
import requests
import json
from typing import Optional, Dict, Any

class PagerDutyClient:
    def __init__(self):
        self.api_key = PAGERDUTY_API_KEY
        self.email = PAGERDUTY_EMAIL
        self.base_url = "https://api.pagerduty.com"
        self.headers = {
            "Authorization": f"Token token={self.api_key}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "From": self.email
        }

    def get_incident(self, incident_key: str) -> Incident:
        """
        Retrieve an incident from PagerDuty using the incident key.
        Includes assignees and users in the response.
        
        Args:
            incident_key (str): The unique identifier of the incident
            
        Returns:
            Incident: An Incident object containing the incident data and logs
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        try:
            # Get incident details
            url = f"{self.base_url}/incidents/{incident_key}"
            params = {
                "include[]": ["assignees", "users"]
            }
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            incident_data = response.json()
            
            # Get the canonical incident ID from the response
            incident_id = incident_data.get('incident', {}).get('id')
            if not incident_id:
                raise ValueError(f"Could not find incident ID in response for key {incident_key}")
            
            # Get incident logs using the canonical ID
            logs_url = f"{self.base_url}/incidents/{incident_id}/log_entries"
            logs_response = requests.get(logs_url, headers=self.headers)
            logs_response.raise_for_status()
            logs_data = logs_response.json()
            
            # Sort logs by time (earliest first)
            sorted_logs = sorted(logs_data.get("log_entries", []), 
                               key=lambda x: x.get("created_at", ""))
            
            return Incident(
                raw=incident_data,
                raw_logs=sorted_logs
            )
            
        except requests.exceptions.RequestException as e:
            # Log the error and re-raise
            print(f"Error fetching incident {incident_key}: {str(e)}")
            raise 