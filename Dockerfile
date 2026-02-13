FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (build-essential for some python libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and local packages
COPY requirements.txt .
COPY pandas-ta.tar.gz .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install pandas-ta.tar.gz

# Copy source code
COPY src ./src

# Create log directory and non-root user
RUN mkdir -p /app/logs && \
    adduser --disabled-password --gecos '' cuanuser && \
    chown -R cuanuser:cuanuser /app/logs
USER cuanuser

EXPOSE 8000

# Run FastAPI via uvicorn (working dir = src for module imports)
WORKDIR /app/src
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
