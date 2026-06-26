import re
from openai import OpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL


class OpenRouterProvider:

    def __init__(self):
        if not OPENROUTER_API_KEY:
            raise Exception("OPENROUTER_API_KEY not configured")

        # Подключаемся к эндпоинту OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )

    def chat(self, messages):
        response = self.client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=messages
        )
        
        content = response.choices[0].message.content
        if not content:
            return ""

        # Очистка вывода от рассуждений нейросети
        return self._strip_thinking_tags(content)

    def _strip_thinking_tags(self, text: str) -> str:
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        if '<think>' in text:
            text = text.split('<think>')[0]
        return text.replace('</think>', '').replace('<', '').replace('>', '').strip()