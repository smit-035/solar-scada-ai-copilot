FROM python:3.13-slim

WORKDIR /app

# Install system dependencies needed for PostgreSQL client
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies list first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend files
COPY . .

# Expose API port
EXPOSE 5000

# Run Flask server as a module
CMD ["python", "-m", "backend.app"]
