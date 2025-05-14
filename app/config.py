# app/config.py
import os
from dotenv import load_dotenv

load_dotenv() # Tải biến từ file .env

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Cấu hình CORS (có thể mở rộng ở đây nếu cần)
CORS_ALLOW_ORIGINS = ["*"] # Trong sản xuất, nên chỉ định cụ thể
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]