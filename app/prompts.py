# aget_messages/prompts.py
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from .schemas import CheckRelatedResponse # Sử dụng relative import
from .llm import get_classification_llm # Sử dụng relative import
from .config import OPENAI_API_KEY # Sử dụng relative import

# --- Sex Education Classification ---
CHECK_RELATED_PARSER = PydanticOutputParser(pydantic_object=CheckRelatedResponse)

CHECK_RELATED_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Bạn cần phân loại câu hỏi của người dùng xem có liên quan đến giáo dục giới tính hay không.
            Các chủ đề liên quan đến giáo dục giới tính bao gồm nhưng không giới hạn:
            1. Cơ thể con người và sự phát triển (dậy thì, các bộ phận cơ thể, thay đổi cơ thể)
            2. Sức khỏe sinh sản (kinh nguyệt, mãn kinh, tinh hoàn, xuất tinh, sức khỏe tuyến tiền liệt)
            3. Mối quan hệ tình cảm và tình dục (mối quan hệ lành mạnh, đồng thuận, giao tiếp)
            4. Bệnh lây truyền qua đường tình dục (HIV/AIDS, bệnh lây qua đường tình dục, phòng ngừa)
            5. Phương pháp tránh thai và kế hoạch hóa gia đình
            6. Định hướng tính dục và bản dạng giới
            7. Vấn đề ranh giới cá nhân và tôn trọng

            Hãy xác định xem câu hỏi có thuộc về các chủ đề trên không.
            Trả về JSON với định dạng:
            {format_instructions}
            """
        ),
        ("human", "Câu hỏi của người dùng: {question}")
    ]
).partial(format_instructions=CHECK_RELATED_PARSER.get_format_instructions())


async def is_sex_education_related(message: str) -> dict:
    """
    Xác định xem câu hỏi có liên quan đến giáo dục giới tính không sử dụng LLM.
    """
    if not OPENAI_API_KEY: # Kiểm tra API key trước khi gọi LLM
        # Trả về mặc định là có liên quan để đi tiếp, hoặc xử lý lỗi cụ thể hơn
        print("Warning: OPENAI_API_KEY is not set. Assuming message is sex-education related.")
        return {"is_sex_education_related": True, "reason": "OPENAI_API_KEY not configured, bypassed check."}

    llm = get_classification_llm() # Lấy LLM từ llm.py
    try:
        chain = CHECK_RELATED_PROMPT_TEMPLATE | llm | CHECK_RELATED_PARSER
        response = await chain.ainvoke({"question": message}) # Sử dụng ainject cho async
        return response.model_dump()
    except Exception as e:
        print(f"Error in check_related: {e}")
        # Trong trường hợp lỗi, giả định là có liên quan để chatbot vẫn cố gắng trả lời
        return {"is_sex_education_related": True, "reason": f"Error during classification: {str(e)}"}

# --- Age/Gender Specific Prompts ---
# Các template này được định nghĩa trong constants.py
# Hàm này sẽ giúp tạo PromptTemplate object từ string trong constants
def get_age_gender_prompt(user_age_group: str, user_gender: str, prompts_dict: dict) -> PromptTemplate:
    """
    Lấy và tạo PromptTemplate dựa trên nhóm tuổi và giới tính.
    """
    template_str = prompts_dict.get(user_age_group, {}).get(user_gender) or \
                   prompts_dict.get(user_age_group, {}).get("default")

    if not template_str:
        # Fallback nếu có lỗi không tìm thấy prompt (dù không nên xảy ra nếu constants đúng)
        template_str = prompts_dict.get("adult", {}).get("default") # Ví dụ fallback

    return PromptTemplate(
        input_variables=["question", "history"], # Thêm history nếu ConversationChain dùng
        template=template_str
    )