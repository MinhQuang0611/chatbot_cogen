# CHATBOT/Dockerfile

# Chọn một Python base image. Python 3.9 hoặc 3.10 là lựa chọn tốt.
# Sử dụng slim-buster để giữ kích thước image nhỏ.
FROM python:3.11.11

# Đặt biến môi trường để Python output không bị buffer, giúp log hiển thị ngay lập tức
ENV PYTHONUNBUFFERED 1

# Đặt thư mục làm việc trong container
WORKDIR /app

# Sao chép file requirements.txt vào thư mục làm việc
COPY requirements.txt requirements.txt

# Cài đặt các thư viện cần thiết từ requirements.txt
# --no-cache-dir để không lưu cache, giúp image nhỏ hơn
# --upgrade pip để đảm bảo pip là phiên bản mới nhất
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ thư mục 'app' (chứa mã nguồn của bạn) vào thư mục làm việc /app trong container
# Nếu thư mục mã nguồn của bạn là 'src/app' thì đổi thành COPY ./src/app ./app
COPY ./app ./app

# Mở cổng 8800 để container có thể nhận request từ bên ngoài
# Đây là cổng mà Uvicorn sẽ chạy (theo cấu hình trong app/main.py của bạn)
EXPOSE 8888

# Lệnh để chạy ứng dụng khi container khởi động
# Chạy Uvicorn, trỏ đến instance 'app' trong file 'app.main'
# --host 0.0.0.0 để chấp nhận kết nối từ mọi IP (cần thiết khi chạy trong Docker)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888", "--reload"]