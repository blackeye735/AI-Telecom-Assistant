# ================================================
# Stage 1: Builder - Install dependencies
# ================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# ================================================
# Stage 2: Runtime - Minimal production image
# ================================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY app/ ./app/
COPY data/ ./data/
COPY chroma_db/ ./chroma_db/
COPY .env.example .env

# Copy startup script
COPY startup.sh .
RUN chmod +x startup.sh

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH

# Expose ports
# 8000 - FastAPI
# 8501 - Streamlit
EXPOSE 8000 8501

# Health check (Streamlit port)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run startup script
CMD ["./startup.sh"]
