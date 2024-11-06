from .base_provider import BaseLLMProvider
from langchain_ollama import OllamaLLM


class OllamaProvider(BaseLLMProvider):
    def __init__(self, model_name="gemma2", temperature=0.7):
        super().__init__()
        self.llm = OllamaLLM(
            model=model_name,
            temperature=temperature,
            num_ctx=2048,  # Context window size
            num_predict=1024,  # Max tokens to generate
            top_k=40,
            top_p=0.8,
            repeat_penalty=1.1,
        )

    def _get_llm_response(self, prompt: str, system_message: str = None) -> str:
        if system_message:
            formatted_prompt = f"""<s>system
{system_message}
</s>
<s>user
{prompt}
</s>
<s>assistant
"""
        else:
            formatted_prompt = prompt

        return self.llm.invoke(formatted_prompt)
