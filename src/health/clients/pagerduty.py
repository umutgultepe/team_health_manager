from ..dataclass import Incident
from ..config.pagerduty import PAGERDUTY_API_KEY, PAGERDUTY_EMAIL
import requests
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

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

    def get_incidents_for_policy(self, escalation_policy_id: str, 
                               start_time: datetime, 
                               end_time: datetime) -> List[Incident]:
        """
        Get all incidents for an escalation policy within a time range.
        
        Args:
            escalation_policy_id (str): The ID of the escalation policy
            start_time (datetime): Start of the time range
            end_time (datetime): End of the time range
            
        Returns:
            List[Incident]: List of incidents ordered from earliest to latest
            
        Raises:
            requests.exceptions.RequestException: If any API request fails
        """
        try:
            # Get escalation policy details which includes services
            policy_url = f"{self.base_url}/escalation_policies/{escalation_policy_id}"
            params = {
                "include[]": ["services"]
            }
            policy_response = requests.get(policy_url, headers=self.headers, params=params)
            policy_response.raise_for_status()
            policy_data = policy_response.json()
            
            # Extract service IDs from the policy response
            service_ids = [service['id'] for service in policy_data.get('escalation_policy', {}).get('services', [])]
            if not service_ids:
                return []
            
            # Get incidents for all services
            incidents = []
            incidents_url = f"{self.base_url}/incidents"
            params = {
                'service_ids[]': service_ids,
                'since': start_time.isoformat(),
                'until': end_time.isoformat(),
                'include[]': ['assignees', 'users'],
                'sort_by': 'created_at:asc'
            }
            
            # Handle pagination
            while incidents_url:
                incidents_response = requests.get(incidents_url, headers=self.headers, params=params)
                incidents_response.raise_for_status()
                incidents_data = incidents_response.json()
                
                # Process each incident
                for incident_data in incidents_data.get('incidents', []):
                    incidents.append(self._get_incident_with_logs(incident_data))
                
                # Check for more pages
                incidents_url = incidents_data.get('next')
                if incidents_url:
                    # Remove params as they're included in the next URL
                    params = None
            
            return incidents
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching incidents for policy {escalation_policy_id}: {str(e)}")
            raise

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
            
            # Get incident data from response and fetch logs
            return self._get_incident_with_logs(incident_data.get('incident', {}))
            
        except requests.exceptions.RequestException as e:
            # Log the error and re-raise
            print(f"Error fetching incident {incident_key}: {str(e)}")
            raise 

    def _get_incident_with_logs(self, incident_data: Dict[str, Any]) -> Incident:
        """
        Helper method to fetch logs for an incident and construct the Incident object.
        
        Args:
            incident_data (Dict[str, Any]): Raw incident data from the API
            
        Returns:
            Incident: Constructed incident object with logs
            
        Raises:
            requests.exceptions.RequestException: If the log fetch fails
            ValueError: If incident ID is not found in the data
        """
        # Get the incident ID
        incident_id = incident_data.get('id')
        if not incident_id:
            raise ValueError(f"Could not find incident ID in response data")
        
        # Get incident logs
        logs_url = f"{self.base_url}/incidents/{incident_id}/log_entries"
        logs_response = requests.get(logs_url, headers=self.headers)
        logs_response.raise_for_status()
        logs_data = logs_response.json()
        
        # Sort logs by time (earliest first)
        sorted_logs = sorted(logs_data.get("log_entries", []), 
                           key=lambda x: x.get("created_at", ""))
        
        return Incident(
            raw={'incident': incident_data},
            raw_logs=sorted_logs
        )