import ollama


class Brain:

    def __init__(self, username="Unknown"):

        self.username = username
        self.history = []

        self.history.append({
            "role": "system",
            "content": (
                f"Ты AI-ассистент уровня ChatGPT. "
                f"Обращайся к пользователю по имени {username}. "
                f"Ты НЕ выполняешь команды напрямую. "
                f"Ты можешь вернуть TOOL JSON если нужно действие. "
                f"Иначе отвечай как обычный ассистент, дружелюбно, на русском языке."
            )
        })

    # =========================
    # SET USER NAME
    # =========================
    def set_username(self, username):
        """Обновление имени пользователя"""
        
        self.username = username
        
        # Обновляем system prompt с новым именем
        self.history[0] = {
            "role": "system",
            "content": (
                f"Ты AI-ассистент уровня ChatGPT. "
                f"Обращайся к пользователю по имени {username}. "
                f"Ты НЕ выполняешь команды напрямую. "
                f"Ты можешь вернуть TOOL JSON если нужно действие. "
                f"Иначе отвечай как обычный ассистент, дружелюбно, на русском языке."
            )
        }

    # =========================
    # THINK
    # =========================
    def think(self, user_text, telemetry):

        message = {
            "role": "user",
            "content": f"""
Пользователь {self.username}: {user_text}
Телеметрия: {telemetry}

Если нужна команда — верни JSON:
{{
  "tool": "take_photo"
}}

Иначе просто ответ на русском.
"""
        }

        self.history.append(message)

        response = ollama.chat(
            model="llama3",
            messages=self.history
        )

        return response["message"]["content"]