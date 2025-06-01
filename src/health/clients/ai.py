from google import genai
from ..config.credentials import GOOGLE_AI_KEY

class AIClient:
    def __init__(self):
        self.client = genai.Client(api_key=GOOGLE_AI_KEY)

    def call_api(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",  
            contents=prompt,
        )
        return response.text