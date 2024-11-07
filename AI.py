from typing import List
from llm_providers import OllamaProvider, GeminiProvider, LLMProviderFactory
import os
from dotenv import load_dotenv
import random

load_dotenv()

# Add more keys if you want to.
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


# Uncomment if you have set up ollama
# ollama_llm = LLMProviderFactory.create_provider(
#     provider_type="ollama",
#     model_name="gemma2",
# )


def get_result(job_description: str, company: str = "") -> dict:
    return llm.get_result(job_description, company)


def get_answers(question: str, options: List[dict] = None) -> dict:
    return llm.get_answers(question, options)
