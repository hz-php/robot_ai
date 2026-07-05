from config import AI_PROVIDER

from services.ai.providers.ollama_provider import OllamaProvider
from services.ai.providers.groq_provider import GroqProvider
from services.ai.providers.openai_provider import OpenAIProvider
from services.ai.providers.openrouter_provider import OpenRouterProvider
from services.ai.providers.qwen_provider import QwenAiProvider


def get_provider():

    if AI_PROVIDER == "ollama":
        return OllamaProvider()
    
    if AI_PROVIDER == "openai":
        return OpenAIProvider()
    
    if AI_PROVIDER == "groq":
        return GroqProvider()

    if AI_PROVIDER == "openrouter":
        return OpenRouterProvider()
    
    if AI_PROVIDER == "qwen":
        return QwenAiProvider()
    
    
    raise Exception(
        f"Unknown AI_PROVIDER: {AI_PROVIDER}"
    )