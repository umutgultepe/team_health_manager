from google import genai
import json
import requests
from ..config.credentials import GOOGLE_AI_KEY, OPENAI_API_KEY, OPENAI_HOST


MODELS = {
    "gpt4o_global": "gpt-4o-2024-05-13",
    "gpt4.1_global": "gpt-4.1-2025-04-14",
    "gpt4.1-mini_global": "gpt-4.1-mini-2025-04-14",
    "gpt4.1-nano_global": "gpt-4.1-nano-2025-04-14",
    "o3_global": "o3-2025-04-16",
    "o4-mini_global": "o4-mini-2025-04-16"
}

class AIClient:
    def __init__(self):
        self.gemini_client = genai.Client(api_key=GOOGLE_AI_KEY)

    def call_api(self, prompt: str) -> str:
        return self._call_openai(prompt)

    def _call_openai(self, prompt: str) -> str:
        model_key = "gpt4o_global"
        url = f"{OPENAI_HOST}/deployments/gpt4o_global/chat/completions"
        response = requests.post(
            url,
            params={"api-version": "2024-02-01"},
            headers={
                "Content-Type": "application/json",
                "api-key": OPENAI_API_KEY
            },
            json={
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "model": MODELS[model_key],
                "max_tokens": 4096
            }
        )
        content = response.json()
        try:
            return content["choices"][0]["message"]["content"]
        except KeyError as e:
            raise Exception(f"Error calling OpenAI API: {response.content}")


    def _call_gemini(self, prompt: str) -> str:
        response = self.gemini_client.models.generate_content(
            model="gemini-2.0-flash",  
            contents=prompt,
        )
        return response.text