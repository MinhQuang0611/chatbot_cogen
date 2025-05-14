# app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

class ChatRequest(BaseModel):
    message: str
    user_age_group: str  # 'child', 'teen', 'adult', 'parent'
    user_gender: Literal["male", "female"]
    context: Optional[List[Dict[str, str]]] = []
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    appropriate: bool
    is_sex_education_related: bool = True

class CheckRelatedResponse(BaseModel):
    is_sex_education_related : bool = Field(
        ..., description= "Câu hỏi có liên quan tới chủ đề giáo dục giới tính không, nếu có trả về True và và False nếu ngược lại"
    )
    reason: str  = Field (
        ..., description= "Lý do tại sao lại có kết quả như thế"
    )