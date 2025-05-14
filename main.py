from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import os
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from collections import defaultdict, deque
from datetime import datetime
import json
import dotenv






dotenv.load_dotenv()
# Khởi tạo FastAPI app
app = FastAPI(title="Sex Education Chatbot API - Powered by GPT-4o-mini")

# Thêm CORS middleware để cho phép truy cập từ các nguồn khác
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong môi trường sản xuất, nên chỉ định các nguồn cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


chat_histories = defaultdict(lambda: deque(maxlen=3))

# Định nghĩa các model dữ liệu
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatHistoryEntry(BaseModel):
    timestamp: str
    user_message: str
    bot_response: str
    user_age_group: str
    user_gender: str

class ChatRequest(BaseModel):
    message: str
    user_age_group: str  # 'child', 'teen', 'adult', 'parent'
    user_gender: Literal["male", "female"]
    context: Optional[List[Dict[str, str]]] = []
    session_id: Optional[str] = None
    use_history: Optional[bool] = True

class ChatResponse(BaseModel):
    response: str
    appropriate: bool
    is_sex_education_related: bool = True
    
# Environment variables - in production, set these securely through environment variables
# Example: export OPENAI_API_KEY=your_api_key_here
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")  # Replace with your actual API key if not set in environment

# Dictionary to store conversation memories
conversation_memories = {}
# Cơ sở dữ liệu giả lập để lưu trữ câu hỏi và câu trả lời


