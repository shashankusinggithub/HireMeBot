from .base_provider import BaseLLMProvider
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name="gpt-3.5-turbo", temperature=0.7):
        super().__init__()
        self.llm = ChatOpenAI(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=1024,
        )

    def _get_llm_response(self, prompt: str, system_message: str = None) -> str:
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))

        response = self.llm.invoke(messages)
        return response.content
