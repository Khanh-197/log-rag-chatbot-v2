#!/bin/bash

echo "Waiting for ChromaDB to be available..."
MAX_RETRIES=30
RETRY_DELAY=5

# Lấy thông tin từ biến môi trường
CHROMA_HOST=${CHROMA_HOST:-vector-db}
CHROMA_PORT=${CHROMA_PORT:-8000}
USE_LOCAL=${CHROMA_USE_LOCAL:-false}

if [ "$USE_LOCAL" = "true" ]; then
    echo "Using local ChromaDB, skipping connection check."
    exit 0
fi

for ((i=1; i<=MAX_RETRIES; i++)); do
    if curl -s "http://$CHROMA_HOST:$CHROMA_PORT/api/v1/heartbeat" > /dev/null; then
        echo "ChromaDB V1 API is available!"
        break
    elif curl -s "http://$CHROMA_HOST:$CHROMA_PORT/api/v2/heartbeat" > /dev/null; then
        echo "ChromaDB V2 API is available!"
        break
    fi
    
    if [ $i -eq $MAX_RETRIES ]; then
        echo "ChromaDB is not available after $MAX_RETRIES retries."
        echo "The application will fallback to using local ChromaDB."
        break
    fi
    
    echo "Attempt $i/$MAX_RETRIES: ChromaDB not available yet. Waiting $RETRY_DELAY seconds..."
    sleep $RETRY_DELAY
done

# Kiểm tra xem thư mục dữ liệu ChromaDB local có tồn tại chưa
if [ ! -d "/app/chroma_db" ]; then
    echo "Creating directory for local ChromaDB data..."
    mkdir -p /app/chroma_db
fi

echo "ChromaDB setup completed."