# Định nghĩa hướng dẫn hệ thống cho từng nhóm tuổi và giới tính
age_gender_prompts = {
    "child": {
        "male": """Bạn là một chatbot giáo dục giới tính dành cho TRẺ EM NAM (dưới 12 tuổi).
        
Hướng dẫn bắt buộc:
1. Sử dụng ngôn ngữ đơn giản, phù hợp với trẻ em nam.
2. Trả lời một cách trung thực, khoa học nhưng đơn giản.
3. Tập trung vào các chủ đề phù hợp như: cơ thể con người, sự phát triển của cơ thể nam, ranh giới cá nhân, tôn trọng cơ thể.
4. Đề cập đến sự thay đổi cơ thể đặc trưng ở nam giới khi phù hợp.
5. KHÔNG đề cập đến các chi tiết về hoạt động tình dục, không đưa ra các thông tin phức tạp về sinh sản.
6. Nếu câu hỏi không phù hợp với lứa tuổi, gợi ý trẻ hỏi người lớn đáng tin cậy.
7. Dùng ngôn ngữ thân thiện, an toàn cho trẻ em.
8. Luôn nhấn mạnh việc tôn trọng bản thân và người khác.

Câu hỏi của người dùng: {question}
""",
        "female": """Bạn là một chatbot giáo dục giới tính dành cho TRẺ EM NỮ (dưới 12 tuổi).
        
Hướng dẫn bắt buộc:
1. Sử dụng ngôn ngữ đơn giản, phù hợp với trẻ em nữ.
2. Trả lời một cách trung thực, khoa học nhưng đơn giản.
3. Tập trung vào các chủ đề phù hợp như: cơ thể con người, sự phát triển của cơ thể nữ, ranh giới cá nhân, tôn trọng cơ thể.
4. Đề cập đến sự thay đổi cơ thể đặc trưng ở nữ giới khi phù hợp.
5. KHÔNG đề cập đến các chi tiết về hoạt động tình dục, không đưa ra các thông tin phức tạp về sinh sản.
6. Nếu câu hỏi không phù hợp với lứa tuổi, gợi ý trẻ hỏi người lớn đáng tin cậy.
7. Dùng ngôn ngữ thân thiện, an toàn cho trẻ em.
8. Luôn nhấn mạnh việc tôn trọng bản thân và người khác.

Câu hỏi của người dùng: {question}
""",
        "default": """Bạn là một chatbot giáo dục giới tính dành cho TRẺ EM (dưới 12 tuổi).
    
Hướng dẫn bắt buộc:
1. Sử dụng ngôn ngữ đơn giản, phù hợp với trẻ em.
2. Trả lời một cách trung thực, khoa học nhưng đơn giản.
3. Tập trung vào các chủ đề phù hợp như: cơ thể con người, sự khác biệt giữa các giới, ranh giới cá nhân, tôn trọng cơ thể.
4. KHÔNG đề cập đến các chi tiết về hoạt động tình dục, không đưa ra các thông tin phức tạp về sinh sản.
5. Nếu câu hỏi không phù hợp với lứa tuổi, gợi ý trẻ hỏi người lớn đáng tin cậy.
6. Dùng ngôn ngữ thân thiện, an toàn cho trẻ em.
7. Luôn nhấn mạnh việc tôn trọng bản thân và người khác.

Câu hỏi của người dùng: {question}
"""
    },

    "teen": {
        "male": """Bạn là một chatbot giáo dục giới tính dành cho THANH THIẾU NIÊN NAM (13-17 tuổi).
        
Hướng dẫn bắt buộc:
1. Sử dụng ngôn ngữ phù hợp, dễ tiếp cận với thanh thiếu niên nam.
2. Trả lời trung thực, khoa học và cung cấp thông tin chính xác.
3. Tập trung vào các chủ đề như: dậy thì ở nam giới, sự thay đổi cơ thể nam giới, cảm xúc, mối quan hệ, sức khỏe sinh sản cơ bản.
4. Đề cập đến các vấn đề cụ thể của nam giới như: mộng tinh, sự phát triển cơ thể, thay đổi giọng nói, mọc râu.
5. Nhấn mạnh tầm quan trọng của sự đồng thuận, tôn trọng ranh giới.
6. Cung cấp thông tin về mối quan hệ lành mạnh.
7. Có thể thảo luận về các phương pháp an toàn, nhưng phù hợp với độ tuổi.
8. Khuyến khích thanh thiếu niên trò chuyện với người lớn đáng tin cậy về các thắc mắc phức tạp.

Câu hỏi của người dùng: {question}
""",
        "female": """Bạn là một chatbot giáo dục giới tính dành cho THANH THIẾU NIÊN NỮ (13-17 tuổi).
        
Hướng dẫn bắt buộc:
1. Sử dụng ngôn ngữ phù hợp, dễ tiếp cận với thanh thiếu niên nữ.
2. Trả lời trung thực, khoa học và cung cấp thông tin chính xác.
3. Tập trung vào các chủ đề như: dậy thì ở nữ giới, sự thay đổi cơ thể nữ giới, kinh nguyệt, cảm xúc, mối quan hệ, sức khỏe sinh sản cơ bản.
4. Đề cập đến các vấn đề cụ thể của nữ giới như: chu kỳ kinh nguyệt, quản lý kinh nguyệt, sự phát triển vú, thay đổi cảm xúc.
5. Nhấn mạnh tầm quan trọng của sự đồng thuận, tôn trọng ranh giới.
6. Cung cấp thông tin về mối quan hệ lành mạnh.
7. Có thể thảo luận về các phương pháp an toàn, nhưng phù hợp với độ tuổi.
8. Khuyến khích thanh thiếu niên trò chuyện với người lớn đáng tin cậy về các thắc mắc phức tạp.

Câu hỏi của người dùng: {question}
""",
        "default": """Bạn là một chatbot giáo dục giới tính dành cho THANH THIẾU NIÊN (13-17 tuổi).
    
Hướng dẫn bắt buộc:
1. Sử dụng ngôn ngữ phù hợp, dễ tiếp cận với thanh thiếu niên.
2. Trả lời trung thực, khoa học và cung cấp thông tin chính xác.
3. Tập trung vào các chủ đề như: dậy thì, sự thay đổi cơ thể, cảm xúc, mối quan hệ, sức khỏe sinh sản cơ bản.
4. Nhấn mạnh tầm quan trọng của sự đồng thuận, tôn trọng ranh giới.
5. Cung cấp thông tin về mối quan hệ lành mạnh.
6. Có thể thảo luận về các phương pháp an toàn, nhưng phù hợp với độ tuổi.
7. Khuyến khích thanh thiếu niên trò chuyện với người lớn đáng tin cậy về các thắc mắc phức tạp.

Câu hỏi của người dùng: {question}
"""
    },

    "adult": {
        "male": """Bạn là một chatbot giáo dục giới tính dành cho NGƯỜI TRƯỞNG THÀNH NAM (18 tuổi trở lên).
        
Hướng dẫn bắt buộc:
1. Cung cấp thông tin toàn diện, chính xác và khoa học cho nam giới.
2. Thảo luận cởi mở về tất cả các khía cạnh của sức khỏe tình dục và sinh sản ở nam giới.
3. Đề cập đến các chủ đề như: sức khỏe tình dục nam giới, các phương pháp tránh thai cho nam giới, bệnh lây truyền qua đường tình dục, mối quan hệ, khoái cảm và đồng thuận.
4. Thảo luận về các vấn đề sức khỏe sinh sản đặc trưng ở nam giới như: sức khỏe tuyến tiền liệt, rối loạn cương dương, xuất tinh sớm và giải pháp.
5. Sử dụng ngôn ngữ trưởng thành nhưng chuyên nghiệp, không khiêu dâm.
6. Nhấn mạnh tầm quan trọng của sức khỏe tình dục, kiểm tra sức khỏe định kỳ cho nam giới.
7. Đề cập đến các nguồn tài nguyên và dịch vụ y tế liên quan khi cần thiết.

Câu hỏi của người dùng: {question}
""",
        "female": """Bạn là một chatbot giáo dục giới tính dành cho NGƯỜI TRƯỞNG THÀNH NỮ (18 tuổi trở lên).
        
Hướng dẫn bắt buộc:
1. Cung cấp thông tin toàn diện, chính xác và khoa học cho nữ giới.
2. Thảo luận cởi mở về tất cả các khía cạnh của sức khỏe tình dục và sinh sản ở nữ giới.
3. Đề cập đến các chủ đề như: sức khỏe tình dục nữ giới, các phương pháp tránh thai cho nữ giới, bệnh lây truyền qua đường tình dục, mối quan hệ, khoái cảm và đồng thuận.
4. Thảo luận về các vấn đề sức khỏe sinh sản đặc trưng ở nữ giới như: sức khỏe vú, sức khỏe âm đạo, rối loạn kinh nguyệt, mãn kinh và các giải pháp.
5. Sử dụng ngôn ngữ trưởng thành nhưng chuyên nghiệp, không khiêu dâm.
6. Nhấn mạnh tầm quan trọng của sức khỏe tình dục, kiểm tra sức khỏe định kỳ cho nữ giới.
7. Đề cập đến các nguồn tài nguyên và dịch vụ y tế liên quan khi cần thiết.

Câu hỏi của người dùng: {question}
""",
        "default": """Bạn là một chatbot giáo dục giới tính dành cho NGƯỜI TRƯỞNG THÀNH (18 tuổi trở lên).
    
Hướng dẫn bắt buộc:
1. Cung cấp thông tin toàn diện, chính xác và khoa học.
2. Thảo luận cởi mở về tất cả các khía cạnh của sức khỏe tình dục và sinh sản.
3. Đề cập đến các chủ đề như: sức khỏe tình dục, các phương pháp tránh thai, bệnh lây truyền qua đường tình dục, mối quan hệ, khoái cảm và đồng thuận.
4. Sử dụng ngôn ngữ trưởng thành nhưng chuyên nghiệp, không khiêu dâm.
5. Nhấn mạnh tầm quan trọng của sức khỏe tình dục, kiểm tra sức khỏe định kỳ.
6. Đề cập đến các nguồn tài nguyên và dịch vụ y tế liên quan khi cần thiết.

Câu hỏi của người dùng: {question}
"""
    },

    "parent": {
        "male": """Bạn là một chatbot giáo dục giới tính dành cho PHỤ HUYNH NAM.
        
Hướng dẫn bắt buộc:
1. Cung cấp hướng dẫn về cách trò chuyện với con cái về giáo dục giới tính phù hợp với độ tuổi.
2. Nhấn mạnh vai trò của người cha/nam giới trong việc giáo dục giới tính cho con.
3. Nhấn mạnh tầm quan trọng của việc cung cấp thông tin chính xác và xây dựng kênh giao tiếp cởi mở.
4. Cung cấp chiến lược để giải quyết các câu hỏi khó hoặc nhạy cảm.
5. Hỗ trợ phụ huynh nam trong việc giáo dục con về ranh giới cá nhân, sự an toàn và mối quan hệ lành mạnh.
6. Đưa ra lời khuyên về cách nhận biết các vấn đề tiềm ẩn và khi nào cần tìm sự trợ giúp chuyên nghiệp.
7. Đề xuất tài nguyên phù hợp với độ tuổi để hỗ trợ giáo dục giới tính.
8. Cung cấp hướng dẫn cụ thể cho việc giáo dục giới tính từ góc nhìn của người cha/nam giới.

Câu hỏi của người dùng: {question}
""",
        "female": """Bạn là một chatbot giáo dục giới tính dành cho PHỤ HUYNH NỮ.
        
Hướng dẫn bắt buộc:
1. Cung cấp hướng dẫn về cách trò chuyện với con cái về giáo dục giới tính phù hợp với độ tuổi.
2. Nhấn mạnh vai trò của người mẹ/nữ giới trong việc giáo dục giới tính cho con.
3. Nhấn mạnh tầm quan trọng của việc cung cấp thông tin chính xác và xây dựng kênh giao tiếp cởi mở.
4. Cung cấp chiến lược để giải quyết các câu hỏi khó hoặc nhạy cảm.
5. Hỗ trợ phụ huynh nữ trong việc giáo dục con về ranh giới cá nhân, sự an toàn và mối quan hệ lành mạnh.
6. Đưa ra lời khuyên về cách nhận biết các vấn đề tiềm ẩn và khi nào cần tìm sự trợ giúp chuyên nghiệp.
7. Đề xuất tài nguyên phù hợp với độ tuổi để hỗ trợ giáo dục giới tính.
8. Cung cấp hướng dẫn cụ thể cho việc giáo dục giới tính từ góc nhìn của người mẹ/nữ giới.

Câu hỏi của người dùng: {question}
""",
        "default": """Bạn là một chatbot giáo dục giới tính dành cho PHỤ HUYNH.
    
Hướng dẫn bắt buộc:
1. Cung cấp hướng dẫn về cách trò chuyện với con cái về giáo dục giới tính phù hợp với độ tuổi.
2. Nhấn mạnh tầm quan trọng của việc cung cấp thông tin chính xác và xây dựng kênh giao tiếp cởi mở.
3. Cung cấp chiến lược để giải quyết các câu hỏi khó hoặc nhạy cảm.
4. Hỗ trợ phụ huynh trong việc giáo dục con về ranh giới cá nhân, sự an toàn và mối quan hệ lành mạnh.
5. Đưa ra lời khuyên về cách nhận biết các vấn đề tiềm ẩn và khi nào cần tìm sự trợ giúp chuyên nghiệp.
6. Đề xuất tài nguyên phù hợp với độ tuổi để hỗ trợ giáo dục giới tính.

Câu hỏi của người dùng: {question}
"""
    }
}

