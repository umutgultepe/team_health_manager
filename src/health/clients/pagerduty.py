from ..dataclass import Incident, PagerDutyStats
from ..config.credentials import PAGERDUTY_API_KEY, PAGERDUTY_EMAIL
import requests
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

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
            offset = 0
            limit = 100
            
            while True:
                params = {
                    'service_ids[]': service_ids,
                    'since': start_time.isoformat(),
                    'until': end_time.isoformat(),
                    'include[]': ['assignees', 'users'],
                    'sort_by': 'created_at:asc',
                    'offset': offset,
                    'limit': limit
                }
                
                incidents_response = requests.get(incidents_url, headers=self.headers, params=params)
                incidents_response.raise_for_status()
                incidents_data = incidents_response.json()
                
                # Process each incident
                for incident_data in incidents_data.get('incidents', []):
                    incidents.append(self._get_incident_with_logs(incident_data))
                
                # Check if there are more pages
                if not incidents_data.get('more', False):
                    break
                
                # Update offset for next page
                offset += limit
            
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

    def policy_statistics(
        self,
        escalation_policy_id: str,
        start: datetime,
        end: datetime
    ) -> PagerDutyStats:
        """Calculate statistics for incidents in an escalation policy.
        
        Args:
            escalation_policy_id: ID of the escalation policy
            start: Start time in UTC
            end: End time in UTC
            
        Returns:
            PagerDutyStats object containing the statistics
        """
        # Get all incidents
        incidents = self.get_incidents_for_policy(escalation_policy_id, start, end)
        
        if not incidents:
            return PagerDutyStats(
                total_incidents=0,
                high_urgency_incidents=0,
                auto_resolved=0,
                timed_out=0,
                mean_time_to_acknowledgement=None,
                total_response_time=timedelta()
            )
        
        # Calculate statistics
        total_incidents = len(incidents)
        auto_resolved = sum(1 for i in incidents if i.resolution_type == "AUTO")
        timed_out = sum(1 for i in incidents if i.timed_out)
        high_urgency_incidents = sum(1 for i in incidents if i.high_urgency)
        # Calculate mean time to acknowledgment
        acknowledgment_times = [i.time_to_acknowledgement for i in incidents if i.high_urgency and i.time_to_acknowledgement is not None]
        mean_time_to_ack = sum(acknowledgment_times, timedelta()) / len(acknowledgment_times) if acknowledgment_times else None
        
        # Calculate total response time
        # Sort incidents by creation time
        sorted_incidents = sorted(incidents, key=lambda x: x.created)
        total_response_time = timedelta()
        current_end = start
        
        for incident in sorted_incidents:
            # If incident started after current_end, add gap to total
            if incident.created > current_end:
                total_response_time += incident.created - current_end
            
            # Update current_end to the later of:
            # - current_end
            # - incident's resolved time (or end if not resolved)
            resolved_time = incident.resolved_time if incident.resolved_time else end
            current_end = max(current_end, resolved_time)
        
        # Add any remaining time after the last incident
        if current_end < end:
            total_response_time += end - current_end
        
        return PagerDutyStats(
            total_incidents=total_incidents,
            auto_resolved=auto_resolved,
            timed_out=timed_out,
            high_urgency_incidents=high_urgency_incidents,
            mean_time_to_acknowledgement=mean_time_to_ack,
            total_response_time=total_response_time
        )