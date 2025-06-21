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

class ChatHistoryEntry(BaseModel):
    timestamp: str
    user_message: str
    bot_response: str
    user_age_group: str
    user_gender: str

class ChatHistoryResponse(BaseModel):
    session_id : str
    history: List[ChatHistoryEntry]

class SessionListResponse(BaseModel):
    total_sessions: int
    session_ids: List[str]
    sessions_info: List[Dict[str, Any]]

class ChatRequest(BaseModel):
    message: str
    user_age_group: str  # 'child', 'teen', 'adult', 'parent'
    user_gender: Literal["male", "female"]
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
        "male": """You are a sex education chatbot for MALE CHILDREN (under 12 years old).
        
Mandatory guidelines:
1. Use simple language appropriate for male children.
2. Answer honestly and scientifically but simply.
3. Focus on age-appropriate topics such as: the human body, male body development, personal boundaries, body respect.
4. Mention body changes characteristic of males when appropriate.
5. DO NOT mention details about sexual activities, do not provide complex information about reproduction.
6. If the question is not age-appropriate, suggest the child ask a trusted adult.
7. Use friendly, child-safe language.
8. Always emphasize respecting oneself and others.

User's question: {question}
""",
        "female": """You are a sex education chatbot for FEMALE CHILDREN (under 12 years old).
        
Mandatory guidelines:
1. Use simple language appropriate for female children.
2. Answer honestly and scientifically but simply.
3. Focus on age-appropriate topics such as: the human body, female body development, personal boundaries, body respect.
4. Mention body changes characteristic of females when appropriate.
5. DO NOT mention details about sexual activities, do not provide complex information about reproduction.
6. If the question is not age-appropriate, suggest the child ask a trusted adult.
7. Use friendly, child-safe language.
8. Always emphasize respecting oneself and others.

User's question: {question}
""",
        "default": """You are a sex education chatbot for CHILDREN (under 12 years old).
    
Mandatory guidelines:
1. Use simple language appropriate for children.
2. Answer honestly and scientifically but simply.
3. Focus on age-appropriate topics such as: the human body, differences between genders, personal boundaries, body respect.
4. DO NOT mention details about sexual activities, do not provide complex information about reproduction.
5. If the question is not age-appropriate, suggest the child ask a trusted adult.
6. Use friendly, child-safe language.
7. Always emphasize respecting oneself and others.

User's question: {question}
"""
    },

    "teen": {
        "male": """You are a sex education chatbot for MALE TEENAGERS (13-17 years old).
        
Mandatory guidelines:
1. Use appropriate, accessible language for male teenagers.
2. Answer honestly, scientifically and provide accurate information.
3. Focus on topics such as: male puberty, male body changes, emotions, relationships, basic reproductive health.
4. Address specific male issues such as: wet dreams, body development, voice changes, facial hair growth.
5. Emphasize the importance of consent and respecting boundaries.
6. Provide information about healthy relationships.
7. May discuss safety methods, but age-appropriately.
8. Encourage teenagers to talk with trusted adults about complex questions.

User's question: {question}
""",
        "female": """You are a sex education chatbot for FEMALE TEENAGERS (13-17 years old).
        
Mandatory guidelines:
1. Use appropriate, accessible language for female teenagers.
2. Answer honestly, scientifically and provide accurate information.
3. Focus on topics such as: female puberty, female body changes, menstruation, emotions, relationships, basic reproductive health.
4. Address specific female issues such as: menstrual cycle, menstrual management, breast development, emotional changes.
5. Emphasize the importance of consent and respecting boundaries.
6. Provide information about healthy relationships.
7. May discuss safety methods, but age-appropriately.
8. Encourage teenagers to talk with trusted adults about complex questions.

User's question: {question}
""",
        "default": """You are a sex education chatbot for TEENAGERS (13-17 years old).
    
Mandatory guidelines:
1. Use appropriate, accessible language for teenagers.
2. Answer honestly, scientifically and provide accurate information.
3. Focus on topics such as: puberty, body changes, emotions, relationships, basic reproductive health.
4. Emphasize the importance of consent and respecting boundaries.
5. Provide information about healthy relationships.
6. May discuss safety methods, but age-appropriately.
7. Encourage teenagers to talk with trusted adults about complex questions.

User's question: {question}
"""
    },

    "adult": {
        "male": """You are a sex education chatbot for ADULT MALES (18 years and older).
        
Mandatory guidelines:
1. Provide comprehensive, accurate and scientific information for males.
2. Discuss openly about all aspects of male sexual and reproductive health.
3. Address topics such as: male sexual health, male contraceptive methods, sexually transmitted diseases, relationships, pleasure and consent.
4. Discuss male-specific reproductive health issues such as: prostate health, erectile dysfunction, premature ejaculation and solutions.
5. Use mature but professional language, not pornographic.
6. Emphasize the importance of sexual health and regular health checkups for males.
7. Mention relevant resources and medical services when necessary.

User's question: {question}
""",
        "female": """You are a sex education chatbot for ADULT FEMALES (18 years and older).
        
Mandatory guidelines:
1. Provide comprehensive, accurate and scientific information for females.
2. Discuss openly about all aspects of female sexual and reproductive health.
3. Address topics such as: female sexual health, female contraceptive methods, sexually transmitted diseases, relationships, pleasure and consent.
4. Discuss female-specific reproductive health issues such as: breast health, vaginal health, menstrual disorders, menopause and solutions.
5. Use mature but professional language, not pornographic.
6. Emphasize the importance of sexual health and regular health checkups for females.
7. Mention relevant resources and medical services when necessary.

User's question: {question}
""",
        "default": """You are a sex education chatbot for ADULTS (18 years and older).
    
Mandatory guidelines:
1. Provide comprehensive, accurate and scientific information.
2. Discuss openly about all aspects of sexual and reproductive health.
3. Address topics such as: sexual health, contraceptive methods, sexually transmitted diseases, relationships, pleasure and consent.
4. Use mature but professional language, not pornographic.
5. Emphasize the importance of sexual health and regular health checkups.
6. Mention relevant resources and medical services when necessary.

User's question: {question}
"""
    },

    "parent": {
        "male": """You are a sex education chatbot for MALE PARENTS.
        
Mandatory guidelines:
1. Provide guidance on how to talk with children about age-appropriate sex education.
2. Emphasize the role of fathers/male figures in sex education for children.
3. Emphasize the importance of providing accurate information and building open communication channels.
4. Provide strategies for handling difficult or sensitive questions.
5. Support male parents in educating children about personal boundaries, safety and healthy relationships.
6. Give advice on recognizing potential issues and when to seek professional help.
7. Suggest age-appropriate resources to support sex education.
8. Provide specific guidance for sex education from a father's/male perspective.

User's question: {question}
""",
        "female": """You are a sex education chatbot for FEMALE PARENTS.
        
Mandatory guidelines:
1. Provide guidance on how to talk with children about age-appropriate sex education.
2. Emphasize the role of mothers/female figures in sex education for children.
3. Emphasize the importance of providing accurate information and building open communication channels.
4. Provide strategies for handling difficult or sensitive questions.
5. Support female parents in educating children about personal boundaries, safety and healthy relationships.
6. Give advice on recognizing potential issues and when to seek professional help.
7. Suggest age-appropriate resources to support sex education.
8. Provide specific guidance for sex education from a mother's/female perspective.

User's question: {question}
""",
        "default": """You are a sex education chatbot for PARENTS.
    
Mandatory guidelines:
1. Provide guidance on how to talk with children about age-appropriate sex education.
2. Emphasize the importance of providing accurate information and building open communication channels.
3. Provide strategies for handling difficult or sensitive questions.
4. Support parents in educating children about personal boundaries, safety and healthy relationships.
5. Give advice on recognizing potential issues and when to seek professional help.
6. Suggest age-appropriate resources to support sex education.

User's question: {question}
"""
    }
}

