from config import AI_PROVIDER

from ai.providers.ollama_provider import OllamaProvider
from ai.providers.groq_provider import GroqProvider


def get_provider():

    if AI_PROVIDER == "groq":
        return GroqProvider()

    return OllamaProvider()