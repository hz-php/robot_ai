import re
from anthropic import Anthropic
from config import CLAUDE_API_KEY, CLAUDE_MODEL


class ClaudeProvider:

    def __init__(self):
        if not CLAUDE_API_KEY:
            raise Exception("CLAUDE_API_KEY not configured")

        self.client = Anthropic(api_key=CLAUDE_API_KEY)

    def chat(self, messages):
        # Выделяем системный промпт, так как Anthropic принимает его отдельным параметром
        system_prompt = ""
        filtered_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                filtered_messages.append({"role": msg["role"], "content": msg["content"]})

        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=filtered_messages
        )

        # Собираем текст из блоков ответа
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        if not content:
            return ""

        # 🔥 Очистка от <think>...</think>
        cleaned_content = self._strip_thinking_tags(content)
        return cleaned_content

    def _strip_thinking_tags(self, text: str) -> str:
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        if '<think>' in text:
            text = text.split('<think>')[0]
        return text.replace('</think>', '').replace('<', '').replace('>', '').strip()