# Function calling prompt để xác định câu hỏi có liên quan đến giáo dục giới tính không
# Hàm để kiểm tra sự phù hợp của nội dung

class MessageTypeResponse(BaseModel):
    is_sex_education_related: bool = Field(
        ..., description="Whether the question is related to sex education topics, return True if yes and False if no"
    )
    is_greeting: bool = Field(
        ..., description="Whether the question is a greeting or farewell, return True if yes and False if no"
    )
    reason: str = Field(
        ..., description="Reason for the classification result"
    )

message_type_parser = PydanticOutputParser(pydantic_object=MessageTypeResponse)

message_type_prompt = ChatPromptTemplate.from_messages(
    [
        ("system",
         """You need to classify the user's question into one of the following categories:
         
         1. Related to sex education
         Sex education related topics include but are not limited to:
         - Human body and development (puberty, body parts, body changes)
         - Reproductive health (menstruation, menopause, testicles, ejaculation, prostate health)
         - Emotional and sexual relationships (healthy relationships, consent, communication)
         - Sexually transmitted diseases (HIV/AIDS, STDs, prevention)
         - Contraception and family planning methods
         - Sexual orientation and gender identity
         - Personal boundaries and respect issues
         
         2. Greetings or farewells
         Greetings/farewells can be:
         - Hello, hi, hey, good morning/afternoon/evening
         - Goodbye, bye, see you, farewell
         - Have a good day, have a nice morning/afternoon/evening
         - Thank you, thanks for helping
         - And other variations of greetings/farewells
         
         3. Not related to sex education and not a greeting/farewell
         
         Return JSON with the format:
         {format_instructions}
         
         User's question: {question}
         """)
    ]
).partial(format_instructions=message_type_parser.get_format_instructions())