# Function calling prompt để xác định câu hỏi có liên quan đến giáo dục giới tính không
# Hàm để kiểm tra sự phù hợp của nội dung

class MessageTypeResponse(BaseModel):
    is_sex_education_related: bool = Field(
        ..., description="Câu hỏi có liên quan tới chủ đề giáo dục giới tính không, nếu có trả về True và False nếu ngược lại"
    )
    is_greeting: bool = Field(
        ..., description="Câu hỏi có phải là lời chào hỏi hoặc tạm biệt không, nếu có trả về True và False nếu ngược lại"
    )
    reason: str = Field(
        ..., description="Lý do tại sao lại có kết quả như thế"
    )

message_type_parser = PydanticOutputParser(pydantic_object=MessageTypeResponse)

message_type_prompt = ChatPromptTemplate.from_messages(
    [
        ("system",
         """Bạn cần phân loại câu hỏi của người dùng vào một trong các loại sau:
         
         1. Liên quan đến giáo dục giới tính
         Các chủ đề liên quan đến giáo dục giới tính bao gồm nhưng không giới hạn:
         - Cơ thể con người và sự phát triển (dậy thì, các bộ phận cơ thể, thay đổi cơ thể)
         - Sức khỏe sinh sản (kinh nguyệt, mãn kinh, tinh hoàn, xuất tinh, sức khỏe tuyến tiền liệt)
         - Mối quan hệ tình cảm và tình dục (mối quan hệ lành mạnh, đồng thuận, giao tiếp)
         - Bệnh lây truyền qua đường tình dục (HIV/AIDS, bệnh lây qua đường tình dục, phòng ngừa)
         - Phương pháp tránh thai và kế hoạch hóa gia đình
         - Định hướng tính dục và bản dạng giới
         - Vấn đề ranh giới cá nhân và tôn trọng
         
         2. Là lời chào hỏi hoặc tạm biệt
         Các câu chào hỏi/tạm biệt có thể là:
         - Xin chào, chào bạn, hello, hi, hey
         - Tạm biệt, goodbye, bye, see you
         - Chúc ngày tốt lành, chúc buổi sáng/chiều/tối tốt lành
         - Cảm ơn bạn, thank you, cảm ơn vì đã giúp đỡ
         - Và các biến thể khác của lời chào/tạm biệt
         
         3. Không liên quan đến giáo dục giới tính và không phải lời chào hỏi/tạm biệt
         
         Trả về JSON với định dạng:
         {format_instructions}
         
         Câu hỏi của người dùng: {question}
         """)
    ]
).partial(format_instructions=message_type_parser.get_format_instructions())

