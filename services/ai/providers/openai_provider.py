import re
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL


class OpenAIProvider:

    def __init__(self):
        if not OPENAI_API_KEY:
            raise Exception("OPENAI_API_KEY not configured")

        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def chat(self, messages):
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages
        )
        
        content = response.choices[0].message.content
        if not content:
            return ""

        # Фильтрация технического мусора
        return self._strip_thinking_tags(content)

    def _strip_thinking_tags(self, text: str) -> str:
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        if '<think>' in text:
            text = text.split('<think>')[0]
        return text.replace('</think>', '').replace('<', '').replace('>', '').strip()