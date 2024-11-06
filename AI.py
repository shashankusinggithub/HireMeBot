from typing import List
from llm_providers import OllamaProvider, GeminiProvider, LLMProviderFactory
import os
from dotenv import load_dotenv
import random

load_dotenv()
api_keys = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY2"),
    os.getenv("GEMINI_API_KEY3"),
]

api_key = random.choice(api_keys)
llm = LLMProviderFactory.create_provider(
    provider_type="gemini",
    api_key=api_key,
    model_name="gemini-1.5-flash",
)
ollama_llm = LLMProviderFactory.create_provider(
    provider_type="ollama",
    model_name="llama3.2",
)


def get_result(job_description: str, company: str = "") -> dict:
    return ollama_llm.get_result(job_description, company)


def get_answers(question: str, options: List[dict] = None) -> dict:
    return llm.get_answers(question, options)