# Hàm để xác định loại tin nhắn của người dùng
async def classify_message_type(message: str, session_id: str = None, use_history: bool = True) -> dict:
    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model="gpt-4o-mini",
        temperature=0.1
    )
    
    try:
        # Tạo prompt với lịch sử chat nếu được yêu cầu và có session_id
        chat_history_text = ""
        if use_history and session_id and session_id in chat_histories and len(chat_histories[session_id]) > 0:
            chat_history_text = "Lịch sử hội thoại gần đây (3 tin nhắn gần nhất):\n"
            for idx, entry in enumerate(chat_histories[session_id]):
                chat_history_text += f"Người dùng: {entry.user_message}\n"
                chat_history_text += f"Chatbot: {entry.bot_response}\n\n"
        
        # Tạo prompt hoàn chỉnh với lịch sử chat
        system_message = """Bạn cần phân loại câu hỏi của người dùng vào một trong các loại sau:
         
         1. Liên quan đến giáo dục giới tính
         Các chủ đề liên quan đến giáo dục giới tính bao gồm nhưng không giới hạn:
         - Cơ thể con người và sự phát triển (dậy thì, các bộ phận cơ thể, thay đổi cơ thể)
         - Sức khỏe sinh sản (kinh nguyệt, mãn kinh, tinh hoàn, xuất tinh, sức khỏe tuyến tiền liệt)
         - Mối quan hệ tình cảm và tình dục (mối quan hệ lành mạnh, đồng thuận, giao tiếp)
         - Bệnh lây truyền qua đường tình dục (HIV/AIDS, bệnh lây qua đường tình dục, phòng ngừa)
         - Phương pháp tránh thai và kế hoạch hóa gia đình
         - Định hướng tính dục và bản dạng giới
         - Vấn đề ranh giới cá nhân và tôn trọng
         
         2. Là lời chào hỏi hoặc tạm biệt
         Các câu chào hỏi/tạm biệt có thể là:
         - Xin chào, chào bạn, hello, hi, hey
         - Tạm biệt, goodbye, bye, see you
         - Chúc ngày tốt lành, chúc buổi sáng/chiều/tối tốt lành
         - Cảm ơn bạn, thank you, cảm ơn vì đã giúp đỡ
         - Và các biến thể khác của lời chào/tạm biệt
         
         3. Không liên quan đến giáo dục giới tính và không phải lời chào hỏi/tạm biệt
         
         Trả về JSON với định dạng:
         {format_instructions}
         """
        
        # Nếu có lịch sử chat, thêm vào prompt
        if chat_history_text:
            system_message += f"\n\n{chat_history_text}\n"
            system_message += f"Câu hỏi mới của người dùng cần phân loại: {message}"
        else:
            system_message += f"\n\nCâu hỏi của người dùng: {message}"
        
        # Tạo message prompt với lịch sử chat
        message_prompt = ChatPromptTemplate.from_messages([
            ("system", system_message)
        ]).partial(format_instructions=message_type_parser.get_format_instructions())
        
        # Thực hiện phân loại
        chain = message_prompt | llm | message_type_parser
        response = chain.invoke({})
        return response.model_dump()
    except Exception as e:
        print(f"Error in message classification: {e}")
        return {
            "is_sex_education_related": True, 
            "is_greeting": False,
            "reason": f"Lỗi phân loại: {str(e)}"
        }


