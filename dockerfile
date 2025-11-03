# ================= BACKEND + FRONTEND =================
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy backend code
COPY backend/ ./backend/

# Copy frontend (HTML, CSS, JS, images)
COPY frontend/ ./frontend/

# Install dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
