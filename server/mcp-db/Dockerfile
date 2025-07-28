FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install -e .

# Copy application code
COPY . .

# Expose port
EXPOSE 8002

# Run the server
CMD ["python", "server.py"]