# Hàm xử lý lời chào hỏi
async def handle_greeting(message: str, user_age_group: str, user_gender: str = None) -> dict:
    greeting_prompts = {
        "child": """Bạn là chatbot giáo dục giới tính thân thiện dành cho trẻ em. 
        Hãy trả lời lời chào hoặc tạm biệt của trẻ một cách vui vẻ, thân thiện và phù hợp với lứa tuổi. 
        Sử dụng ngôn ngữ đơn giản và gần gũi.
        Đừng quên giới thiệu bản thân là chatbot giáo dục giới tính có thể giúp trẻ tìm hiểu về cơ thể và sự phát triển.
        Tin nhắn: {message}""",
        
        "teen": """Bạn là chatbot giáo dục giới tính dành cho thanh thiếu niên.
        Hãy trả lời lời chào hoặc tạm biệt của họ một cách thân thiện và tôn trọng.
        Giới thiệu bản thân là chatbot có thể giúp trả lời các câu hỏi về sự phát triển cơ thể, mối quan hệ lành mạnh và sức khỏe sinh sản.
        Tin nhắn: {message}""",
        
        "adult": """Bạn là chatbot giáo dục giới tính chuyên nghiệp dành cho người trưởng thành.
        Hãy trả lời lời chào hoặc tạm biệt của họ một cách lịch sự và chuyên nghiệp.
        Giới thiệu bản thân là chatbot có thể cung cấp thông tin về sức khỏe tình dục và sinh sản, mối quan hệ lành mạnh và các vấn đề liên quan.
        Tin nhắn: {message}""",
        
        "parent": """Bạn là chatbot giáo dục giới tính hỗ trợ cho phụ huynh.
        Hãy trả lời lời chào hoặc tạm biệt của họ một cách lịch sự và chuyên nghiệp.
        Giới thiệu bản thân là chatbot có thể hỗ trợ phụ huynh trong việc giáo dục giới tính cho con cái, cung cấp chiến lược trò chuyện và tài liệu phù hợp với độ tuổi.
        Tin nhắn: {message}"""
    }
    
    try:
        llm = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY,
            model="gpt-4o-mini",
            temperature=0.7,
        )
        
        prompt_template = PromptTemplate(
            input_variables=["message"],
            template=greeting_prompts.get(user_age_group, greeting_prompts["adult"])
        )
        
        chain = LLMChain(
            llm=llm,
            prompt=prompt_template
        )
        
        response = chain.run(message=message)
        
        return {
            "response": response,
            "appropriate": True,
            "is_sex_education_related": False
        }
    except Exception as e:
        print(f"Error in handling greeting: {e}")
        return {
            "response": "Xin chào! Tôi là chatbot giáo dục giới tính. Tôi có thể giúp gì cho bạn hôm nay?",
            "appropriate": True,
            "is_sex_education_related": False
        }

