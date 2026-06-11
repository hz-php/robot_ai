import ollama


class Brain:

    def __init__(self):

        self.history = []

        self.history.append({
            "role": "system",
            "content": (
                "Ты AI-ассистент уровня ChatGPT. "
                "Ты НЕ выполняешь команды напрямую. "
                "Ты можешь вернуть TOOL JSON если нужно действие. "
                "Иначе отвечай как обычный ассистент."
            )
        })

    # =========================
    # THINK
    # =========================
    def think(self, user_text, telemetry):

        message = {
            "role": "user",
            "content": f"""
Пользователь: {user_text}
Телеметрия: {telemetry}

Если нужна команда — верни JSON:
{{
  "tool": "take_photo"
}}

Иначе просто ответ.
"""
        }

        self.history.append(message)

        response = ollama.chat(
            model="llama3",
            messages=self.history
        )

        return response["message"]["content"]