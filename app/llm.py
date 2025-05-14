# app/llm.py
from langchain_openai import ChatOpenAI
from .config import OPENAI_API_KEY

def get_llm(temperature: float = 0.7, model: str = "gpt-4o-mini") -> ChatOpenAI:
    """Khởi tạo và trả về một instance của ChatOpenAI."""
    return ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model=model,
        temperature=temperature
    )

def get_classification_llm(temperature: float = 0.1, model: str = "gpt-4o-mini") -> ChatOpenAI:
    """Khởi tạo LLM cho mục đích phân loại, thường với temperature thấp hơn."""
    return ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model=model,
        temperature=temperature
    )