# Sửa đổi hàm xử lý tin nhắn sử dụng LangChain và GPT-4o-mini
async def process_message_with_langchain(message: str, user_age_group: str, user_gender: str = None, session_id: str = None, use_history: bool = True) -> ChatResponse:
    
    try:
        # Kiểm tra API key
        if not OPENAI_API_KEY:
            return ChatResponse(
                response="Thiết lập API chưa hoàn tất. Vui lòng cung cấp OPENAI_API_KEY trong biến môi trường.",
                appropriate=True,
                is_sex_education_related=True
            )
        
        # Phân loại tin nhắn với lịch sử chat nếu có
        message_classification = await classify_message_type(message, session_id, use_history)
        is_sex_ed_related = message_classification["is_sex_education_related"]
        is_greeting = message_classification["is_greeting"]
        
        # Xử lý lời chào hỏi
        if is_greeting:
            greeting_response = await handle_greeting(message, user_age_group, user_gender)
            return ChatResponse(**greeting_response)
        
        # Nếu không liên quan đến giáo dục giới tính và không phải lời chào
        if not is_sex_ed_related and not is_greeting:
            return ChatResponse(
                response="Xin lỗi, tôi là chatbot chuyên về giáo dục giới tính. Tôi chỉ có thể trả lời các câu hỏi liên quan đến giáo dục giới tính. Bạn có thể hỏi tôi về các chủ đề như sự phát triển cơ thể, sức khỏe sinh sản, mối quan hệ lành mạnh, hoặc các vấn đề liên quan khác.",
                appropriate=True,
                is_sex_education_related=False
            )
        
        # Khởi tạo LLM với mô hình GPT-4o-mini
        llm = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY,
            model="gpt-4o-mini",
            temperature=0.7
        )
        
        # Tạo hoặc lấy bộ nhớ hội thoại cho người dùng
        if session_id:
            if session_id not in conversation_memories:
                conversation_memories[session_id] = ConversationBufferMemory(return_messages=True)
            memory = conversation_memories[session_id]
        else:
            memory = ConversationBufferMemory(return_messages=True)
        
        # Lấy lịch sử chat nếu được yêu cầu và có session_id
        chat_history_text = ""
        if use_history and session_id and session_id in chat_histories and len(chat_histories[session_id]) > 0:
            chat_history_text = "Lịch sử hội thoại gần đây:\n"
            for idx, entry in enumerate(chat_histories[session_id]):
                chat_history_text += f"Người dùng: {entry.user_message}\n"
                chat_history_text += f"Chatbot: {entry.bot_response}\n\n"
        
        # Tạo prompt template với lịch sử chat nếu có
        if user_gender and user_gender in ["male", "female"]:
            base_template = age_gender_prompts[user_age_group][user_gender]
        else:
            base_template = age_gender_prompts[user_age_group]["default"]
        
        # Thêm lịch sử chat vào prompt nếu có
        if chat_history_text:
            final_template = f"{base_template}\n\n{chat_history_text}\nCâu hỏi mới: {{question}}"
        else:
            final_template = base_template
        
        # Tạo prompt template
        prompt_template = PromptTemplate(
            input_variables=["question"],
            template=final_template
        )
        
        # Tạo chain
        chain = LLMChain(
            llm=llm,
            prompt=prompt_template,
            memory=memory
        )
        
        # Gửi tin nhắn và nhận phản hồi
        response = chain.run(question=message)
        
        return ChatResponse(
            response=response,
            appropriate=True,
            is_sex_education_related=True
        )
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return ChatResponse(
            response=f"Đã xảy ra lỗi khi xử lý yêu cầu: {str(e)}",
            appropriate=True,
            is_sex_education_related=True
        )

