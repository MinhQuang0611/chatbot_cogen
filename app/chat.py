# app/chat.py
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.chains import LLMChain, conversation
from langchain.prompts import PromptTemplate # Cần import PromptTemplate ở đây nữa


from .schemas import ChatRequest, ChatResponse
from .constants import SENSITIVE_KEYWORDS, AGE_GENDER_PROMPTS
from .greeting import get_greeting_response
from .prompts import is_sex_education_related #, get_age_gender_prompt # get_age_gender_prompt đã ở prompts.py
from .memory import get_conversation_memory
from .llm import get_llm
from .config import OPENAI_API_KEY

def is_content_appropriate(message: str) -> bool: # Bỏ user_age_group vì không dùng
    """get_conversation_memory
    Kiểm tra sự phù hợp của nội dung tin nhắn.
    """
    message_lower = message.lower()
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in message_lower:
            return False
    return True

async def process_message_with_langchain(request: ChatRequest) -> ChatResponse:
    """
    Xử lý tin nhắn của người dùng, bao gồm kiểm tra nội dung,
    chào hỏi, phân loại và tạo phản hồi từ LLM.
    """
    try:
        llm_instance = get_llm()
        memory_instance = get_conversation_memory(request.session_id)

        # Template cho prompt
        base_template_str = AGE_GENDER_PROMPTS.get(request.user_age_group, {}).get(request.user_gender) or \
                            AGE_GENDER_PROMPTS.get(request.user_age_group, {}).get("default") or \
                            AGE_GENDER_PROMPTS.get("adult", {}).get("default")

        # Cấu trúc prompt
        prompt = PromptTemplate(
            input_variables=["history", "question"],
            template=base_template_str
        )

        # Hàm callback để lấy lịch sử
        async def get_session_history():
            memory = get_conversation_memory(request.session_id)
            # Sử dụng `aget_messages()` để lấy danh sách tin nhắn
            messages = await memory.load_memory_variables()
            return messages

        # Tạo chain mới
        chain = RunnableWithMessageHistory(
            runnable=llm_instance,
            get_session_history=get_session_history,
            prompt=prompt
        )

        # Gửi tin nhắn và nhận phản hồi
        response_text = await chain.ainvoke({"question": request.message})

        return ChatResponse(
            response=response_text,
            appropriate=True,
            is_sex_education_related=True
        )

    except Exception as e:
        print(f"Error in Langchain processing: {str(e)}")
        return ChatResponse(
            response=f"Đã xảy ra lỗi khi xử lý yêu cầu của bạn: {str(e)}",
            appropriate=True,
            is_sex_education_related=True
        )