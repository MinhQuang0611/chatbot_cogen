# app/greeting.py
from typing import Tuple, Optional, Dict
from .constants import GREETING_KEYWORDS, GREETING_RESPONSES # Relative import

def is_greeting(message: str) -> Tuple[bool, str]:
    """
    Kiểm tra xem tin nhắn có phải là lời chào hỏi không.
    Return: (is_greeting, greeting_type)
    """
    message_lower = message.lower().strip()
    
    for greeting_type, phrases in GREETING_KEYWORDS.items():
        for phrase in phrases:
            if phrase in message_lower:
                return True, greeting_type
    
    return False, ""

def get_greeting_response(message: str, user_age_group: str) -> Optional[Dict[str, any]]:
    """
    Trả về câu trả lời chào hỏi phù hợp với độ tuổi của người dùng.
    """
    is_greet, greeting_type = is_greeting(message)
    
    age_group_responses = GREETING_RESPONSES.get(user_age_group)
    if is_greet and age_group_responses and greeting_type in age_group_responses:
        response_text = age_group_responses[greeting_type]
        return {
            "response": response_text,
            "appropriate": True,
            "is_sex_education_related": True  # Để chatbot không từ chối trả lời chào hỏi
        }
    
    return None