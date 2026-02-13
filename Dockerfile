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

# Create non-root user
RUN adduser --disabled-password --gecos '' cuanuser
USER cuanuser

CMD ["tail", "-f", "/dev/null"]
