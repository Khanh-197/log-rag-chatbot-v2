FROM python:3.10-slim

WORKDIR /app

# Cài đặt dependencies cần thiết
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt các phụ thuộc Python
COPY requirements.txt .
RUN pip install --no-cache-dir torch==1.13.1 torchvision==0.14.1
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir sentence-transformers==2.2.2 huggingface-hub==0.12.1 requests

COPY . .
# Đảm bảo script có quyền thực thi
RUN chmod +x /app/setup_chromadb.sh

EXPOSE 8501

# Chạy script setup trước, sau đó khởi động ứng dụng
CMD ["/bin/bash", "-c", "/app/setup_chromadb.sh && streamlit run ui/streamlit_app.py"]
