import re
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL


class GroqProvider:

    def __init__(self):
        if not GROQ_API_KEY:
            raise Exception("GROQ_API_KEY not configured")

        self.client = Groq(api_key=GROQ_API_KEY)

    def chat(self, messages):
        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages
        )
        
        content = response.choices[0].message.content
        if not content:
            return ""

        # 🔥 Очистка от <think>...</think>
        cleaned_content = self._strip_thinking_tags(content)
        return cleaned_content

    def _strip_thinking_tags(self, text: str) -> str:
        # Удаляем парные теги вместе с их содержимым
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Если тег <think> открылся, но не закрылся (модель оборвала мысль)
        if '<think>' in text:
            text = text.split('<think>')[0]
        # На всякий случай чистим одиночные плавающие теги и скобки
        text = text.replace('</think>', '').replace('<', '').replace('>', '')
        return text.strip()