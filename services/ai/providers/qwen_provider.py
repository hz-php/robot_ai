import re
from openai import OpenAI
from config import QWEN_API_KEY, QWEN_MODEL, QWEN_API_URL


class QwenAiProvider:

    def __init__(self):
        if not QWEN_API_KEY:
            raise Exception("QWEN_API_KEY not configured in config.py")

        self.client = OpenAI(
            api_key=QWEN_API_KEY,
            base_url=QWEN_API_URL
        )

    def chat(self, messages):
        try:
            response = self.client.chat.completions.create(
                model=QWEN_MODEL,
                messages=messages
            )
            
            content = response.choices[0].message.content
            if not content:
                return ""

            # 🔥 Чистим текст от мыслей и системных ID
            cleaned_content = self._clean_response(content)
            return cleaned_content
            
        except Exception as e:
            print(f"[QWEN ERROR] API call failed: {e}")
            return f"Ошибка ИИ-агента (Qwen): {e}"

    def _clean_response(self, text: str) -> str:
        # 1. Удаляем парные теги рассуждений <think>...</think>
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        if '<think>' in text:
            text = text.split('<think>')[0]
        text = text.replace('</think>', '')

        # 2. 🔥 Вырезаем блок логирования <details>...</details> вместе с Response ID
        text = re.sub(r'<details>.*?</details>', '', text, flags=re.DOTALL)
        
        # 3. На всякий случай убираем одиночные незакрытые теги details, если они оборвались
        if '<details>' in text:
            text = text.split('<details>')[0]

        return text.strip()