# 3. Cập nhật endpoint chat để hỗ trợ sử dụng lịch sử chat
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # Kiểm tra độ tuổi hợp lệ
    if request.user_age_group not in ["child", "teen", "adult", "parent"]:
        raise HTTPException(status_code=400, detail="Độ tuổi không hợp lệ. Vui lòng chọn một trong các giá trị: child, teen, adult, parent")
    
    # Xác định có sử dụng lịch sử chat không
    use_history = request.use_history if hasattr(request, 'use_history') else True
    
    # Xử lý tin nhắn và trả về câu trả lời sử dụng LangChain và GPT-4o-mini
    response = await process_message_with_langchain(
        message=request.message, 
        user_age_group=request.user_age_group, 
        user_gender=request.user_gender, 
        session_id=request.session_id,
        use_history=use_history
    )
    
    # Lưu vào lịch sử chat nếu có session_id
    if request.session_id:
        chat_histories[request.session_id].append(
            ChatHistoryEntry(
                timestamp=datetime.now().isoformat(),
                user_message=request.message,
                bot_response=response.response,
                user_age_group=request.user_age_group,
                user_gender=request.user_gender
            )
        )
    
    return response


# API endpoint để lấy danh sách các nhóm tuổi
@app.get("/age-groups", response_model=List[str])
async def get_age_groups():
    return list(age_gender_prompts.keys())

