FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (IMPORTANT for ML + OpenCV + dlib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    gcc \
    g++ \
    curl \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip (helps avoid build issues)
RUN pip install --upgrade pip

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.txt

# Copy rest of the code
COPY . .

# Start server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
