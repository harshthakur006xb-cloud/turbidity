# Production Dockerfile for AquaSpot Laser Turbidity Analyzer
FROM python:3.11-slim

# Install OpenCV system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements & install dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend and frontend static build
COPY backend/ ./backend/
COPY frontend/dist ./frontend/dist

EXPOSE 8000

ENV PORT=8000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
