# app/routers/info_router.py
from fastapi import APIRouter
from typing import List, Dict, Any

from ..constants import AGE_GENDER_PROMPTS # Relative import
from ..config import OPENAI_API_KEY # Relative import

router = APIRouter()

@router.get("/age-groups", response_model=List[str])
async def get_age_groups_endpoint():
    return list(AGE_GENDER_PROMPTS.keys())

@router.get("/health")
async def health_check_endpoint():
    api_status = "OK" if OPENAI_API_KEY else "CONFIG_ERROR"
    message = "API đang hoạt động bình thường." if OPENAI_API_KEY else "Lỗi: OPENAI_API_KEY chưa được thiết lập."
    
    return {
        "status": api_status,
        "message": message,
        "langchain_status": "enabled", # Giả định Langchain luôn được kích hoạt nếu API chạy
        "model_in_use": "gpt-4o-mini" # Hoặc lấy từ config nếu có thể thay đổi
    }

@router.get("/")
async def root_endpoint():
    return {
        "api_name": "Sex Education Chatbot API - Powered by GPT-4o-mini",
        "version": "1.0.1", # Cập nhật version nếu cần
        "description": "API cung cấp thông tin về giáo dục giới tính phù hợp với độ tuổi, sử dụng LangChain và GPT-4o-mini. Refactored structure.",
        "documentation": "/docs" # Hoặc /redoc
    }