# app/routers/chat_router.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List

from ..schemas import ChatRequest, ChatResponse # Relative imports
from ..chat import process_message_with_langchain
from ..memory import clear_session_memory, get_all_memories_keys # Thêm get_all_memories_keys để debug (tùy chọn)
from ..constants import AGE_GENDER_PROMPTS # Để lấy danh sách age_groups

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def handle_chat(request_data: ChatRequest):
    # Kiểm tra độ tuổi hợp lệ (đã có trong schema rồi, nhưng check lại ở đây cũng tốt)
    if request_data.user_age_group not in AGE_GENDER_PROMPTS:
        raise HTTPException(status_code=400, detail="Độ tuổi không hợp lệ. Vui lòng chọn một trong các giá trị hợp lệ.")
    
    return await process_message_with_langchain(request_data)

@router.delete("/clear-memory/{session_id}")
async def clear_memory_endpoint(session_id: str):
    if clear_session_memory(session_id):
        return {"status": "success", "message": f"Đã xóa bộ nhớ hội thoại cho session {session_id}"}
    else:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy session {session_id}")

# (Tùy chọn) Endpoint để xem các session đang có trong memory (dùng để debug)
# @router.get("/active-sessions")
# async def list_active_sessions():
#     return {"active_session_ids": get_all_memories_keys()}