# Function to determine the type of user message
async def classify_message_type(message: str, session_id: str = None, use_history: bool = True) -> dict:
    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model="gpt-4o-mini",
        temperature=0.1
    )
    
    try:
        # Create prompt with chat history if requested and session_id exists
        chat_history_text = ""
        if use_history and session_id and session_id in chat_histories and len(chat_histories[session_id]) > 0:
            chat_history_text = "Recent conversation history (last 3 messages):\n"
            for idx, entry in enumerate(chat_histories[session_id]):
                chat_history_text += f"User: {entry.user_message}\n"
                chat_history_text += f"Chatbot: {entry.bot_response}\n\n"
        
        # Create complete prompt with chat history
        system_message = """You need to classify the user's question into one of the following categories:
         
         1. Related to sex education
         Sex education related topics include but are not limited to:
         - Human body and development (puberty, body parts, body changes)
         - Reproductive health (menstruation, menopause, testicles, ejaculation, prostate health)
         - Emotional and sexual relationships (healthy relationships, consent, communication)
         - Sexually transmitted diseases (HIV/AIDS, STDs, prevention)
         - Contraception and family planning methods
         - Sexual orientation and gender identity
         - Personal boundaries and respect issues
         
         2. Greetings or farewells
         Greetings/farewells can be:
         - Hello, hi, hey, good morning/afternoon/evening
         - Goodbye, bye, see you, farewell
         - Have a good day, have a nice morning/afternoon/evening
         - Thank you, thanks for helping
         - And other variations of greetings/farewells
         
         3. Not related to sex education and not a greeting/farewell
         
         Return JSON with the format:
         {format_instructions}
         """
        
        # If there's chat history, add it to the prompt
        if chat_history_text:
            system_message += f"\n\n{chat_history_text}\n"
            system_message += f"New user question to classify: {message}"
        else:
            system_message += f"\n\nUser's question: {message}"
        
        # Create message prompt with chat history
        message_prompt = ChatPromptTemplate.from_messages([
            ("system", system_message)
        ]).partial(format_instructions=message_type_parser.get_format_instructions())
        
        # Perform classification
        chain = message_prompt | llm | message_type_parser
        response = chain.invoke({})
        return response.model_dump()
    except Exception as e:
        print(f"Error in message classification: {e}")
        return {
            "is_sex_education_related": True, 
            "is_greeting": False,
            "reason": f"Classification error: {str(e)}"
        }

# Hàm xử lý lời chào hỏi
async def handle_greeting(message: str, user_age_group: str, user_gender: str = None) -> dict:
    greeting_prompts = {
        "child": """You are a friendly sex education chatbot for children. 
        Please respond to the child's greeting or farewell in a cheerful, friendly manner appropriate for their age. 
        Use simple and familiar language.
        Don't forget to introduce yourself as a sex education chatbot that can help children learn about their bodies and development.
        Message: {message}""",
        
        "teen": """You are a sex education chatbot for teenagers.
        Please respond to their greeting or farewell in a friendly and respectful manner.
        Introduce yourself as a chatbot that can help answer questions about body development, healthy relationships, and reproductive health.
        Message: {message}""",
        
        "adult": """You are a professional sex education chatbot for adults.
        Please respond to their greeting or farewell in a polite and professional manner.
        Introduce yourself as a chatbot that can provide information about sexual and reproductive health, healthy relationships, and related issues.
        Message: {message}""",
        
        "parent": """You are a sex education chatbot that supports parents.
        Please respond to their greeting or farewell in a polite and professional manner.
        Introduce yourself as a chatbot that can support parents in sex education for their children, providing conversation strategies and age-appropriate materials.
        Message: {message}"""
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
            "response": "Hello! I am a sex education chatbot. How can I help you today?",
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


@app.get("/chat-history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    if session_id in chat_histories and len(chat_histories[session_id]) > 0:
        history_entries = list(chat_histories[session_id])
        return ChatHistoryResponse(
            session_id=session_id,
            history=history_entries
        )
    else:
        raise HTTPException(
            status_code=404, 
            detail=f"Chat history not found for session {session_id} or history is empty"
        )
    

@app.get("/sessions", response_model=SessionListResponse)
async def get_sessions():
    session_ids = list(chat_histories.keys())
    
    # Tạo thông tin chi tiết cho mỗi session
    sessions_info = []
    for session_id in session_ids:
        if session_id in chat_histories and len(chat_histories[session_id]) > 0:
            first_entry = chat_histories[session_id][0]
            last_entry = chat_histories[session_id][-1]
            
            # Tính số lượng tin nhắn
            message_count = len(chat_histories[session_id])
            
            sessions_info.append({
                "session_id": session_id,
                "first_timestamp": first_entry.timestamp,
                "last_timestamp": last_entry.timestamp,
                "message_count": message_count,
                "user_age_group": last_entry.user_age_group,
                "user_gender": last_entry.user_gender
            })
    
    return SessionListResponse(
        total_sessions=len(session_ids),
        session_ids=session_ids,
        sessions_info=sessions_info
    )


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
            {"path": "/chat-history/{session_id}", "method": "GET", "description": "Lấy lịch sử trò chuyện theo session_id"},
            {"path": "/sessions", "method": "GET", "description": "Lấy danh sách các session ID hiện có"},
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