# API endpoint để xóa bộ nhớ hội thoại
@app.delete("/clear-memory/{session_id}")
async def clear_memory(session_id: str):
    if session_id in conversation_memories:
        del conversation_memories[session_id]
        return {"status": "success", "message": f"Đã xóa bộ nhớ hội thoại cho session {session_id}"}
    else:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy session {session_id}")

# API endpoint để kiểm tra trạng thái hoạt động của API
@app.get("/health")
async def health_check():
    api_status = "OK" if OPENAI_API_KEY else "CONFIGURED_ERROR"
    message = "API đang hoạt động bình thường" if OPENAI_API_KEY else "Thiếu OPENAI_API_KEY"
    
    return {
        "status": api_status,
        "message": message,
        "langchain_status": "enabled",
        "model": "gpt-4o-mini"
    }

# API endpoint để lấy thông tin về API
@app.get("/")
async def root():
    return {
        "name": "Sex Education Chatbot API - Powered by GPT-4o-mini",
        "version": "1.0.0",
        "description": "API cung cấp thông tin về giáo dục giới tính phù hợp với độ tuổi sử dụng LangChain và GPT-4o-mini",
        "endpoints": [
            {"path": "/chat", "method": "POST", "description": "Gửi tin nhắn và nhận câu trả lời"},
            {"path": "/age-groups", "method": "GET", "description": "Lấy danh sách các nhóm tuổi"},
            {"path": "/clear-memory/{session_id}", "method": "DELETE", "description": "Xóa bộ nhớ hội thoại cho một session"},
            {"path": "/health", "method": "GET", "description": "Kiểm tra trạng thái hoạt động của API"},
            {"path": "/docs", "method": "GET", "description": "Tài liệu API tự động tạo"}
        ]
    }

# Middleware để xử lý CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong môi trường sản xuất, nên chỉ định các nguồn cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8800, reload=False)