# providers/factory.py
from typing import Optional, Union
from .base_provider import BaseLLMProvider
from .opennAI_provider import OpenAIProvider
from .ollama_provider import OllamaProvider
from .gemini_provider import GeminiProvider


class LLMProviderFactory:
    @staticmethod
    def create_provider(
        provider_type: str,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> BaseLLMProvider:
        """
        Create and return an LLM provider instance based on the specified type.

        Args:
            provider_type: Type of provider ('openai', 'ollama', or 'gemini')
            api_key: API key for providers that require it
            model_name: Optional model name to use

        Returns:
            An instance of the specified LLM provider
        """
        provider_type = provider_type.lower()

        if provider_type == "openai":
            if not api_key:
                raise ValueError("OpenAI provider requires an API key")
            return OpenAIProvider(
                api_key=api_key, model_name=model_name or "gpt-3.5-turbo"
            )

        elif provider_type == "ollama":
            return OllamaProvider(model_name=model_name or "gemma2")

        elif provider_type == "gemini":
            if not api_key:
                raise ValueError("Gemini provider requires an API key")
            return GeminiProvider(
                api_key=api_key, model_name=model_name or "gemini-pro"
            )

        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
