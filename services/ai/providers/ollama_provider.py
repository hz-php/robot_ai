import ollama

from config import OLLAMA_TEXT_MODEL


class OllamaProvider:

    def chat(self, messages):

        response = ollama.chat(
            model=OLLAMA_TEXT_MODEL,
            messages=messages
        )

        return response["message"]["content"]