# providers/gemini_provider.py
from .base_provider import BaseLLMProvider
import google.generativeai as genai
from google.generativeai.types import ContentType


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name="gemini-pro"):
        super().__init__()
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def _get_llm_response(self, prompt: str, system_message: str = None) -> str:
        # Combine system message and prompt for Gemini
        if system_message:
            full_prompt = f"{system_message}\n\nUser: {prompt}\n\nAssistant:"
        else:
            full_prompt = prompt

        chat = self.model.start_chat(history=[])
        response = chat.send_message(
            full_prompt,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1024,
            },
        )
        return response.text

    def _format_chat_history(self, messages):
        formatted_messages = []
        for message in messages:
            if message["role"] == "system":
                formatted_messages.append(
                    {"role": "user", "parts": [message["content"]]}
                )
                formatted_messages.append(
                    {"role": "model", "parts": ["Understood, I will act as specified."]}
                )
            else:
                formatted_messages.append(
                    {
                        "role": "user" if message["role"] == "user" else "model",
                        "parts": [message["content"]],
                    }
                )
        return formatted_messages
