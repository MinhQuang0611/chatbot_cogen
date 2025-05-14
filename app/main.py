# app/main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Relative imports for routers and config
from .routers import chat_router, info_router
from .config import (
    CORS_ALLOW_ORIGINS,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS,
    OPENAI_API_KEY # Import để có thể check ở startup nếu muốn
)

# Khởi tạo FastAPI app
app = FastAPI(
    title="Sex Education Chatbot API - Refactored",
    description="API cung cấp thông tin giáo dục giới tính, được refactor theo cấu trúc module.",
    version="1.0.1"
)

# Thêm CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)

# Include routers
app.include_router(info_router.router, tags=["Information"])
app.include_router(chat_router.router, prefix="/api/v1", tags=["Chat"]) # Thêm prefix /api/v1 cho chat routes

# (Optional) Startup event to check for API Key
@app.on_event("startup")
async def startup_event():
    if not OPENAI_API_KEY:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! WARNING: OPENAI_API_KEY is not set in the environment. !!!")
        print("!!! The application might not function correctly.         !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    else:
        print("OpenAI API Key found. Application starting...")


if __name__ == "__main__":
    # Chú ý: Nếu file này là app/main.py thì câu lệnh run phải là "main:app"
    # Nếu bạn chạy từ thư mục CHATBOT/ thì là "app.main:app"
    uvicorn.run("app.main:app", host="0.0.0.0", port=8800, reload=True)
    # Đổi "test:app" thành "app.main:app" nếu file này là app/main.py
    # và app instance tên là "app".
    # Nếu bạn vẫn muốn giữ file gốc là test.py và chạy uvicorn test:app,
    # thì file test.py đó chỉ cần import app từ app.main:
    # from app.main import app
    # và các file khác không cần if __name__ == "__main__": uvicorn.run(...)