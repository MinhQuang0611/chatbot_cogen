# app/memory.py
from langchain.memory import ConversationBufferMemory
from typing import Dict

# Dictionary to store conversation memories
_conversation_memories = {}

def get_conversation_memory(session_id: str) -> ConversationBufferMemory:
    """
    Lấy ConversationBufferMemory theo session_id.
    Nếu chưa tồn tại, tạo mới.
    """
    if session_id not in _conversation_memories:
        _conversation_memories[session_id] = ConversationBufferMemory(
            memory_key="history",
            return_messages=True  # Đảm bảo trả về messages thay vì văn bản thông thường
        )
    return _conversation_memories[session_id]

def clear_session_memory(session_id: str) -> bool:
    """
    Xóa bộ nhớ hội thoại cho một session_id.
    Trả về True nếu xóa thành công, False nếu không tìm thấy session.
    """
    if session_id in _conversation_memories:
        del _conversation_memories[session_id]
        return True
    return False

def get_all_memories_keys() -> list:
    """Trả về danh sách các session_id đang có trong bộ nhớ."""
    return list(_conversation_memories.keys())