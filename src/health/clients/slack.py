import os
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from ..config.credentials import SLACK_BOT_TOKEN

class SlackClient:
    def __init__(self):
        """Initialize Slack client with API token from environment."""
        token = os.getenv('SLACK_BOT_TOKEN') or SLACK_BOT_TOKEN
        if not token:
            raise ValueError("SLACK_BOT_TOKEN not found in environment or config")
        self.client = WebClient(token=token)

    def get_channel_id(self, channel_name: str) -> str:
        """Get channel ID from channel name."""
        try:
            # Remove # if present at the start of channel name
            channel_name = channel_name.lstrip('#')
            
            # Try to find the channel
            response = self.client.conversations_list()
            for channel in response['channels']:
                if channel['name'] == channel_name:
                    return channel['id']
            
            raise ValueError(f"Channel '{channel_name}' not found")
        except SlackApiError as e:
            raise Exception(f"Error getting channel ID: {str(e)}")

    def get_messages(self, channel: str, start_time: datetime, end_time: datetime) -> list:
        """
        Get messages from a Slack channel within the specified time range.
        
        Args:
            channel (str): Channel name or ID
            start_time (datetime): Start time in UTC
            end_time (datetime): End time in UTC
            
        Returns:
            list: List of message objects
        """
        try:
            # Get channel ID if channel name is provided
            channel_id = channel if channel.startswith('C') else self.get_channel_id(channel)
            
            # Convert datetime to Unix timestamp
            oldest = start_time.timestamp()
            latest = end_time.timestamp()
            
            messages = []
            # Handle pagination
            next_cursor = None
            
            while True:
                response = self.client.conversations_history(
                    channel=channel_id,
                    oldest=str(oldest),
                    latest=str(latest),
                    limit=100,  # Max messages per request
                    cursor=next_cursor
                )
                
                messages.extend(response['messages'])
                
                # Check if there are more messages
                if not response['has_more']:
                    break
                    
                next_cursor = response['response_metadata']['next_cursor']
            
            return messages
            
        except SlackApiError as e:
            raise Exception(f"Error fetching messages: {str(e)}")

    def get_user_info(self, user_id: str) -> dict:
        """Get user information by user ID."""
        try:
            response = self.client.users_info(user=user_id)
            return response['user']
        except SlackApiError as e:
            raise Exception(f"Error fetching user info: {str(e)}")

    def post_message(self, channel: str, text: str, thread_ts: str = None) -> dict:
        """
        Post a message to a Slack channel.
        
        Args:
            channel (str): Channel name or ID
            text (str): Message text
            thread_ts (str, optional): Thread timestamp to reply to
            
        Returns:
            dict: Response from Slack API
        """
        try:
            # Get channel ID if channel name is provided
            channel_id = channel if channel.startswith('C') else self.get_channel_id(channel)
            
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=text,
                thread_ts=thread_ts
            )
            return response
            
        except SlackApiError as e:
            raise Exception(f"Error posting message: {str(e)}") 