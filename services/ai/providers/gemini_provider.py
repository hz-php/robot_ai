import re
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL


class GeminiProvider:

    def __init__(self):
        if not GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY not configured")
            
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def chat(self, messages):
        # Конвертируем историю под формат Gemini (роли user/model)
        gemini_history = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            if msg["role"] == "system":
                # В Gemini системный промпт обычно задается при инициализации модели, 
                # но для простоты перекинем его как первый юзер-месседж, если провайдер stateless
                role = "user"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        # Берем последнее сообщение как текущий запрос
        current_prompt = gemini_history[-1]["parts"][0]
        
        response = self.model.generate_content(current_prompt)
        content = response.text
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