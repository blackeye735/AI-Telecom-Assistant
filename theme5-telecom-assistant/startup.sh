#!/bin/bash
# Startup script to run both FastAPI and Streamlit

set -e

echo "============================================"
echo "Starting Telecom Knowledge Assistant"
echo "============================================"

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start FastAPI in background
echo "Starting FastAPI backend on port 8000..."
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Wait for FastAPI to be ready
echo "Waiting for FastAPI to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✓ FastAPI is ready"
        break
    fi
    sleep 1
done

# Start Streamlit in foreground
echo "Starting Streamlit UI on port 8501..."
streamlit run app/ui/streamlit_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.serverAddress 0.0.0.0 \
    --browser.gatherUsageStats false

# If Streamlit exits, kill FastAPI
kill $FASTAPI_PID 2>/dev/null
